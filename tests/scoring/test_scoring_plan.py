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
    }
    ids = {"run_id": source["run_id"], "checkpoint_id": source["checkpoint_sha256"]}
    meta = {
        "fit_sha256": "4" * 64,
        "backbone_source": source,
        "readout_config": config,
        "fit_execution": fit["execution"],
        "prediction_identity": ids,
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
        "readout_recipe_sha256": identity({k: v for k, v in config.items() if k != "seed"}),
    }
    validate_fit(slot, ids, fit, meta, "4" * 64)
    for key, value, match in [
        ("pretraining_seed", 29, "paired seed"),
        ("label_budget", 100, "budget"),
        ("condition", "time", "experimental slot"),
        ("readout_recipe_sha256", "f" * 64, "recipe"),
    ]:
        with pytest.raises(ValueError, match=match):
            validate_fit({**slot, key: value}, ids, fit, meta, "4" * 64)
