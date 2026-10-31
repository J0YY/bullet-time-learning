from copy import deepcopy
import json

import pytest

from bullet_time.generation import evaluation_motion as motion
from bullet_time.generation import evaluation_selection as selection
from bullet_time.provenance import atomic_json, digest


def test_global_reservation_with_cross_task_collisions_and_reordered_json(monkeypatch):
    def candidate(seed, index, task):
        return dict(
            task=task,
            index=index,
            groups={
                "asset": str(index),
                "trajectory": f"{task}-{index}",
                "configuration": f"{task}-{index}",
            },
            assigned_pools={
                kind: "train" if index % 2 == 0 else "dev"
                for kind in ["asset", "trajectory", "configuration"]
            },
            frames={"one": {}},
        )

    monkeypatch.setattr(motion, "forecast_candidate", candidate)
    monkeypatch.setattr(
        motion, "tracking_candidate", lambda seed, index: candidate(seed, index, "tracking")
    )
    counts = {task: {"train": 1, "dev": 1} for task in ("collision", "order", "tracking")}
    requests, evidence = motion.select_collection(17, counts)
    assert [r["index"] for r in requests] == list(range(6))
    assert selection.check_collection(requests, counts)["unique_prototypes"]["asset"] == 6
    reordered = {
        task: dict(reversed(list(row.items()))) for task, row in reversed(list(counts.items()))
    }
    assert motion.select_collection(17, reordered) == (requests, evidence)
    invalid = deepcopy(requests)
    invalid[-1]["groups"]["asset"] = requests[0]["groups"]["asset"]
    with pytest.raises(ValueError, match="duplicate asset"):
        selection.check_collection(invalid, counts)
    with pytest.raises(ValueError, match="train/dev"):
        motion.select_collection(17, {task: {"train": 1, "assessment": 1} for task in counts})


def test_reservation_skips_real_candidate_without_mutating_prior_inventory():
    original, _ = motion.select_groups(71, "train", 1, "collision")
    reserved = {
        kind: {original[0]["groups"][kind]} for kind in ("asset", "trajectory", "configuration")
    }
    before = deepcopy(reserved)
    selected, _ = motion.select_groups(71, "train", 1, "collision", reserved=reserved)
    assert reserved == before
    assert all(selected[0]["groups"][kind] not in reserved[kind] for kind in reserved)
    with pytest.raises(ValueError, match="insufficient"):
        motion.select_groups(
            71, "train", 1, "collision", limit=original[0]["index"] + 1, reserved=reserved
        )


def test_pilot_episode_units_are_complete_groups_and_assessment_is_not_selected():
    pilot = selection.read_pilot()
    counts = selection.counts_from_pilot(pilot)
    assert counts == {
        "collision": {"train": 300, "dev": 100},
        "order": {"train": 300, "dev": 100},
        "tracking": {"train": 600, "dev": 200},
    }
    for key, value in [("train", 601), ("pair_size", 1), ("pair_size", True), ("dev", 0)]:
        bad = deepcopy(pilot)
        bad["evaluation_sets"]["collision"][key] = value
        with pytest.raises(ValueError):
            selection.counts_from_pilot(bad)


def test_selection_snapshot_reconstructs_and_rejects_rewritten_counts_or_bytes(
    tmp_path, monkeypatch
):
    pilot = selection.read_pilot()
    for record in pilot["evaluation_sets"].values():
        record.update(train=record["pair_size"], dev=record["pair_size"])
    monkeypatch.setattr(selection, "read_pilot", lambda: deepcopy(pilot))
    original = selection.subprocess.check_output

    def git(args, **kwargs):
        if args == ["git", "status", "--porcelain"]:
            return b""
        return original(args, **kwargs)

    monkeypatch.setattr(selection.subprocess, "check_output", git)
    output = tmp_path / "collection"
    report = selection.plan_collection(output)
    assert selection.verify_selection(output) == report
    assert report["summary"]["groups"] == 6
    assert not report["summary"]["rendered"]
    with pytest.raises(ValueError, match="overwrite"):
        selection.plan_collection(output)
    path = output / "private/requests.jsonl"
    rows = path.read_bytes().splitlines()
    # Rehashing a tampered request is insufficient: verification reconstructs actual selection.
    changed = json.loads(rows[0])
    changed["index"] += 1
    path.write_bytes(json.dumps(changed).encode() + b"\n" + b"\n".join(rows[1:]) + b"\n")
    report["inventory"]["private/requests.jsonl"] = digest(path.read_bytes())
    atomic_json(output / "selection.json", report)
    with pytest.raises(ValueError, match="reproducible"):
        selection.verify_selection(output)
    report["groups_per_task"]["collision"]["train"] = 2
    atomic_json(output / "selection.json", report)
    with pytest.raises(ValueError, match="counts/seed"):
        selection.verify_selection(output)
