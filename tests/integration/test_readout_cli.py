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
    expected[0]["run_id"] = "incorrect-run"
    inventory.write_text(json.dumps(expected))
    assert "actual run/checkpoint" in run(*common, "--output", tmp_path / "wrong-run", ok=False)
    assert not (tmp_path / "wrong-run").exists()
