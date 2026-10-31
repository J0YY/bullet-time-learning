"""Public-only inventories; synthetic assessment, never relabeled development data."""

import json
from pathlib import Path
import subprocess
import sys

import pytest

from bullet_time.evaluation.assessment_inputs import compile_inputs
from bullet_time.generation.assessment_export import prepare_assessment
from bullet_time.provenance import atomic_json, digest
from readouts.test_assessment_export import source_fixture, lines


@pytest.fixture
def prepared(tmp_path):
    source = tmp_path / "source"
    source_fixture(source)
    output = tmp_path / "prepared"
    prepare_assessment(source, output)
    return output / "public"


def reseal(public):
    """Test coherent malformed producer metadata, beyond simple byte tampering."""
    receipt = json.loads((public / "preparation.json").read_text())
    receipt["public_inventory"] = {
        name: digest((public / name).read_bytes()) for name in receipt["public_inventory"]
    }
    atomic_json(public / "preparation.json", receipt)


def test_compile_without_private_or_source_access(prepared, monkeypatch):
    original = Path.open
    forbidden = [prepared.parent / "private", prepared.parent.parent / "source"]

    def guarded(path, *args, **kwargs):
        assert not any(path.resolve().is_relative_to(p) for p in forbidden)
        return original(path, *args, **kwargs)

    monkeypatch.setattr(Path, "open", guarded)
    report = compile_inputs(prepared, allow_partial=True)
    assert not report["pilot_counts_complete"]
    assert not report["assessment_authorized"] and not report["scientific_gate_pass"]
    assert {t: c["queries"] for t, c in report["counts"].items()} == {
        "collision": 2,
        "order": 2,
        "tracking": 3,
    }
    assert {t: c["groups"] for t, c in report["counts"].items()} == {
        "collision": 1,
        "order": 1,
        "tracking": 1,
    }
    assert compile_inputs(prepared, allow_partial=True) == report
    with pytest.raises(ValueError, match="400 episodes"):
        compile_inputs(prepared)


@pytest.mark.parametrize("mutation", ["missing", "extra", "hash", "symlink", "private"])
def test_public_inventory_rejects_mutation_before_compilation(prepared, mutation):
    if mutation == "missing":
        (prepared / "groups.json").unlink()
    elif mutation == "extra":
        (prepared / "extra.json").write_text("{}")
    elif mutation == "hash":
        with (prepared / "groups.json").open("a") as f:
            f.write("\n")
    elif mutation == "symlink":
        (prepared / "alias").symlink_to(prepared.parent / "private", target_is_directory=True)
    else:
        receipt = json.loads((prepared / "preparation.json").read_text())
        receipt["public_inventory"]["../private/labels.jsonl"] = "0" * 64
        atomic_json(prepared / "preparation.json", receipt)
    with pytest.raises(ValueError, match="inventory|changed|symlinks|private"):
        compile_inputs(prepared, allow_partial=True)


@pytest.mark.parametrize(
    "mutation",
    [
        "missing_commitment",
        "duplicate_commitment",
        "wrong_split",
        "wrong_group",
        "no_primary",
        "tracking_gap",
    ],
)
def test_coherent_metadata_errors_fail(prepared, mutation):
    if mutation in ("missing_commitment", "duplicate_commitment", "wrong_split"):
        path = prepared / "target-commitments.json"
        rows = json.loads(path.read_text())
        if mutation == "missing_commitment":
            rows.pop()
        elif mutation == "duplicate_commitment":
            rows.append(rows[0])
        else:
            rows[0]["split"] = "dev"
        atomic_json(path, rows)
    elif mutation == "wrong_group":
        path = prepared / "groups.json"
        data = json.loads(path.read_text())
        row = next(r for r in data["records"] if r["task_id"] == "collision")
        row["group_id"] = "0" * 64
        atomic_json(path, data)
    else:
        path = prepared / "evaluation.jsonl"
        rows = [json.loads(line) for line in path.read_text().splitlines()]
        if mutation == "no_primary":
            row = next(r for r in rows if r["task_id"] == "collision")
            old_horizon, new_horizon = "0.5", "1.0"
            row["horizon_seconds"] = 1.0
        else:
            row = next(
                r for r in rows if r["task_id"] == "tracking" and r["prediction_frame"] == 17
            )
            old_horizon, new_horizon = "17", "18"
            row["prediction_frame"] = 18
            row["observed_frame_indices"] = list(range(3, 19))
            row["reference_frame"] = 3
        lines(path, rows)
        target_path = prepared / "target-commitments.json"
        targets = json.loads(target_path.read_text())
        target = next(
            r
            for r in targets
            if r["episode_id"] == row["episode_id"] and r["horizon_or_frame"] == old_horizon
        )
        target["horizon_or_frame"] = new_horizon
        atomic_json(target_path, targets)
    reseal(prepared)
    with pytest.raises(ValueError):
        compile_inputs(prepared, allow_partial=True)


def test_only_primary_horizons_selected_but_all_commitments_required(tmp_path):
    source = tmp_path / "source"
    rows, labels, _ = source_fixture(source)
    classification = [r for r in rows if r["task_id"] != "tracking"]
    targets = [r for r in labels if r["task_id"] != "tracking"]
    for horizon in (0.25, 1.0):
        rows.extend(dict(r, horizon_seconds=horizon) for r in classification)
        labels.extend(dict(r, horizon_or_frame=str(horizon)) for r in targets)
    lines(source / "inputs/evaluation.jsonl", rows)
    lines(source / "private/labels.jsonl", labels)
    prepare_assessment(source, tmp_path / "prepared")
    public = tmp_path / "prepared/public"
    report = compile_inputs(public, allow_partial=True)
    assert all(len(report["templates"][t]) == 2 for t in ("collision", "order"))
    commitments = json.loads((public / "target-commitments.json").read_text())
    commitments = [r for r in commitments if r["horizon_or_frame"] != "0.25"]
    atomic_json(public / "target-commitments.json", commitments)
    reseal(public)
    with pytest.raises(ValueError, match="all declared inputs"):
        compile_inputs(public, allow_partial=True)


def test_concurrent_rgb_mutation_rejected(prepared, monkeypatch):
    from bullet_time.evaluation.assessment_inputs import ImageStore

    original = ImageStore.read
    called = False

    def mutate(store, image):
        nonlocal called
        result = original(store, image)
        if not called:
            called = True
            path = store.root / store.images[image]["rgb_path"]
            path.write_bytes(path.read_bytes() + b"\n")
        return result

    monkeypatch.setattr(ImageStore, "read", mutate)
    with pytest.raises(ValueError, match="changed"):
        compile_inputs(prepared, allow_partial=True)


def test_cli_partial_inventory_and_immutable_output(prepared, tmp_path):
    output = tmp_path / "inventory.json"
    command = [
        sys.executable,
        "scripts/scoring/assessment_inputs.py",
        "--public",
        str(prepared),
        "--output",
        str(output),
        "--allow-partial",
    ]
    run = subprocess.run(command, capture_output=True, text=True, check=True)
    assert not json.loads(run.stdout)["assessment_authorized"]
    before = output.read_bytes()
    assert subprocess.run(command, capture_output=True).returncode != 0
    assert output.read_bytes() == before
    command[command.index(str(output))] = str(prepared / "inventory.json")
    assert subprocess.run(command, capture_output=True).returncode != 0
    assert not (prepared / "inventory.json").exists()


def test_full_counts_are_not_scientific_admission(prepared):
    from bullet_time.provenance import identity

    rows = [json.loads(line) for line in (prepared / "evaluation.jsonl").read_text().splitlines()]
    groups = json.loads((prepared / "groups.json").read_text())
    targets = json.loads((prepared / "target-commitments.json").read_text())
    expanded, memberships, commitments = [], [], []
    for task, copies in (("collision", 200), ("order", 200), ("tracking", 400)):
        for index in range(copies):
            for row in (r for r in rows if r["task_id"] == task):
                expanded.append(dict(row, episode_id=identity([row["episode_id"], index])))
            for row in (r for r in groups["records"] if r["task_id"] == task):
                memberships.append(
                    dict(
                        row,
                        episode_id=identity([row["episode_id"], index]),
                        group_id=identity([row["group_id"], index]),
                    )
                )
            for row in (r for r in targets if r["task_id"] == task):
                commitments.append(dict(row, episode_id=identity([row["episode_id"], index])))
    lines(prepared / "evaluation.jsonl", expanded)
    atomic_json(prepared / "groups.json", dict(groups, records=memberships))
    atomic_json(prepared / "target-commitments.json", commitments)
    reseal(prepared)
    report = compile_inputs(prepared)
    assert report["pilot_counts_complete"]
    assert all(c["episodes"] == 400 for c in report["counts"].values())
    assert not report["assessment_authorized"] and not report["scientific_gate_pass"]
