"""Explicit local commands; no automatic experiment launch or dataset download."""

import argparse
from dataclasses import asdict, replace
import json
from pathlib import Path
import sys
import torch
from bullet_time.provenance import strict_json, atomic_json, digest, identity, integer
from bullet_time.loading.manifest import Corpus
from bullet_time.models.video import ModelConfig, build_model, model_identity
from bullet_time.training.runner import Runner, TrainConfig
from bullet_time.training.admission import admit


def read_config(path, cls):
    return cls(**strict_json(Path(path).read_bytes()))


def new_output(path):
    path = Path(path)
    path.mkdir(parents=True, exist_ok=False)
    return path


def load_backbone(checkpoint, external_cache=None):
    path = Path(checkpoint)
    meta = strict_json(Path(str(path) + ".json").read_bytes())
    if digest(path.read_bytes()) != meta["sha256"]:
        raise ValueError("backbone checkpoint hash mismatch")
    payload = torch.load(path, map_location="cpu", weights_only=True)
    if payload.get("schema_version") not in (
        "bullet-time.checkpoint.v1",
        "bullet-time.reference.v1",
    ):
        raise ValueError("unknown backbone checkpoint")
    from bullet_time.models.references import rebuild_backbone

    kind = payload["binding"].get("reference_kind", "videomae")
    if kind == "dinov2":
        from bullet_time.models.external import lock

        if payload["binding"]["external_lock"] != lock():
            raise ValueError("external source lock differs")
    model = rebuild_backbone(
        payload["binding"]["model"],
        payload["binding"]["training"]["seed"],
        kind=kind,
        cache=external_cache,
    )
    model.load_state_dict(payload["model"], strict=True)
    if model_identity(model) != meta["model_sha256"]:
        raise ValueError("backbone parameter hash mismatch")
    binding = payload["binding"]
    if identity(binding) != meta["binding_sha256"]:
        raise ValueError("backbone binding hash mismatch")
    integer(payload["global_step"], "global_step")
    if payload["schema_version"] == "bullet-time.reference.v1":
        if payload["global_step"] != 0 or binding["reference_status"] != (
            "external_pretrained" if kind == "dinov2" else "untrained"
        ):
            raise ValueError("invalid reference progress/status")
        assessment_eligible = True
    else:
        grids = binding.get("corpus_grids")
        assessment_eligible = False  # Old/unknown progress fails closed.
        if grids is not None:
            integer(grids, "corpus_grids", 1)
            config = TrainConfig(**binding["training"])
            config.validate()
            steps_per_pass = (grids + config.grids_per_update - 1) // config.grids_per_update
            total_steps = steps_per_pass * config.total_passes
            if payload["global_step"] > total_steps:
                raise ValueError("checkpoint exceeds fixed budget")
            assessment_eligible = (
                payload["global_step"] == total_steps and config.total_passes == 20
            )
    return model, {
        "assessment_eligible": assessment_eligible,
        "run_id": identity(payload["binding"]),
        "backbone_kind": kind,
        "checkpoint_sha256": meta["sha256"],
        "binding": payload["binding"],
        "global_step": payload["global_step"],
    }


def command_train(args):
    model_config = read_config(args.model_config, ModelConfig)
    training = read_config(args.training_config, TrainConfig)
    model_config.validate()
    training.validate()
    corpus = Corpus(args.manifest, image_size=model_config.image_size)
    admission = admit(
        corpus,
        model_config,
        training,
        args.scope,
        receipt_path=args.admission,
        stop_after_updates=args.stop_after_updates,
    )
    runner = Runner(corpus, model_config, training)
    if args.resume:
        runner.resume(args.resume)
    stop = args.stop_after_updates
    if stop is None:
        stop = runner.global_step + 1
    if stop <= runner.global_step or stop > runner.total_steps:
        raise ValueError("stop must be an absolute later step within fixed budget")
    interval = args.checkpoint_every_updates or runner.steps_per_pass
    if interval < 1:
        raise ValueError("checkpoint interval must be positive")
    output = new_output(args.output)
    run_record = {
        "schema_version": "bullet-time.run.v1",
        "status": "running",
        "run_id": runner.binding_sha256,
        "objective": "image_mae" if model_config.frames == 1 else "videomae",
        "condition": "image_only" if model_config.frames == 1 else training.condition,
        "recipe": training.recipe,
        "paired_pretraining_seed": training.seed,
        "binding": runner.binding,
        "binding_sha256": runner.binding_sha256,
        "admission": admission,
        "initial_step": runner.global_step,
        "stop_after_updates": stop,
        "checkpoint_every_updates": interval,
        "resume_source": str(Path(args.resume).resolve()) if args.resume else None,
    }
    atomic_json(output / "run.json", run_record)
    try:
        with (output / "updates.jsonl").open("x") as log:
            while runner.global_step < stop:
                event = runner.step(detailed_audit=args.detailed_audit)
                log.write(json.dumps(event, sort_keys=True, allow_nan=False) + "\n")
                log.flush()
                if runner.global_step % interval == 0 or runner.global_step == stop:
                    runner.save(output / f"step-{runner.global_step:06d}.pt")
        result = {
            "status": "completed_requested_segment",
            "scope": args.scope,
            "global_step": runner.global_step,
            "fixed_budget_steps": runner.total_steps,
            "binding_sha256": runner.binding_sha256,
            "latest_checkpoint": str((output / f"step-{runner.global_step:06d}.pt").resolve()),
            "updates_sha256": digest((output / "updates.jsonl").read_bytes()),
            "scientific_gate_pass": False,
        }
        atomic_json(output / "result.json", result)
        run_record.update(
            status=result["status"],
            completed_step=runner.global_step,
            updates_sha256=result["updates_sha256"],
        )
        atomic_json(output / "run.json", run_record)
        return result
    except BaseException as exc:
        run_record.update(status="failed", last_completed_step=runner.global_step)
        atomic_json(output / "run.json", run_record)
        atomic_json(
            output / "failure.json",
            {
                "status": "failed",
                "last_completed_step": runner.global_step,
                "error": str(exc),
                "exception_type": type(exc).__name__,
            },
        )
        raise


def command_fit(args):
    from bullet_time.evaluation.inputs import ImageStore, EvaluationInputs
    from bullet_time.evaluation.training import ReadoutConfig, Targets, build_readout, fit

    config = read_config(args.readout_config, ReadoutConfig)
    config.validate()
    store = ImageStore(args.images)
    inputs = EvaluationInputs(args.inputs, store)
    targets = Targets(args.labels, inputs, classes=config.classes)
    admission = {}
    if config.task in ("collision", "order", "tracking"):
        from bullet_time.evaluation.subsets import Groups, select_game_labels, verify_pairs

        if not args.groups or config.label_budget is None:
            raise ValueError("game fitting requires group metadata and an explicit episode budget")
        groups = Groups(args.groups)
        if config.task in ("collision", "order"):
            admission["pairs"] = verify_pairs(inputs, targets, groups, config.task)
        inputs = select_game_labels(inputs, groups, config.task, config.label_budget)
    else:
        from bullet_time.evaluation.external import validate_external_groups

        if not args.partitions or not args.groups:
            raise ValueError("SSv2 fitting requires partitions and complete video-group audit")
        partitions = strict_json(Path(args.partitions).read_bytes())
        admission["external_groups"] = validate_external_groups(
            partitions, strict_json(Path(args.groups).read_bytes())
        )
        for split, expected_ids in [
            ("train", partitions["train_10pct"]),
            ("dev", partitions["dev"]),
        ]:
            if {
                e.episode_id for e in inputs.examples if e.task_id == "ssv2" and e.split == split
            } != set(expected_ids):
                raise ValueError("SSv2 inputs differ from the frozen internal split/label subset")
    backbone, source = load_backbone(args.backbone, args.external_cache)
    if config.image_size != backbone.bt_config.image_size:
        raise ValueError("readout/backbone geometry mismatch")
    model = build_readout(backbone, config)
    from bullet_time.evaluation.access import prediction_access, prediction_ids

    output = new_output(args.output)
    try:
        report = fit(model, inputs, targets, config)
        report["backbone_source"] = source
        report["consumer_admission"] = admission
        atomic_json(output / "fit.json", report)
        state = {
            "schema_version": "bullet-time.readout.v1",
            "readout_config": asdict(config),
            "backbone_config": asdict(backbone.bt_config),
            "backbone_seed": source["binding"]["training"]["seed"],
            "backbone_source": source,
            "model": model.state_dict(),
            "fit_sha256": digest((output / "fit.json").read_bytes()),
            "actual_label_budget": report["train_episodes"],
            "allowed_prediction_splits": prediction_access(config, source),
        }
        path = output / "readout.pt"
        with path.open("xb") as file:
            torch.save(state, file)
        readout_sha256 = digest(path.read_bytes())
        identifiers = prediction_ids(config, source, readout_sha256)
        atomic_json(
            str(path) + ".json",
            {
                "sha256": readout_sha256,
                "model_sha256": model_identity(model),
                "prediction_identity": identifiers,
                "allowed_prediction_splits": state["allowed_prediction_splits"],
            },
        )
        return {
            "status": "fitted_development_only",
            "prediction_identity": identifiers,
            "allowed_prediction_splits": state["allowed_prediction_splits"],
            "report": str((output / "fit.json").resolve()),
            "checkpoint": str(path.resolve()),
        }
    except BaseException as exc:
        atomic_json(
            output / "failure.json",
            {"status": "failed", "error": str(exc), "exception_type": type(exc).__name__},
        )
        raise


def command_predict(args):
    from bullet_time.evaluation.inputs import ImageStore, EvaluationInputs
    from bullet_time.evaluation.training import ReadoutConfig, build_readout, predict, task_examples
    from bullet_time.evaluation.export import write_predictions, KEY

    path = Path(args.checkpoint)
    meta = strict_json(Path(str(path) + ".json").read_bytes())
    if digest(path.read_bytes()) != meta["sha256"]:
        raise ValueError("readout byte hash mismatch")
    state = torch.load(path, map_location="cpu", weights_only=True)
    if state["schema_version"] != "bullet-time.readout.v1":
        raise ValueError("unknown readout checkpoint")
    from bullet_time.evaluation.access import prediction_access, prediction_ids

    saved_config = ReadoutConfig(**state["readout_config"])
    saved_config.validate()
    allowed = prediction_access(saved_config, state["backbone_source"])
    if state.get("allowed_prediction_splits") != allowed or args.split not in allowed:
        raise ValueError("checkpoint is not eligible for the requested prediction split")
    identifiers = prediction_ids(saved_config, state["backbone_source"], meta["sha256"])
    if meta.get("prediction_identity") != identifiers:
        raise ValueError("prediction identity differs from fitted checkpoint")
    config = replace(saved_config, device=args.device)
    from bullet_time.models.references import rebuild_backbone

    backbone = rebuild_backbone(
        state["backbone_config"],
        state["backbone_seed"],
        kind=state["backbone_source"]["backbone_kind"],
        cache=args.external_cache,
    )
    model = build_readout(backbone, config)
    model.load_state_dict(state["model"], strict=True)
    if model_identity(model) != meta["model_sha256"]:
        raise ValueError("readout parameter hash mismatch")
    inputs = EvaluationInputs(args.inputs, ImageStore(args.images), allowed_splits=(args.split,))
    expected = strict_json(Path(args.expected).read_bytes())
    selected = task_examples(inputs, config)
    by_key = {
        (row["episode_or_video_id"], row["query_id"], str(row["horizon_or_frame"])): row
        for row in expected
    }
    if len(by_key) != len(expected) or set(by_key) != {e.key for e in selected}:
        raise ValueError("expected-key inventory differs from actual declared input")
    for e in selected:
        row = by_key[e.key]
        if (
            row["run_id"] != identifiers["run_id"]
            or row["checkpoint_id"] != identifiers["checkpoint_id"]
            or (row["label_budget"] != state["actual_label_budget"])
        ):
            raise ValueError(
                "prediction inventory does not bind actual run/checkpoint/label budget"
            )
        if (
            row["task_id"] != config.task
            or row["split"] != e.split
            or row["readout_seed"] != config.seed
            or row["prediction_role"] != e.prediction_role
        ):
            raise ValueError("prediction inventory metadata mismatch")
    observed = []
    for example, values in predict(model, inputs, config):
        row = {key: by_key[example.key][key] for key in KEY}
        row.update(status="ok", error="")
        if config.task in ("collision", "order"):
            row["contact_probability"] = values[0]
        elif config.task == "tracking":
            row.update(x=values[0], y=values[1], visibility_probability=values[2])
        else:
            row["class_id"] = max(range(len(values)), key=values.__getitem__)
        observed.append(row)
    return write_predictions(
        args.output,
        expected,
        observed,
        {
            "readout_sha256": meta["sha256"],
            "input_sha256": inputs.sha256,
            "image_manifest_sha256": inputs.store.manifest_sha256,
            "fit_sha256": state["fit_sha256"],
            "backbone_source": state["backbone_source"],
            "prediction_identity": identifiers,
            "readout_config": state["readout_config"],
            "allowed_prediction_splits": allowed,
            "classes": config.classes,
            "split": args.split,
        },
    )


def parser():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--threads", type=int, default=1)
    commands = p.add_subparsers(dest="command", required=True)
    make = commands.add_parser("make-fixture")
    make.add_argument("--output", required=True)
    make.add_argument("--grids", type=int, default=8)
    make.add_argument("--image-size", type=int, default=32)
    verify = commands.add_parser("verify-corpus")
    verify.add_argument("--manifest", required=True)
    verify.add_argument("--image-size", type=int, default=224)
    train = commands.add_parser("train")
    for name in ("manifest", "model-config", "training-config", "output"):
        train.add_argument("--" + name, required=True)
    train.add_argument(
        "--scope",
        choices=("synthetic", "integration", "pilot_early", "pilot_full", "reference"),
        required=True,
    )
    train.add_argument("--admission")
    train.add_argument("--resume")
    train.add_argument("--stop-after-updates", type=int)
    train.add_argument("--detailed-audit", action="store_true")
    train.add_argument("--checkpoint-every-updates", type=int)
    fit = commands.add_parser("fit-readout")
    for name in ("images", "inputs", "labels", "backbone", "readout-config", "output"):
        fit.add_argument("--" + name, required=True)
    fit.add_argument("--groups")
    fit.add_argument("--partitions")
    fit.add_argument("--external-cache")
    predict = commands.add_parser("predict-readout")
    for name in ("images", "inputs", "checkpoint", "expected", "output"):
        predict.add_argument("--" + name, required=True)
    predict.add_argument("--split", choices=("dev", "assessment"), required=True)
    predict.add_argument("--device", default="cpu")
    predict.add_argument("--external-cache")
    reference = commands.add_parser("make-reference")
    reference.add_argument("--model-config", required=True)
    reference.add_argument("--seed", type=int, default=17)
    reference.add_argument("--output", required=True)
    external = commands.add_parser("prepare-dinov2")
    external.add_argument("--cache", required=True)
    external.add_argument("--output", required=True)
    decode = commands.add_parser("extract-video")
    decode.add_argument("--video", required=True)
    decode.add_argument("--video-id", required=True)
    decode.add_argument("--output", required=True)
    audit = commands.add_parser("audit-update")
    for name in ("manifest", "model-config", "training-config", "output"):
        audit.add_argument("--" + name, required=True)
    slots = commands.add_parser("pilot-slots")
    slots.add_argument("--output", required=True)
    resource = commands.add_parser("estimate-resources")
    resource.add_argument("--benchmark", required=True)
    resource.add_argument("--output", required=True)
    split = commands.add_parser("ssv2-partitions")
    split.add_argument("--metadata", required=True)
    split.add_argument("--output", required=True)
    return p


def main(argv=None):
    args = parser().parse_args(argv)
    try:
        if args.threads < 1:
            raise ValueError("threads must be positive")
        torch.set_num_threads(args.threads)
        if args.command == "make-fixture":
            from bullet_time.testing import make_corpus

            if args.grids < 1 or args.image_size < 2:
                raise ValueError("invalid fixture dimensions/count")
            result = {
                "manifest": str(make_corpus(args.output, args.grids, args.image_size).resolve()),
                "synthetic_only": True,
            }
        elif args.command == "make-reference":
            from bullet_time.models.references import save_reference

            result = save_reference(
                build_model(read_config(args.model_config, ModelConfig), args.seed),
                args.output,
                seed=args.seed,
            )
        elif args.command == "prepare-dinov2":
            from bullet_time.models.external import build_dino
            from bullet_time.models.references import save_reference

            result = save_reference(
                build_dino(args.cache, pretrained=True, download=True), args.output, seed=0
            )
        elif args.command == "extract-video":
            from bullet_time.evaluation.video_decode import extract_action_video

            result = extract_action_video(args.video, args.output, args.video_id)
        elif args.command == "verify-corpus":
            result = Corpus(args.manifest, image_size=args.image_size).verify()
        elif args.command == "audit-update":
            from bullet_time.training.audit import audit_update

            if Path(args.output).exists():
                raise ValueError("refuse to overwrite update audit")
            model = read_config(args.model_config, ModelConfig)
            report = audit_update(
                Corpus(args.manifest, image_size=model.image_size),
                model,
                read_config(args.training_config, TrainConfig),
            )
            atomic_json(args.output, report)
            result = {k: v for k, v in report.items() if k != "events"}
        elif args.command == "train":
            result = command_train(args)
        elif args.command == "fit-readout":
            result = command_fit(args)
        elif args.command == "predict-readout":
            result = command_predict(args)
        elif args.command in ("pilot-slots", "estimate-resources"):
            from bullet_time.training.plan import pilot_slots, estimate_resources

            result = (
                pilot_slots()
                if args.command == "pilot-slots"
                else estimate_resources(strict_json(Path(args.benchmark).read_bytes()))
            )
            if Path(args.output).exists():
                raise ValueError("refuse to overwrite plan/report")
            atomic_json(args.output, result)
        else:
            from bullet_time.evaluation.external import ssv2_partitions

            result = ssv2_partitions(strict_json(Path(args.metadata).read_bytes()))
            path = Path(args.output)
            if path.exists():
                raise ValueError("refuse to overwrite partition proposal")
            atomic_json(path, result)
        print(json.dumps(result, indent=2, sort_keys=True, allow_nan=False))
        return 0
    except (ValueError, TypeError, KeyError, OSError, RuntimeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
