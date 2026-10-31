"""Bounded actual complete-pass and checkpoint-tail comparison across all arms."""

from collections import Counter
from dataclasses import asdict, replace
from pathlib import Path
import json
import torch

from bullet_time.loading.schedule import CONDITIONS
from bullet_time.models.video import model_identity
from bullet_time.provenance import atomic_json, digest, identity
from .runner import Runner, code_identity


def state_identity(value):
    """Hash actual optimizer tensors and scalars, without pickle serialization noise."""

    def encode(item):
        if isinstance(item, torch.Tensor):
            tensor = item.detach().cpu().contiguous()
            return {
                "dtype": str(tensor.dtype),
                "shape": list(tensor.shape),
                "sha256": digest(tensor.numpy().tobytes()),
            }
        if isinstance(item, dict):
            return {str(k): encode(v) for k, v in item.items()}
        if isinstance(item, (list, tuple)):
            return [encode(v) for v in item]
        return item

    return identity(encode(value))


def audit_tail_pass(corpus, model, config, output):
    """Execute one whole pass per condition and repeat its tail from a checkpoint.

    The native pilot audit uses 100 grids, 12 full updates and a four-grid tail.
    Smaller fixtures are allowed for code checks, and explicitly identified by
    count/geometry. No updates are skipped or simulated by advancing a counter.
    """
    config.validate()
    model.validate()
    count = len(corpus.grids)
    full, tail = divmod(count, config.grids_per_update)
    if (
        config.recipe != "controlled"
        or model.frames != 16
        or not 1 <= count <= 100
        or full < 1
        or tail == 0
    ):
        raise ValueError(
            "tail audit needs controlled video, at most 100 grids, full and partial updates"
        )
    output = Path(output)
    output.mkdir(parents=True, exist_ok=False)
    steps = full + 1
    run = {
        "schema_version": "bullet-time.tail-audit-run.v1",
        "status": "running",
        "model": asdict(model),
        "training": asdict(config),
        "corpus_sha256": corpus.manifest_sha256,
        "source_sha256": code_identity(),
        "grids": count,
        "full_updates": full,
        "tail_grids": tail,
        "conditions": list(CONDITIONS),
        "completed_conditions": [],
        "scientific_gate_pass": False,
    }
    atomic_json(output / "run.json", run)
    references = []
    conditions = {}
    common_binding = None
    all_grids = Counter(g.grid_id for g in corpus.grids)
    try:
        for condition in CONDITIONS:
            arm = output / condition
            arm.mkdir()
            cfg = replace(config, condition=condition)
            runner = Runner(corpus, model, cfg)
            paired_binding = dict(runner.binding, training=asdict(replace(cfg, condition="view")))
            if common_binding is None:
                common_binding = paired_binding
            if (
                paired_binding != common_binding
                or runner.binding["source_sha256"] != run["source_sha256"]
            ):
                raise ValueError("paired audit source/config/data/runtime binding changed")
            if runner.steps_per_pass != steps or runner.global_step != 0:
                raise ValueError("unexpected initial pass state")
            events = []
            seen = Counter()
            checkpoint = arm / "before-tail.pt"
            with (arm / "updates.jsonl").open("x") as log:
                for step in range(steps):
                    if step == full:
                        runner.save(checkpoint)
                    event = runner.step(detailed_audit=True)
                    grids = config.grids_per_update if step < full else tail
                    targets = (
                        grids
                        * 16
                        * (model.frames // model.tubelet)
                        * int(config.mask_ratio * (model.image_size // model.patch_size) ** 2)
                        * (3 * model.tubelet * model.patch_size**2)
                    )
                    if (
                        event["step"] != step
                        or event["pass_index"] != 0
                        or event["update_index"] != step
                        or event["optimizer_steps"] != step + 1
                        or event["scheduler_steps"] != step + 1
                        or event["teacher_steps"] != 0
                        or len(event["grid_ids"]) != grids
                        or event["clips"] != grids * 16
                        or event["images"] != grids * 256
                        or event["target_values"] != targets
                    ):
                        raise ValueError("complete-pass budget/normalization mismatch")
                    seen.update(event["grid_ids"])
                    signature = {
                        "grid_ids": event["grid_ids"],
                        "exposure_sha256": identity(event["detailed_exposure"]),
                        "target_values": event["target_values"],
                        "learning_rate": event["learning_rate"],
                        "initialization_sha256": runner.initialization_sha256,
                        "optimizer_steps": event["optimizer_steps"],
                        "scheduler_steps": event["scheduler_steps"],
                    }
                    if not conditions:
                        references.append(signature)
                    elif signature != references[step]:
                        raise ValueError(
                            f"actual complete-pass exposure/init/budget mismatch: {condition}"
                        )
                    compact = {k: v for k, v in event.items() if k != "detailed_exposure"}
                    compact["detailed_exposure_sha256"] = signature["exposure_sha256"]
                    log.write(json.dumps(compact, sort_keys=True, allow_nan=False) + "\n")
                    log.flush()
                    events.append(compact)
                    print(
                        f"{condition}: actual update {step + 1}/{steps}, {grids} grids", flush=True
                    )
            if seen != all_grids or runner.global_step != steps:
                raise ValueError("complete pass omitted or repeated grids")
            final_model = model_identity(runner.model)
            final_optimizer = state_identity(runner.optimizer.state_dict())
            del runner
            replay = Runner(corpus, model, cfg)
            replay.resume(checkpoint)
            if replay.global_step != full:
                raise ValueError("tail checkpoint does not follow all full updates")
            repeated = replay.step(detailed_audit=True)
            replay_compact = {k: v for k, v in repeated.items() if k != "detailed_exposure"}
            replay_compact["detailed_exposure_sha256"] = identity(repeated["detailed_exposure"])
            if (
                {k: v for k, v in replay_compact.items() if k != "seconds"}
                != {k: v for k, v in events[-1].items() if k != "seconds"}
                or model_identity(replay.model) != final_model
                or state_identity(replay.optimizer.state_dict()) != final_optimizer
            ):
                raise ValueError(f"tail checkpoint replay differs: {condition}")
            conditions[condition] = {
                "binding": replay.binding,
                "binding_sha256": replay.binding_sha256,
                "actual_pass_updates": steps,
                "replay_updates": 1,
                "tail_grid_ids": events[-1]["grid_ids"],
                "tail_replay_exact": True,
                "final_model_sha256": final_model,
                "final_optimizer_sha256": final_optimizer,
                "updates_sha256": digest((arm / "updates.jsonl").read_bytes()),
                "checkpoint_sha256": digest(checkpoint.read_bytes()),
            }
            atomic_json(arm / "result.json", conditions[condition])
            del replay
            run["completed_conditions"].append(condition)
            atomic_json(output / "run.json", run)
        if (
            code_identity() != run["source_sha256"]
            or digest(corpus.manifest.read_bytes()) != corpus.manifest_sha256
        ):
            raise ValueError("source/manifest changed during complete-pass audit")
        report = {
            "schema_version": "bullet-time.tail-audit.v1",
            "all_conditions_pass": True,
            "grids": count,
            "full_updates_per_condition": full,
            "tail_grids": tail,
            "actual_updates_per_condition": steps,
            "replay_updates_per_condition": 1,
            "pilot_100_grid_layout": count == 100 and config.grids_per_update == 8,
            "corpus_sha256": corpus.manifest_sha256,
            "source_sha256": run["source_sha256"],
            "shared_updates_sha256": identity(references),
            "conditions": conditions,
            "scientific_gate_pass": False,
            "scope": "actual single pass and exact tail replay; no joint split, learning or solvability gate",
        }
        atomic_json(output / "report.json", report)
        run["status"] = "completed"
        atomic_json(output / "run.json", run)
        return report
    except BaseException as exc:
        run.update(status="failed", error=str(exc))
        atomic_json(output / "run.json", run)
        raise
