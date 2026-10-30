"""Synthetic admission fixtures; real rendering is a separately recorded local check."""

from copy import deepcopy
import hashlib
import json
import math

import numpy as np
from PIL import Image
import pytest

from bullet_time.generation.arena import camera_position, make_request, stream
from bullet_time.generation.bundle import (
    ROOT,
    REPEAT_CELLS,
    confined,
    read,
    same_request,
    validate_grid,
    write,
)


@pytest.fixture
def grid(tmp_path):
    plan = read(ROOT / "configs/generation/arena-integration.json")
    pin = read(ROOT / "configs/rendering/godot-macos.json")
    request = make_request(plan, 0)
    gid = request["grid_id"]
    states, replay = [], []
    for t in range(16):
        objects = {}
        for obj in request["objects"]:
            position = list(obj["position"])
            if obj["id"] == "projectile":
                position[0] += t / 8
            objects[obj["id"]] = {"transform": [[1, 0, 0], [0, 1, 0], [0, 0, 1], position]}
        tick = request["start_tick"] + t * request["stride_ticks"]
        states.append({"physics_tick": tick, "seconds": tick / 64, "objects": objects})
        replay.append(json.dumps({k: v["transform"] for k, v in objects.items()}))
    engine = dict(major=4, minor=5, patch=1, status="stable", build="official", hash="f62fdbde1")
    saved = dict(request=request, states=states, contacts=[], physics_hz=64, engine_version=engine)
    write(tmp_path / f"private/states/{gid}.json", saved)
    write(tmp_path / f"private/states/{gid}-repeat.json", saved)
    cameras = []
    for pos in request["camera"]["poses"]:
        z = np.subtract(pos, request["camera"]["look_at"])
        z /= np.linalg.norm(z)
        x = np.cross([0, 1, 0], z)
        x /= np.linalg.norm(x)
        cameras.append([x.tolist(), np.cross(z, x).tolist(), z.tolist(), pos])
    pixels = np.zeros((224, 224, 3), dtype=np.uint8)
    pixels[:10, :10] = [255, 0, 0]
    pixels[10:20, :10] = [0, 255, 0]
    image = Image.fromarray(pixels)
    records = []
    for t in range(16):
        for c in range(16):
            name = f"t{t:02d}-c{c:02d}.png"
            for folder in [f"rgb-only/rgb/{gid}", f"private/masks/{gid}"]:
                dest = tmp_path / folder / name
                dest.parent.mkdir(parents=True, exist_ok=True)
                image.save(dest)
            checksum = hashlib.sha256(replay[t].encode()).hexdigest()
            records.append(
                dict(
                    world_time_index=t,
                    camera_index=c,
                    rgb_file=name,
                    frozen_state_unchanged=True,
                    before_state_sha256=checksum,
                    after_state_sha256=checksum,
                )
            )
    repeats = []
    for t, c in REPEAT_CELLS:
        dest = tmp_path / f"validation/render/{gid}/repeat/t{t:02d}-c{c:02d}.png"
        dest.parent.mkdir(parents=True, exist_ok=True)
        image.save(dest)
        repeats.append(dict(world_time_index=t, camera_index=c, pixel_identical=True))
    report = dict(
        engine_version=engine,
        renderer="gl_compatibility",
        display="synthetic-test",
        video_adapter="synthetic-test",
        physics_nodes_in_replay=0,
        temporal_effects=False,
        replayed_state_json=replay,
        camera_transforms=cameras,
        cells=records,
        repeat_checks=repeats,
    )
    report_path = tmp_path / f"validation/render/{gid}/render.json"
    write(report_path, report)
    return tmp_path, request, plan, pin, report_path


def test_request_streams_and_smooth_loop():
    plan = read(ROOT / "configs/generation/arena-integration.json")
    for i in range(8):
        request = make_request(plan, i)
        assert request == make_request(deepcopy(plan), i)
        camera = request["camera"]
        np.testing.assert_allclose(
            camera_position(camera, 0), camera_position(camera, math.tau), atol=1e-12
        )
    camera_rng = stream(17, 0, "camera")
    before = stream(17, 0, "physics").getstate()
    for _ in range(1000):
        camera_rng.random()
    assert stream(17, 0, "physics").getstate() == before
    with pytest.raises(ValueError):
        make_request(plan, 8)
    with pytest.raises(ValueError):
        make_request({**plan, "split": "test"}, 0)


def test_json_roundtrip_tolerance_does_not_hide_configuration_change():
    assert same_request({"x": [1.123456789012345]}, {"x": [1.1234567890123449]})
    assert not same_request({"x": [1.123457]}, {"x": [1.1234567890123449]})
    assert not same_request({"x": [1.0, 2.0]}, {"x": [1.0]})
    assert not same_request({"x": float("nan")}, {"x": 1.0})


def test_complete_synthetic_grid_admitted(grid):
    root, req, plan, pin, _ = grid
    record, summary = validate_grid(root, req, plan, pin)
    assert len(record["cells"]) == 256
    assert summary["visible_cameras_per_state"] == [16] * 16


@pytest.mark.parametrize(
    "mutation,match",
    [
        ("camera", "actual camera"),
        ("state", "visual transform"),
        ("cadence", "simulation cadence"),
        ("duplicate", "duplicate/invalid"),
        ("trace", "frozen state"),
        ("headless", "rendering environment"),
        ("repeat", "repeat-render pixels"),
        ("visibility", "foreground visibility"),
    ],
)
def test_reject_bad_grid(grid, mutation, match):
    root, req, plan, pin, report_path = grid
    report = read(report_path)
    if mutation == "camera":
        report["camera_transforms"][0][3][0] += 0.01
    elif mutation == "state":
        state = json.loads(report["replayed_state_json"][0])
        state["projectile"][3][0] += 0.01
        report["replayed_state_json"][0] = json.dumps(state)
    elif mutation == "cadence":
        for suffix in ["", "-repeat"]:
            path = root / f"private/states/{req['grid_id']}{suffix}.json"
            saved = read(path)
            saved["states"][0]["physics_tick"] += 1
            write(path, saved)
    elif mutation == "duplicate":
        report["cells"][1] = report["cells"][0]
    elif mutation == "trace":
        report["cells"][0]["after_state_sha256"] = "0" * 64
    elif mutation == "headless":
        report["display"] = "headless"
    elif mutation == "repeat":
        Image.new("RGB", (224, 224)).save(report_path.parent / "repeat/t15-c15.png")
    elif mutation == "visibility":
        for c in range(9):
            Image.new("RGB", (224, 224)).save(
                root / f"private/masks/{req['grid_id']}/t00-c{c:02d}.png"
            )
    write(report_path, report)
    with pytest.raises(ValueError, match=match):
        validate_grid(root, req, plan, pin)


def test_artifact_paths_and_duplicate_json_fail_closed(tmp_path):
    path = tmp_path / "payload.json"
    path.write_text('{"x":1,"x":2}')
    with pytest.raises(ValueError, match="duplicate JSON"):
        read(path)
    with pytest.raises(ValueError, match="path escape"):
        confined(tmp_path, "../payload.json")
    with pytest.raises(ValueError, match="path escape"):
        confined(tmp_path, str(path))
    outside = tmp_path.parent / "outside.json"
    outside.write_text("{}")
    (tmp_path / "link.json").symlink_to(outside)
    with pytest.raises(ValueError, match="path escape"):
        confined(tmp_path, "link.json")
