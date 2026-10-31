import json
from dataclasses import asdict, replace
import pytest
from bullet_time.models.video import build_model
from bullet_time.models.references import save_reference
from bullet_time.evaluation.training import ReadoutConfig, Targets
from bullet_time.evaluation.inputs import EvaluationInputs
from bullet_time.cli import load_backbone
from fixtures.consumer.evaluation import fixtures, TINY
from test_cli import run


@pytest.mark.parametrize(
    "kind,mode", [("frozen", "sequence"), ("diagnostic", "sequence"), ("diagnostic", "final_frame")]
)
def test_reference_fit_predict_cli_and_wrong_run_rejection(tmp_path, kind, mode):
    path, store, base = fixtures(tmp_path / "data")
    inputs = []
    labels = []
    groups = []
    for split in ("train", "dev"):
        for branch in (0, 1):
            episode = f"{split}-{branch}"
            inputs.append(dict(base, episode_id=episode, split=split))
            labels.append(
                dict(
                    schema_version="bullet-time.labels.v1",
                    task_id="collision",
                    episode_id=episode,
                    query_id="query",
                    horizon_or_frame="0.5",
                    split=split,
                    target={"contact": branch},
                )
            )
            groups.append(
                dict(episode_id=episode, task_id="collision", split=split, group_id=split)
            )
    path.write_text("".join(json.dumps(r) + "\n" for r in inputs))
    label_path = tmp_path / "labels.jsonl"
    label_path.write_text("".join(json.dumps(r) + "\n" for r in labels))
    group_path = tmp_path / "groups.json"
    group_path.write_text(
        json.dumps(dict(schema_version="bullet-time.evaluation-groups.v1", records=groups))
    )
    backbone = tmp_path / "untrained.pt"
    save_reference(
        build_model(replace(TINY, frames=1, tubelet=1) if kind == "diagnostic" else TINY, 17),
        backbone,
    )
    _, source = load_backbone(backbone)
    assert source["assessment_eligible"]
    config = tmp_path / "head.json"
    config.write_text(
        json.dumps(
            asdict(
                ReadoutConfig(
                    image_size=32, width=24, heads=3, epochs=1, label_budget=2, kind=kind, mode=mode
                )
            )
        )
    )
    fitted = run(
        "fit-readout",
        "--images",
        store.path,
        "--inputs",
        path,
        "--labels",
        label_path,
        "--groups",
        group_path,
        "--backbone",
        backbone,
        "--readout-config",
        config,
        "--output",
        tmp_path / "fit",
    )
    dev = tmp_path / "dev.jsonl"
    dev.write_text("".join(json.dumps(r) + "\n" for r in inputs if r["split"] == "dev"))
    all_inputs = EvaluationInputs(path, store)
    targets = Targets(label_path, all_inputs)
    expected = []
    for e in all_inputs.examples:
        if e.split != "dev":
            continue
        expected.append(
            dict(
                run_id=fitted["prediction_identity"]["run_id"],
                checkpoint_id=fitted["prediction_identity"]["checkpoint_id"],
                task_id="collision",
                label_budget=2,
                readout_seed=101,
                episode_or_video_id=e.episode_id,
                query_id=e.query_id,
                horizon_or_frame=e.key[-1],
                split="dev",
                scene_family="fixture",
                pair_group_id="dev",
                prediction_role="primary",
                target_reference_sha256=targets.reference_hash(e),
            )
        )
    inventory = tmp_path / "expected.json"
    inventory.write_text(json.dumps(expected))
    common = [
        "predict-readout",
        "--images",
        store.path,
        "--inputs",
        dev,
        "--checkpoint",
        fitted["checkpoint"],
        "--expected",
        inventory,
        "--split",
        "dev",
    ]
    assert run(*common, "--output", tmp_path / "predictions")["complete"]
    # Consume actual fit/inference receipts through the development scorer. This
    # remains a synthetic-data integration, with no fitted recipe inferred by hand.
    from bullet_time.evaluation.score_plan import run_plan
    from bullet_time.provenance import atomic_json, digest, identity

    dev_labels = tmp_path / "dev-labels.jsonl"
    dev_labels.write_text("".join(json.dumps(r) + "\n" for r in labels if r["split"] == "dev"))
    cfg = json.loads(config.read_text())

    def bound(p):
        return {"path": p.relative_to(tmp_path).as_posix(), "sha256": digest(p.read_bytes())}

    slot = dict(
        slot_id="actual-fit",
        condition=mode if kind == "diagnostic" else "untrained",
        objective="supervised" if kind == "diagnostic" else "untrained",
        task_id="collision",
        horizon="0.5",
        label_budget=2,
        checkpoint_pass=0,
        model_kind="diagnostic" if kind == "diagnostic" else "untrained",
        corpus_sha256="0" * 64,
        readout_recipe_sha256=identity({k: v for k, v in cfg.items() if k != "seed"}),
        pretraining_seed=17,
        readout_seed=101,
        expected=bound(inventory),
        predictions="predictions",
        fit=bound(tmp_path / "fit/fit.json"),
    )
    plan_path = tmp_path / "scoring-plan.json"
    atomic_json(
        plan_path,
        dict(
            schema_version="bullet-time.scoring-plan.v1",
            scope="development",
            split="dev",
            families=["fixture"],
            classes=174,
            labels=bound(dev_labels),
            groups=bound(group_path),
            pretraining_seeds=[17, 29],
            readout_seeds=[101, 102, 103],
            slots=[slot],
            contrasts=[],
            bootstrap={"replicates": 100, "seed": 99},
        ),
    )
    scored = run_plan(plan_path, tmp_path / "scored.json")
    assert scored["complete"] and scored["slots"]["actual-fit"]["inference_inputs"][
        "input_sha256"
    ] == digest(dev.read_bytes())
    expected[0]["run_id"] = "incorrect-run"
    inventory.write_text(json.dumps(expected))
    assert "actual run/checkpoint" in run(*common, "--output", tmp_path / "wrong-run", ok=False)
    assert not (tmp_path / "wrong-run").exists()

    if kind == "frozen":
        import torch
        from bullet_time.provenance import digest

        altered = tmp_path / "wrong-source.pt"
        state = torch.load(fitted["checkpoint"], map_location="cpu", weights_only=True)
        state["fit_execution"]["source_sha256"] = "f" * 64
        torch.save(state, altered)
        metadata = json.loads((tmp_path / "fit/readout.pt.json").read_text())
        metadata["sha256"] = digest(altered.read_bytes())
        altered.with_suffix(".pt.json").write_text(json.dumps(metadata))
        wrong_source = common.copy()
        wrong_source[wrong_source.index("--checkpoint") + 1] = altered
        assert "source differs" in run(
            *wrong_source, "--output", tmp_path / "wrong-source", ok=False
        )
