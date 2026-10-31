from copy import deepcopy
from pathlib import Path
import json
import shutil

import pytest

from bullet_time.evaluation import assessment_contract as contract
from bullet_time.provenance import identity, atomic_json

SNAPSHOT = Path(__file__).resolve().parents[2] / "reports/data/audit-snapshots/diagnostic-dev-v1"


def records():
    fit = json.loads((SNAPSHOT / "fit.json").read_bytes())
    metadata = json.loads((SNAPSHOT / "predictions/run.json").read_bytes())
    return fit, metadata


def recipe(fit, meta):
    return contract.fit_recipe(
        fit,
        inference_execution=meta["inference_execution"],
        input_sha256=meta["input_sha256"],
        image_manifest_sha256=meta["image_manifest_sha256"],
    )


def design(fit):
    return dict(
        task_id=fit["config"]["task"],
        label_budget=fit["train_episodes"],
        readout_seed=fit["config"]["seed"],
        pretraining_seed=fit["backbone_source"]["binding"]["training"]["seed"],
        horizon="0.5",
        model_kind="diagnostic",
        condition="sequence",
        objective="supervised",
        checkpoint_pass=0,
        corpus_sha256="0" * 64,
        readout_recipe_sha256=identity({k: v for k, v in fit["config"].items() if k != "seed"}),
    )


def verify(root=SNAPSHOT, *, declared=None, locked=None, split="dev"):
    fit, meta = records()
    return contract.verify_predictor(
        root / "fit.json",
        root / "predictions",
        root / "expected.json",
        declared or design(fit),
        locked or identity(recipe(fit, meta)),
        split=split,
    )


def test_historical_actual_export_validates_without_labels_or_checkpoint_access(tmp_path):
    # Real dev metadata/CSV, not a new fit or assessment outcome. Deliberately copy no labels.
    shutil.copytree(SNAPSHOT / "predictions", tmp_path / "predictions")
    for name in ("fit.json", "expected.json"):
        shutil.copyfile(SNAPSHOT / name, tmp_path / name)
    result = verify(tmp_path)
    assert result["complete"] and result["expected_rows"] == 16
    assert not result["assessment_authorized"] and not result["scientific_gate_pass"]
    assert result["predictor"]["prediction_identity"] == records()[1]["prediction_identity"]
    assert result["execution"]["contract_sha256"]
    assert set(result["artifacts"]) == {
        "fit",
        "expected",
        "run.json",
        "coverage.json",
        "predictions.csv",
    }


def test_fit_outcomes_can_change_but_all_known_recipe_fields_remain_locked():
    fit, meta = records()
    original = recipe(fit, meta)
    changed = deepcopy(fit)
    changed.update(
        history=[], selected_dev_loss=100.0, model_sha256="1" * 64, frozen_backbone_sha256="2" * 64
    )
    assert recipe(changed, meta) == original
    for key in contract.FIXED_FIT_FIELDS:
        changed = deepcopy(fit)
        changed[key] = {"changed": True}
        assert recipe(changed, meta) != original, key
    altered = deepcopy(meta)
    altered["input_sha256"] = "0" * 64
    assert recipe(fit, altered) != original


def test_only_future_learned_backbone_hash_may_be_unknown():
    fit, meta = records()
    original = recipe(fit, meta)
    fit["backbone_source"]["checkpoint_sha256"] = "0" * 64
    assert recipe(fit, meta) != original  # existing external reference must stay pinned
    fit["backbone_source"]["binding"].pop("reference_status")
    learned = recipe(fit, meta)
    fit["backbone_source"].pop("checkpoint_sha256")
    assert recipe(fit, meta) == learned  # can plan before unknown learned bytes exist
    fit["backbone_source"]["checkpoint_sha256"] = "1" * 64
    assert recipe(fit, meta) == learned
    fit["backbone_source"]["global_step"] += 1
    assert recipe(fit, meta) != learned


@pytest.mark.parametrize(
    "change",
    [
        lambda d: d.update(task_id="order"),
        lambda d: d.update(readout_seed=102),
        lambda d: d.update(label_budget=600),
        lambda d: d.update(horizon="1.0"),
    ],
)
def test_expected_keys_must_match_declared_slot(change):
    fit, _ = records()
    declared = design(fit)
    change(declared)
    with pytest.raises(ValueError, match="expected"):
        verify(declared=declared)


def test_assessment_cannot_relabel_existing_dev_predictions():
    with pytest.raises(ValueError, match="split"):
        verify(split="assessment")
    with pytest.raises(ValueError, match="pre-H3 lock"):
        verify(locked="0" * 64)


@pytest.mark.parametrize(
    "filename", ["expected.json", "predictions/predictions.csv", "predictions/coverage.json"]
)
def test_artifact_mutation_during_verification_is_rejected(tmp_path, monkeypatch, filename):
    shutil.copytree(SNAPSHOT / "predictions", tmp_path / "predictions")
    for name in ("fit.json", "expected.json"):
        shutil.copyfile(SNAPSHOT / name, tmp_path / name)
    original = contract.read_predictions

    def mutate(*args, **kwargs):
        result = original(*args, **kwargs)
        path = tmp_path / filename
        path.write_bytes(path.read_bytes() + b"\n")
        return result

    monkeypatch.setattr(contract, "read_predictions", mutate)
    with pytest.raises(ValueError, match="artifacts changed"):
        verify(tmp_path)


def test_inference_source_cannot_be_missing_or_different(tmp_path):
    shutil.copytree(SNAPSHOT / "predictions", tmp_path / "predictions")
    for name in ("fit.json", "expected.json"):
        shutil.copyfile(SNAPSHOT / name, tmp_path / name)
    path = tmp_path / "predictions/run.json"
    meta = json.loads(path.read_bytes())
    meta["inference_execution"]["source_sha256"] = "0" * 64
    atomic_json(path, meta)
    with pytest.raises(ValueError, match="inference consumer"):
        verify(tmp_path)


def test_self_consistent_refit_metadata_cannot_change_locked_recipe(tmp_path):
    from bullet_time.provenance import digest

    shutil.copytree(SNAPSHOT / "predictions", tmp_path / "predictions")
    for name in ("fit.json", "expected.json"):
        shutil.copyfile(SNAPSHOT / name, tmp_path / name)
    fit, meta = records()
    fit["config"]["epochs"] += 1
    fit["training_episode_ids"].reverse()
    atomic_json(tmp_path / "fit.json", fit)
    meta["readout_config"] = fit["config"]
    meta["fit_sha256"] = digest((tmp_path / "fit.json").read_bytes())
    atomic_json(tmp_path / "predictions/run.json", meta)
    with pytest.raises(ValueError, match="pre-H3 lock"):
        verify(tmp_path)


def test_expected_input_commitment_can_lock_before_future_predictor_bytes():
    rows = json.loads((SNAPSHOT / "expected.json").read_bytes())
    original = contract.expected_input_identity(rows)
    changed = deepcopy(rows)
    for row in changed:
        row.update(run_id="a" * 64, checkpoint_id="b" * 64, label_budget=600, readout_seed=103)
    assert contract.expected_input_identity(reversed(changed)) == original
    changed[0]["target_reference_sha256"] = "0" * 64
    assert contract.expected_input_identity(changed) != original
    with pytest.raises(ValueError, match="unique"):
        contract.expected_input_identity(rows + rows[:1])


def test_verifier_source_change_during_validation_is_rejected(monkeypatch):
    original = contract.verifier_binding
    calls = 0

    def changed_binding():
        nonlocal calls
        calls += 1
        record = original()
        if calls == 2:
            record["contract_sha256"] = "0" * 64
        return record

    monkeypatch.setattr(contract, "verifier_binding", changed_binding)
    with pytest.raises(ValueError, match="source/runtime changed"):
        verify()
