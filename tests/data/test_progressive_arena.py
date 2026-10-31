"""Transport/admission orchestration fixtures; mocked captures are not native evidence."""

from collections import Counter
from pathlib import Path
import copy

import pytest

from bullet_time.generation import progressive_arena as p


@pytest.fixture
def transport(monkeypatch):
    calls = []

    def capture(root, request, binary):
        gid = request["grid_id"]
        calls.append(request["index"])
        for location in p.locations(gid):
            path = root / location
            if path.suffix == ".json":
                p.write(path, request if location.startswith("requests/") else {"synthetic": True})
            else:
                path.mkdir(parents=True)
                (path / "fixture.bin").write_bytes(gid.encode())
        return [{"synthetic_transport": True}]

    def validator(root, request, plan, pin):
        gid = request["grid_id"]
        image_path = f"rgb/{gid}/fixture.bin"
        return (
            {
                "grid_id": gid,
                "cells": [
                    {"rgb_path": image_path, "rgb_sha256": p.sha(root / "rgb-only" / image_path)}
                ],
            },
            {
                "grid_id": gid,
                "renderer": {"device": "synthetic fixture"},
                "groups": request["groups"],
                "stride_ticks": request["stride_ticks"],
                "repeated_cells": 4,
            },
        )

    monkeypatch.setattr(p, "render_grid", capture)
    monkeypatch.setattr(p, "validate_grid", validator)
    monkeypatch.setattr(p, "verify_engine", lambda binary, pin: Path(binary))
    monkeypatch.setattr(
        p.subprocess,
        "check_output",
        lambda argv, **kw: "synthetic-fixture" if kw.get("text") else b"",
    )
    return calls


def refresh_inventory(root):
    bundle = p.read(root / "bundle.json")
    bundle["inventory"] = p.inventory(root, exclude=("bundle.json",))
    p.write(root / "bundle.json", bundle)


def test_pilot_prefix_preserves_existing_requests_and_full_cadences():
    plan = p.pilot_plan()
    old = p.read(p.ROOT / "configs/generation/arena-integration.json")
    assert all(
        p.canonical_bytes(p.make_request(plan, i)) == p.canonical_bytes(p.make_request(old, i))
        for i in range(8)
    )
    requests = [p.make_request(plan, i) for i in range(1000)]
    assert Counter(r["stride_ticks"] for r in requests) == {16: 334, 8: 333, 4: 333}
    assert all(
        len({r["groups"][kind] for r in requests}) == 1000
        for kind in ("configuration", "trajectory", "asset", "rollout")
    )
    for n in (0, True, 7, 101, 1001):
        with pytest.raises(ValueError):
            p.build_progressive("not-created", n, "unused")


def test_progressive_prefix_reuses_raw_bytes_and_rejects_bad_aggregate(tmp_path, transport):
    first, grown = tmp_path / "first", tmp_path / "grown"
    p.build_progressive(first, 1, "synthetic")
    report = p.build_progressive(grown, 8, "synthetic", reuse=first)
    assert transport == list(range(8))
    assert report["grids"] == 8 and report["cadences_ticks"] == {"4": 2, "8": 3, "16": 3}
    assert not report["scientific_gate_pass"] and report["joint_evaluation_admission"].startswith(
        "pending"
    )
    gid = p.make_request(p.pilot_plan(), 0)["grid_id"]
    for name, value in p.capture_inventory(first, gid).items():
        assert p.sha(grown / name) == value
    receipt = p.read(grown / f"private/capture-receipts/{gid}.json")
    assert receipt["commands"][0]["reused_grid"] == gid
    with pytest.raises(ValueError, match="overwrite"):
        p.build_progressive(grown, 8, "synthetic")
    (grown / "rgb-only/forbidden-state.json").write_text("{}")
    refresh_inventory(grown)
    with pytest.raises(ValueError, match="unlisted"):
        p.verify_progressive(grown)


def test_interrupted_capture_recovers_completed_receipts_without_inheriting_acceptance(
    tmp_path, transport, monkeypatch
):
    stopped, recovered = tmp_path / "stopped", tmp_path / "recovered"
    original = p.render_grid

    def fail(root, request, binary):
        if request["index"] == 1:
            (root / f"requests/{request['grid_id']}.json").write_text('{"partial":')
            raise RuntimeError("simulated render failure")
        return original(root, request, binary)

    monkeypatch.setattr(p, "render_grid", fail)
    with pytest.raises(RuntimeError, match="simulated"):
        p.build_progressive(stopped, 8, "synthetic")
    assert not (stopped / "bundle.json").exists()
    assert len(list((stopped / "private/capture-receipts").glob("*.json"))) == 1
    monkeypatch.setattr(p, "render_grid", original)
    assert p.build_progressive(recovered, 8, "synthetic", reuse=stopped)["grids"] == 8
    assert transport == list(range(8))


def test_legacy_preview_can_migrate_with_changed_plan_limit(tmp_path, transport):
    modern, legacy = tmp_path / "modern", tmp_path / "legacy"
    p.build_progressive(modern, 1, "synthetic")
    gid = p.make_request(p.pilot_plan(), 0)["grid_id"]
    for name in p.locations(gid):
        src, dst = modern / name, legacy / name
        dst.parent.mkdir(parents=True, exist_ok=True)
        p.shutil.copytree(src, dst) if src.is_dir() else p.shutil.copy2(src, dst)
    p.write(
        legacy / "bundle.json",
        {
            "schema_version": "bullet-time.arena-bundle.v1",
            "scope": "integration",
            "development": False,
            "grid_indices": [0],
            "plan": p.read(p.ROOT / "configs/generation/arena-integration.json"),
            "engine_pin": p.read(p.ROOT / "configs/rendering/godot-macos.json"),
            "producer_sources": p.source_files(),
            "inventory": p.inventory(legacy),
        },
    )
    p.build_progressive(tmp_path / "migrated", 1, "synthetic", reuse=legacy)
    assert transport == [0]


def test_changed_request_is_rendered_fresh_and_source_is_preserved(
    tmp_path, transport, monkeypatch
):
    first = tmp_path / "first"
    p.build_progressive(first, 1, "synthetic")
    original = p.make_request

    def changed(plan, index):
        request = original(plan, index)
        request["action"] += "; changed private request"
        return request

    monkeypatch.setattr(p, "make_request", changed)
    p.build_progressive(tmp_path / "changed", 1, "synthetic", reuse=first)
    assert transport == [0, 0]
    assert not p.read(first / f"requests/{original(p.pilot_plan(), 0)['grid_id']}.json")[
        "action"
    ].endswith("changed private request")


@pytest.mark.parametrize("kind", ["bytes", "request", "native", "development"])
def test_unusable_capture_sources_fail_closed(tmp_path, transport, kind):
    first = tmp_path / "first"
    p.build_progressive(first, 1, "synthetic")
    if kind in ("bytes", "request"):
        gid = p.make_request(p.pilot_plan(), 0)["grid_id"]
        if kind == "bytes":
            (first / f"rgb-only/rgb/{gid}/fixture.bin").write_bytes(b"tampered")
        else:
            path = first / f"requests/{gid}.json"
            request = p.read(path)
            request["action"] += "; tampered source"
            p.write(path, request)
    else:
        header = p.read(first / "capture.json")
        if kind == "native":
            header["producer_sources"]["game/arena_driver.gd"] = "0" * 64
        else:
            header["development"] = True
        p.write(first / "capture.json", header)
    with pytest.raises(ValueError, match="mismatch"):
        p.build_progressive(tmp_path / "new", 1, "synthetic", reuse=first)
    assert transport == [0]


def test_verifier_reconstructs_manifest_even_when_inventory_is_rewritten(tmp_path, transport):
    root = tmp_path / "drop"
    p.build_progressive(root, 1, "synthetic")
    (root / "rgb-only/pretrain.jsonl").write_text("{}\n")
    refresh_inventory(root)
    with pytest.raises(ValueError, match="manifest differs"):
        p.verify_progressive(root)


def test_plan_and_runtime_incompatibility_are_not_silently_accepted(
    tmp_path, transport, monkeypatch
):
    root = tmp_path / "drop"
    p.build_progressive(root, 1, "synthetic")
    actual = p.generation_runtime()
    monkeypatch.setattr(p, "generation_runtime", lambda: dict(actual, python="different"))
    with pytest.raises(ValueError, match="runtime differs"):
        p.verify_progressive(root)
    original_read = p.read

    def altered(path):
        row = original_read(path)
        if Path(path).name == "pilot-plan.json":
            row = copy.deepcopy(row)
            row["grid_shape"] = [8, 16]
        return row

    monkeypatch.setattr(p, "read", altered)
    with pytest.raises(ValueError, match="geometry/counts"):
        p.pilot_plan()

    def bad_visibility(path):
        row = original_read(path)
        if Path(path).name == "arena-integration.json":
            row["minimum_visible_cameras_per_state"] = 17
        return row

    monkeypatch.setattr(p, "read", bad_visibility)
    with pytest.raises(ValueError, match="visibility threshold"):
        p.pilot_plan()
