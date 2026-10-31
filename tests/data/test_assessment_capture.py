from copy import deepcopy

import pytest

from bullet_time.generation import assessment_capture as capture
from bullet_time.provenance import atomic_json, canonical_bytes, digest


def test_prefix_counts_and_order_never_split_selected_groups(tmp_path):
    rows = [
        dict(task=t, split="assessment", group_id=f"{t}-{i}")
        for t in capture.TASKS
        for i in range(10)
    ]
    (tmp_path / "requests.jsonl").write_bytes(b"".join(canonical_bytes(r) + b"\n" for r in rows))
    one, eight = capture.prefix(tmp_path, 1), capture.prefix(tmp_path, 8)
    assert len(one) == 3 and len(eight) == 24
    assert all(r in eight for r in one)
    assert [r["group_id"] for r in one] == [f"{task}-0" for task in capture.TASKS]
    assert "seed" not in capture._plan(1)
    for count in (0, 2, True, 400):
        with pytest.raises(ValueError, match="only one or eight"):
            capture.prefix(tmp_path, count)
    rows.pop()
    rows = [r for r in rows if r["task"] != "tracking"]
    (tmp_path / "requests.jsonl").write_bytes(b"".join(canonical_bytes(r) + b"\n" for r in rows))
    with pytest.raises(ValueError, match="incomplete"):
        capture.prefix(tmp_path, 1)


def test_reuse_checks_native_identity_and_actual_bytes(tmp_path):
    raw = tmp_path / "raw.bin"
    raw.write_bytes(b"synthetic native capture fixture")
    sources, pin = capture.source_files(), {"synthetic_engine": "fixture"}
    report = dict(
        schema_version=capture.SCHEMA,
        source_files=sources,
        engine_pin=pin,
        runtime=capture.generation_runtime(),
        inventory={"raw.bin": digest(raw.read_bytes())},
    )
    atomic_json(tmp_path / "source.json", report)
    assert capture.reuse_source(tmp_path, pin, sources)[0] == tmp_path
    bad = deepcopy(sources)
    bad["game/evaluation_driver.gd"] = "0" * 64
    with pytest.raises(ValueError, match="source/runtime"):
        capture.reuse_source(tmp_path, pin, bad)
    raw.write_bytes(b"changed")
    with pytest.raises(ValueError, match="bytes differ"):
        capture.reuse_source(tmp_path, pin, sources)


def test_reuse_rejects_root_and_internal_symlinks(tmp_path):
    root = tmp_path / "root"
    root.mkdir()
    alias = tmp_path / "alias"
    alias.symlink_to(root, target_is_directory=True)
    with pytest.raises(ValueError, match="symlink"):
        capture.reuse_source(alias, {}, {})
    with pytest.raises(ValueError, match="symlink"):
        capture.verify_source(alias)


def test_existing_capture_output_rejected_before_source_access(tmp_path):
    with pytest.raises(ValueError, match="new private"):
        capture.build_prefix(tmp_path, "absent-engine", tmp_path)


def test_capture_plan_rejects_unimplemented_pilot_geometry(monkeypatch):
    original = capture.read
    for key, value in (("physics_hz", 32), ("evaluation_hz", 8), ("rgb_shape", [32, 32, 3])):

        def altered(path):
            data = original(path)
            return {**data, key: value} if path.name == "pilot-plan.json" else data

        monkeypatch.setattr(capture, "read", altered)
        with pytest.raises(ValueError, match="geometry/cadence"):
            capture._plan(1)
