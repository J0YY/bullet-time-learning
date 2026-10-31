from copy import deepcopy

import pytest

from bullet_time.generation import evaluation_bundle as bundle
from bullet_time.generation.evaluation_motion import select_collection
from bullet_time.provenance import atomic_json, digest


def test_progressive_counts_and_prefixes_preserve_complete_groups():
    one = bundle.progressive_plan("a" * 64, 1)
    eight = bundle.progressive_plan("a" * 64, 8)
    full = bundle.progressive_plan("a" * 64, 600)
    for plan in (one, eight, full):
        bundle.check_plan(plan)
    assert full["groups_per_task"]["collision"] == {"train": 300, "dev": 100}
    assert full["groups_per_task"]["tracking"] == {"train": 600, "dev": 200}
    rows, stats = select_collection(
        one["seed"], {task: {"train": 2, "dev": 2} for task in one["tasks"]}
    )
    selected, observed_stats, retained_full = bundle.select_for_capture(
        one, full_requests=rows, full_selection=stats
    )
    assert len(selected) == 6 and observed_stats == stats and retained_full == rows
    assert bundle.check_lineage(selected, one) == {
        kind: 6 for kind in ("asset", "trajectory", "configuration")
    }
    assert sum(1 if r["task"] == "tracking" else 2 for r in selected) == 10
    assert sum(len(r["frames"]) for r in selected) == 150
    assert all(
        r is next(x for x in rows if (x["task"], x["split"]) == (r["task"], r["split"]))
        for r in selected
    )
    for limit in (0, 2, True, 1000):
        with pytest.raises(ValueError):
            bundle.progressive_plan("a" * 64, limit)
    bad = deepcopy(one)
    bad["groups_per_task"]["collision"]["train"] = 2
    with pytest.raises(ValueError):
        bundle.check_plan(bad)


def test_progressive_rejects_incompatible_pilot_cadence(monkeypatch):
    original = bundle.read_pilot()
    for key, value in [
        ("physics_hz", 32),
        ("evaluation_hz", 32),
        ("rgb_shape", [112, 112, 3]),
        ("family", "room"),
    ]:
        monkeypatch.setattr(bundle, "read_pilot", lambda: {**original, key: value})
        with pytest.raises(ValueError, match="geometry/cadence"):
            bundle.progressive_plan("a" * 64, 1)


def test_progressive_raw_reuse_requires_same_selection_and_immutable_bytes(tmp_path):
    data = tmp_path / "raw.bin"
    data.write_bytes(b"synthetic pixels")
    atomic_json(tmp_path / "generation.json", {"source_commit": "synthetic"})
    sources = {
        "game/evaluation_driver.gd": "a" * 64,
        "src/bullet_time/generation/evaluation_bundle.py": "b" * 64,
    }
    old_plan = bundle.progressive_plan("c" * 64, 1)
    pin = {"runtime": "synthetic"}
    old = dict(
        schema_version="bullet-time.measurement-bundle.v1",
        plan=old_plan,
        engine_pin=pin,
        development=False,
        producer_sources=sources,
        inventory={p.name: digest(p.read_bytes()) for p in tmp_path.iterdir()},
    )
    atomic_json(tmp_path / "bundle.json", old)
    new_plan = bundle.progressive_plan("c" * 64, 8)
    root, evidence = bundle.reuse_capture_source(tmp_path, new_plan, pin, sources)
    assert root == tmp_path and evidence["bundle_sha256"] == digest(
        (tmp_path / "bundle.json").read_bytes()
    )
    with pytest.raises(ValueError, match="plan/runtime"):
        bundle.reuse_capture_source(tmp_path, bundle.progressive_plan("d" * 64, 8), pin, sources)
    with pytest.raises(ValueError, match="renderer/motion"):
        bundle.reuse_capture_source(
            tmp_path, new_plan, pin, {**sources, "game/evaluation_driver.gd": "e" * 64}
        )
    data.write_bytes(b"changed")
    with pytest.raises(ValueError, match="bytes changed"):
        bundle.reuse_capture_source(tmp_path, new_plan, pin, sources)
