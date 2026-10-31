import json
import subprocess
import sys
from copy import deepcopy
import pytest
from bullet_time.provenance import atomic_json
from bullet_time.evaluation.score_plan import run_plan
from fixtures.scoring.factory import make_plan


def test_complete_plan_cli_and_missing_run_ledger(tmp_path):
    path = make_plan(tmp_path / "plan")
    output = tmp_path / "result.json"
    subprocess.run(
        [sys.executable, "scripts/scoring/score.py", "--plan", str(path), "--output", str(output)],
        check=True,
        capture_output=True,
        text=True,
    )
    report = json.loads(output.read_text())
    assert report["complete"] and report["planned_slots"] == report["complete_slots"] == 18
    assert report["contrasts"]["time-view"]["inference"]["n_paired_pretraining_seeds"] == 3
    assert report["contrasts"]["time-view"]["inference"]["paired_differences"] == [0, 0.5, 0]
    assert not report["scientific_claim_pass"]
    plan = json.loads(path.read_text())
    plan["slots"][0]["predictions"] = "not-delivered"
    atomic_json(path, plan)
    result = run_plan(path, tmp_path / "incomplete.json")
    assert not result["complete"] and result["complete_slots"] == 17
    assert result["multiple_individual_claims"] is None


def test_missing_design_cell_and_duplicate_slot_fail_correctly(tmp_path):
    path = make_plan(tmp_path / "plan")
    plan = json.loads(path.read_text())
    incomplete = deepcopy(plan)
    incomplete["slots"].pop()
    atomic_json(path, incomplete)
    result = run_plan(path, tmp_path / "incomplete.json")
    assert not result["complete"] and result["contrasts"]["time-view"]["missing_seed_cells"][
        "left"
    ] == [[43, 103]]
    plan["slots"].append(plan["slots"][0])
    atomic_json(path, plan)
    with pytest.raises(ValueError, match="duplicate slot"):
        run_plan(path, tmp_path / "bad.json")


def test_plan_binds_actual_inputs_and_rejects_assessment_before_access(tmp_path):
    path = make_plan(tmp_path / "plan")
    plan = json.loads(path.read_text())
    plan["labels"]["sha256"] = "0" * 64
    atomic_json(path, plan)
    with pytest.raises(ValueError, match="hash mismatch"):
        run_plan(path, tmp_path / "bad.json")
    plan["split"] = "assessment"
    plan["labels"]["path"] = "missing"
    atomic_json(path, plan)
    with pytest.raises(ValueError, match="release workflow"):
        run_plan(path, tmp_path / "bad.json")


def test_unfitted_slot_is_retained_without_inventing_predictor_keys(tmp_path):
    path = make_plan(tmp_path / "plan")
    plan = json.loads(path.read_text())
    plan["slots"][0]["expected"] = None
    plan["slots"][0]["predictions"] = "not-fitted-yet"
    atomic_json(path, plan)
    result = run_plan(path, tmp_path / "incomplete.json")
    assert result["planned_slots"] == 18 and result["complete_slots"] == 17
    assert result["slots"]["view-17-101"]["reason"] == "fit/predictor inventory not delivered"
    from bullet_time.provenance import digest

    receipt = path.parent / "not-fitted-yet/failure.json"
    atomic_json(receipt, {"status": "failed", "error": "OOM during fit"})
    result = run_plan(path, tmp_path / "failed.json")
    failed = result["slots"]["view-17-101"]
    assert failed["reason"] == "OOM during fit" and not failed["rows"]
    assert failed["provenance"] == {
        "state": "failed_run",
        "failure_sha256": digest(receipt.read_bytes()),
    }
    atomic_json(receipt, {"status": "failed"})
    with pytest.raises(ValueError, match="malformed failure"):
        run_plan(path, tmp_path / "malformed.json")


def test_real_fit_metadata_controls_pairing_and_recipe_claims():
    from dataclasses import asdict
    from bullet_time.evaluation.training import ReadoutConfig
    from bullet_time.evaluation.score_plan import validate_fit
    from bullet_time.provenance import identity

    config = asdict(ReadoutConfig(label_budget=300))
    binding = {"training": {"seed": 17}, "reference_status": "untrained", "model": {}}
    source = {
        "binding": binding,
        "run_id": identity(binding),
        "checkpoint_sha256": "2" * 64,
        "global_step": 0,
    }
    fit = {
        "config": config,
        "backbone_source": source,
        "train_episodes": 300,
        "execution": {"source_sha256": "3" * 64},
        "training_episode_ids": [f"train-{i}" for i in range(300)],
        "input_sha256": "5" * 64,
        "image_manifest_sha256": "6" * 64,
        "label_sha256": "7" * 64,
        "selection": None,
        "dev_episodes": 200,
        "horizon_seconds": 0.5,
    }
    ids = {"run_id": source["run_id"], "checkpoint_id": source["checkpoint_sha256"]}
    meta = {
        "fit_sha256": "4" * 64,
        "backbone_source": source,
        "readout_config": config,
        "fit_execution": fit["execution"],
        "prediction_identity": ids,
        "inference_execution": {"source_sha256": "3" * 64},
        "input_sha256": "8" * 64,
        "image_manifest_sha256": "6" * 64,
    }
    slot = {
        "model_kind": "untrained",
        "condition": "untrained",
        "objective": "untrained",
        "checkpoint_pass": 0,
        "corpus_sha256": "0" * 64,
        "pretraining_seed": 17,
        "readout_seed": 101,
        "task_id": "collision",
        "label_budget": 300,
        "horizon": "0.5",
        "readout_recipe_sha256": identity({k: v for k, v in config.items() if k != "seed"}),
    }
    result = validate_fit(slot, ids, fit, meta, "4" * 64)
    assert result["backbone_identity"] == ids
    assert result["readout_training"]["training_episode_ids"] == sorted(fit["training_episode_ids"])
    assert result["readout_training"]["label_sha256"] == fit["label_sha256"]
    assert result["pretraining_recipe"]["training"] == {}
    assert result["readout_execution"]["fit"] == fit["execution"]
    assert result["readout_execution"]["inference"] == meta["inference_execution"]
    assert result["inference_inputs"]["input_sha256"] == meta["input_sha256"]
    for key, value, match in [
        ("pretraining_seed", 29, "paired seed"),
        ("label_budget", 100, "budget"),
        ("condition", "time", "experimental slot"),
        ("horizon", "0.25", "horizon"),
        ("readout_recipe_sha256", "f" * 64, "recipe"),
    ]:
        with pytest.raises(ValueError, match=match):
            validate_fit({**slot, key: value}, ids, fit, meta, "4" * 64)


def test_separate_horizons_may_share_backbone_prediction_identity(tmp_path):
    from bullet_time.provenance import digest, identity
    from bullet_time.evaluation.export import KEY, write_predictions

    path = make_plan(tmp_path / "plan")
    plan = json.loads(path.read_text())
    labels_path = path.parent / plan["labels"]["path"]
    labels = [json.loads(line) for line in labels_path.read_text().splitlines()]
    extra_labels = [{**r, "horizon_or_frame": "0.25"} for r in labels]
    labels_path.write_text("".join(json.dumps(r) + "\n" for r in labels + extra_labels))
    plan["labels"]["sha256"] = digest(labels_path.read_bytes())
    slot = deepcopy(plan["slots"][0])
    slot.update(slot_id="view-17-101-quarter", horizon="0.25", predictions="quarter/predictions")
    rows = json.loads((path.parent / slot["expected"]["path"]).read_text())
    for row, label in zip(rows, extra_labels, strict=True):
        row.update(horizon_or_frame="0.25", target_reference_sha256=identity(label))
    expected_path = path.parent / "quarter/expected.json"
    atomic_json(expected_path, rows)
    slot["expected"] = {
        "path": "quarter/expected.json",
        "sha256": digest(expected_path.read_bytes()),
    }
    predictions = [
        {**{k: r[k] for k in KEY}, "status": "ok", "error": "", "contact_probability": 0.5}
        for r in rows
    ]
    write_predictions(path.parent / slot["predictions"], rows, predictions, {"scope": "synthetic"})
    plan["slots"].append(slot)
    atomic_json(path, plan)
    result = run_plan(path, tmp_path / "result.json")
    assert result["complete"] and result["complete_slots"] == 19
