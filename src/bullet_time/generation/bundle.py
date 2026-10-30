"""Bounded Godot production and byte-level admission, separate from the consumer."""

from pathlib import Path
import hashlib
import json
import math
import platform
import shutil
import subprocess
import time

import numpy as np
from PIL import Image

from .arena import camera_position, fingerprint, make_request

ROOT = Path(__file__).resolve().parents[3]
REPEAT_CELLS = [(15, 15), (0, 0), (8, 7), (0, 15)]


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read(path):
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError(f"duplicate JSON key: {key}")
            result[key] = value
        return result

    def constant(value):
        raise ValueError(f"nonfinite JSON: {value}")

    return json.loads(Path(path).read_text(), object_pairs_hook=pairs, parse_constant=constant)


def write(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, sort_keys=True, indent=2, allow_nan=False) + "\n")


def confined(root, relative):
    path = Path(relative)
    if path.is_absolute() or ".." in path.parts or "\\" in relative:
        raise ValueError("artifact path escape")
    full = (root / path).resolve(strict=True)
    if not full.is_relative_to(root.resolve()) or not full.is_file():
        raise ValueError("artifact path escape or non-file")
    return full


def sources():
    paths = [ROOT / "game/project.godot", ROOT / "game/arena_driver.gd", ROOT / "game/LICENSE"]
    for directory in (
        "src/bullet_time/generation",
        "scripts/data",
        "configs/generation",
        "configs/rendering",
    ):
        paths.extend(p for p in (ROOT / directory).glob("*") if p.suffix in {".py", ".json"})
    return {p.relative_to(ROOT).as_posix(): sha(p) for p in sorted(paths)}


def verify_engine(binary, pin):
    binary = Path(binary).resolve(strict=True)
    if sha(binary) != pin["binary_sha256"]:
        raise ValueError("engine binary differs from pin")
    version = subprocess.check_output([str(binary), "--version"], text=True, timeout=20).strip()
    if version != pin["version"]:
        raise ValueError("engine version differs from pin")
    return binary


def command(binary, mode, source, output):
    args = [str(binary), "--path", str(ROOT / "game")]
    if mode == "simulate":
        args += ["--headless", "--fixed-fps", "64"]
    else:
        args += [
            "--rendering-method",
            "gl_compatibility",
            "--resolution",
            "224x224",
            "--position",
            "20,60",
        ]
    return args + ["--script", "res://arena_driver.gd", "--", mode, str(source), str(output)]


def invoke(args, log, timeout):
    start = time.perf_counter()
    with Path(log).open("x") as file:
        subprocess.run(args, stdout=file, stderr=subprocess.STDOUT, check=True, timeout=timeout)
    return {"command": args, "seconds": time.perf_counter() - start, "log": Path(log).name}


def rgb(path):
    with Image.open(path) as image:
        if image.format != "PNG" or image.mode != "RGB" or image.size != (224, 224):
            raise ValueError(f"expected 224-square lossless RGB PNG: {path}")
        return np.array(image, dtype=np.uint8)


def same_request(actual, expected):
    """Godot's double JSON parser/writer can shift a request number by one ULP.

    This tolerance is only for the echoed request, never states or image bytes.
    The original request file itself is byte-bound in the immutable inventory.
    """
    if isinstance(expected, dict):
        return (
            isinstance(actual, dict)
            and actual.keys() == expected.keys()
            and all(same_request(actual[k], v) for k, v in expected.items())
        )
    if isinstance(expected, list):
        return (
            isinstance(actual, list)
            and len(actual) == len(expected)
            and all(same_request(a, e) for a, e in zip(actual, expected))
        )
    if type(expected) is float:
        return type(actual) in (float, int) and math.isclose(
            actual, expected, rel_tol=0, abs_tol=1e-12
        )
    return actual == expected


def camera_checks(request, saved, render):
    camera = request["camera"]
    for c, pose in enumerate(camera["poses"]):
        if not np.allclose(pose, camera_position(camera, math.tau * c / 16), rtol=0, atol=1e-10):
            raise ValueError("camera loop pose differs from declared curve")
    if len(render["camera_transforms"]) != 16:
        raise ValueError("missing measured camera transforms")
    for pose, observed in zip(camera["poses"], render["camera_transforms"]):
        observed = np.asarray(observed)
        expected_z = np.asarray(pose) - camera["look_at"]
        expected_z /= np.linalg.norm(expected_z)
        expected_x = np.cross([0, 1, 0], expected_z)
        expected_x /= np.linalg.norm(expected_x)
        expected_y = np.cross(expected_z, expected_x)
        if not np.allclose(observed, [expected_x, expected_y, expected_z, pose], rtol=0, atol=2e-6):
            raise ValueError("actual camera position/orientation differs from loop")
    endpoint_error = np.max(
        np.abs(np.subtract(camera_position(camera, 0), camera_position(camera, math.tau)))
    )
    epsilon = 1e-4
    derivatives = [
        np.subtract(camera_position(camera, t + epsilon), camera_position(camera, t - epsilon))
        / (2 * epsilon)
        for t in [0, math.tau]
    ]
    if endpoint_error > 1e-10 or not np.allclose(*derivatives, rtol=0, atol=1e-8):
        raise ValueError("camera loop position/motion does not close")
    # Conservative clearance: entire smooth curve is above every transformed object.
    max_y = -math.inf
    for state in saved["states"]:
        for obj in request["objects"]:
            transform = np.asarray(state["objects"][obj["id"]]["transform"])
            extent = [obj["radius"]] * 3 if obj["kind"] == "sphere" else np.asarray(obj["size"]) / 2
            max_y = max(max_y, transform[3, 1] + np.abs(transform[:3, 1]) @ extent)
    minimum_camera_y = camera["center"][1] - abs(camera["height_amplitude"])
    if minimum_camera_y <= max_y + 0.25:
        raise ValueError("camera curve lacks conservative geometry clearance")
    return {
        "closure_position_error": float(endpoint_error),
        "minimum_vertical_clearance": minimum_camera_y - max_y,
        "orientation_verified": True,
        "curve": camera["kind"],
    }


def validate_grid(root, request, plan, pin):
    gid = request["grid_id"]
    saved = read(root / f"private/states/{gid}.json")
    repeated = read(root / f"private/states/{gid}-repeat.json")
    render = read(root / f"validation/render/{gid}/render.json")
    if saved != repeated:
        raise ValueError("fixed-step simulation replay differs")
    if (
        not same_request(saved["request"], request)
        or len(saved["states"]) != 16
        or saved["physics_hz"] != 64
    ):
        raise ValueError("state/request mismatch")
    for record in (saved, render):
        version = record["engine_version"]
        expected = f"{version['major']}.{version['minor']}.{version['patch']}.{version['status']}.{version['build']}.{version['hash'][:9]}"
        if expected != pin["version"]:
            raise ValueError("recorded engine mismatch")
    if (
        render["renderer"] != pin["renderer"]
        or render["display"] == "headless"
        or render["physics_nodes_in_replay"] != 0
        or render["temporal_effects"] is not False
    ):
        raise ValueError("invalid rendering environment")
    expected_ids = {o["id"] for o in request["objects"]}
    if len(render["replayed_state_json"]) != 16:
        raise ValueError("missing replay snapshots")
    for t, state in enumerate(saved["states"]):
        tick = request["start_tick"] + t * request["stride_ticks"]
        if state["physics_tick"] != tick or state["seconds"] != tick / 64:
            raise ValueError("wrong simulation cadence")
        observed = json.loads(render["replayed_state_json"][t])
        if set(state["objects"]) != expected_ids or set(observed) != expected_ids:
            raise ValueError("replay object inventory mismatch")
        for oid in expected_ids:
            matrix = np.asarray(state["objects"][oid]["transform"])
            if (
                matrix.shape != (4, 3)
                or not np.isfinite(matrix).all()
                or not np.array_equal(matrix, observed[oid])
            ):
                raise ValueError("saved/replayed visual transform mismatch")
    centers = np.asarray([s["objects"]["projectile"]["transform"][3] for s in saved["states"]])
    if np.linalg.norm(centers - centers[0], axis=1).max() < 1:
        raise ValueError("projectile did not traverse the arena")
    if len(render["cells"]) != 256:
        raise ValueError("incomplete render evidence")
    cells, projectile, targets, seen = [], [], [], set()
    for record in render["cells"]:
        t, c = record["world_time_index"], record["camera_index"]
        if (
            type(t) is not int
            or type(c) is not int
            or not 0 <= t < 16
            or not 0 <= c < 16
            or (t, c) in seen
        ):
            raise ValueError("duplicate/invalid render cell")
        seen.add((t, c))
        state_hash = hashlib.sha256(render["replayed_state_json"][t].encode()).hexdigest()
        if (
            record["before_state_sha256"] != state_hash
            or record["after_state_sha256"] != state_hash
            or record["frozen_state_unchanged"] is not True
        ):
            raise ValueError("render advanced or changed frozen state")
        name = f"t{t:02d}-c{c:02d}.png"
        if record["rgb_file"] != name:
            raise ValueError("render filename/index mismatch")
        image_path = root / f"rgb-only/rgb/{gid}/{name}"
        pixels = rgb(image_path)
        mask = rgb(root / f"private/masks/{gid}/{name}")
        projectile.append((t, c, int(np.all(mask == [255, 0, 0], axis=2).sum())))
        targets.append((t, c, int(np.all(mask == [0, 255, 0], axis=2).sum())))
        cells.append(
            dict(
                world_time_index=t,
                camera_index=c,
                image_id=f"{gid}/t{t:02d}/c{c:02d}",
                rgb_path=f"rgb/{gid}/{name}",
                file_sha256=sha(image_path),
                rgb_sha256=hashlib.sha256(pixels.tobytes()).hexdigest(),
                height=224,
                width=224,
                channels=3,
            )
        )
    visibility = []
    for t in range(16):
        count = sum(
            p[2] >= plan["minimum_projectile_pixels"] and q[2] >= plan["minimum_target_pixels"]
            for p, q in zip(projectile, targets)
            if p[0] == t
        )
        if count < plan["minimum_visible_cameras_per_state"]:
            raise ValueError(
                f"grid {gid}: insufficient foreground visibility at state {t}: {count} cameras"
            )
        visibility.append(count)
    checks = render["repeat_checks"]
    if [(r["world_time_index"], r["camera_index"]) for r in checks] != REPEAT_CELLS or not all(
        r["pixel_identical"] is True for r in checks
    ):
        raise ValueError("repeat capture inventory failed")
    for t, c in REPEAT_CELLS:
        name = f"t{t:02d}-c{c:02d}.png"
        if not np.array_equal(
            rgb(root / f"rgb-only/rgb/{gid}/{name}"),
            rgb(root / f"validation/render/{gid}/repeat/{name}"),
        ):
            raise ValueError("repeat-render pixels differ")
    target_contacts = [
        c
        for c in saved["contacts"]
        if c["a"] == "projectile" and c["b"].startswith("target_") and c["b"] != "target_pad"
    ]
    return {
        "schema_version": "bullet-time.grid.v1",
        "grid_id": gid,
        "scene_family": "projectile_arena",
        "cells": sorted(cells, key=lambda c: (c["world_time_index"], c["camera_index"])),
    }, {
        "grid_id": gid,
        "camera": camera_checks(request, saved, render),
        "visible_cameras_per_state": visibility,
        "projectile_mask_pixels": projectile,
        "target_mask_pixels": targets,
        "repeated_cells": len(checks),
        "simulation_replay_identical": True,
        "all_256_frozen_state_checks": True,
        "game_goal": "projectile contacts at least one target block",
        "goal_reached": bool(target_contacts),
        "goal_contacts": target_contacts,
        "stride_ticks": request["stride_ticks"],
        "groups": request["groups"],
        "renderer": {k: render[k] for k in ["renderer", "video_adapter", "display"]},
    }


def verify_bundle(root, *, current_sources=False):
    root = Path(root).resolve(strict=True)
    bundle = read(root / "bundle.json")
    if (
        bundle["schema_version"] != "bullet-time.arena-bundle.v1"
        or bundle["scope"] != "integration"
    ):
        raise ValueError("unsupported bundle")
    if current_sources and bundle["producer_sources"] != sources():
        raise ValueError("producer source mismatch; cannot reuse")
    inventory = bundle["inventory"]
    actual = {
        p.relative_to(root).as_posix()
        for p in root.rglob("*")
        if p.is_file() and p != root / "bundle.json"
    }
    if set(inventory) != actual:
        raise ValueError("bundle inventory differs from actual files")
    for name, checksum in inventory.items():
        if sha(confined(root, name)) != checksum:
            raise ValueError(f"artifact hash mismatch: {name}")
    records, summaries = [], []
    for i in bundle["grid_indices"]:
        request = make_request(bundle["plan"], i)
        if read(root / f"requests/{request['grid_id']}.json") != request:
            raise ValueError("request differs from reproducible plan")
        record, summary = validate_grid(root, request, bundle["plan"], bundle["engine_pin"])
        records.append(record)
        summaries.append(summary)
    expected = b"".join(
        (json.dumps(r, sort_keys=True, separators=(",", ":")) + "\n").encode() for r in records
    )
    if (root / "rgb-only/pretrain.jsonl").read_bytes() != expected:
        raise ValueError("RGB manifest differs from validated cells")
    if bundle["grid_indices"] not in ([0], list(range(8))):
        raise ValueError("integration bundle must contain preview or eight grids")
    if len({fingerprint(s["renderer"]) for s in summaries}) != 1:
        raise ValueError("mixed rendering runtime")
    for kind in ("configuration", "asset", "trajectory", "rollout"):
        groups = [s["groups"][kind] for s in summaries]
        if len(groups) != len(set(groups)):
            raise ValueError(f"duplicate {kind} lineage")
    image_groups = {}
    for record in records:
        for cell in record["cells"]:
            owners = image_groups.setdefault(cell["rgb_sha256"], set())
            owners.add(record["grid_id"])
            if len(owners) > 1:
                raise ValueError("identical RGB across distinct integration rollouts")
    return {
        "grids": len(records),
        "images": len(records) * 256,
        "corpus_sha256": sha(root / "rgb-only/pretrain.jsonl"),
        "bundle_sha256": sha(root / "bundle.json"),
        "repeated_cells": sum(s["repeated_cells"] for s in summaries),
        "summaries": summaries,
        "cross_split_status": "not evaluated: only a pretraining integration pool exists",
        "scientific_gate_pass": False,
        "development": bundle["development"],
    }


def build_bundle(output, count, binary, plan_path, reuse=None, development=False):
    if count not in (1, 8):
        raise ValueError("this milestone is bounded to one or eight grids")
    output = Path(output).resolve()
    if output.exists():
        raise ValueError("refusing to overwrite an existing artifact directory")
    plan = read(plan_path)
    pin = read(ROOT / "configs/rendering/godot-macos.json")
    binary = verify_engine(binary, pin)
    producer = sources()
    dirty = bool(subprocess.check_output(["git", "status", "--porcelain"], cwd=ROOT))
    if dirty and not development:
        raise ValueError(
            "commit producer changes before accepted generation; --development labels debugging only"
        )
    old = None
    if reuse:
        reuse = Path(reuse).resolve(strict=True)
        verify_bundle(reuse, current_sources=True)
        old = read(reuse / "bundle.json")
        if (
            old["plan"] != plan
            or old["engine_pin"] != pin
            or old["grid_indices"] != [0]
            or old["development"]
        ):
            raise ValueError("preview cannot migrate to this plan/runtime")
    output.mkdir(parents=True)
    commands = []
    records, summaries = [], []
    for index in range(count):
        request = make_request(plan, index)
        gid = request["grid_id"]
        locations = [
            f"requests/{gid}.json",
            f"private/states/{gid}.json",
            f"private/states/{gid}-repeat.json",
            f"rgb-only/rgb/{gid}",
            f"private/masks/{gid}",
            f"validation/render/{gid}",
        ]
        if index == 0 and old:
            for relative in locations:
                src, dst = reuse / relative, output / relative
                dst.parent.mkdir(parents=True, exist_ok=True)
                if src.is_dir():
                    shutil.copytree(src, dst)
                else:
                    shutil.copy2(src, dst)
            commands.append(
                {"reused_preview": str(reuse), "bundle_sha256": sha(reuse / "bundle.json")}
            )
        else:
            write(output / locations[0], request)
            (output / "private/states").mkdir(parents=True, exist_ok=True)
            (output / "logs").mkdir(exist_ok=True)
            for suffix in ("", "-repeat"):
                args = command(
                    binary,
                    "simulate",
                    output / locations[0],
                    output / f"private/states/{gid}{suffix}.json",
                )
                commands.append(invoke(args, output / f"logs/{gid}{suffix}-simulate.log", 30))
            staging = output / f"validation/render/{gid}"
            for name in ("rgb", "masks", "repeat"):
                (staging / name).mkdir(parents=True)
            args = command(binary, "render", output / locations[1], staging)
            commands.append(invoke(args, output / f"logs/{gid}-render.log", 180))
            for name, relative in [("rgb", locations[3]), ("masks", locations[4])]:
                (output / relative).parent.mkdir(parents=True, exist_ok=True)
                shutil.move(str(staging / name), str(output / relative))
        record, summary = validate_grid(output, request, plan, pin)
        records.append(record)
        summaries.append(summary)
        print(f"Validated {gid}: 256 RGBs, replay, masks, camera and repeat captures", flush=True)
    (output / "rgb-only/pretrain.jsonl").write_text(
        "".join(json.dumps(r, sort_keys=True, separators=(",", ":")) + "\n" for r in records)
    )
    write(output / "validation/grids.json", {"summaries": summaries, "scientific_gate_pass": False})
    write(
        output / "generation.json",
        {
            "commands": commands,
            "host_system": platform.platform(),
            "source_commit": subprocess.check_output(
                ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
            ).strip(),
            "development": development,
            "dirty_at_start": dirty,
        },
    )
    if sources() != producer:
        raise ValueError("producer changed during generation; retain rejected attempt")
    inventory = {
        p.relative_to(output).as_posix(): sha(p) for p in sorted(output.rglob("*")) if p.is_file()
    }
    write(
        output / "bundle.json",
        {
            "schema_version": "bullet-time.arena-bundle.v1",
            "scope": "integration",
            "plan": plan,
            "engine_pin": pin,
            "producer_sources": producer,
            "grid_indices": list(range(count)),
            "development": development,
            "inventory": inventory,
            "assets": "original procedural primitives/materials; game/LICENSE",
            "artifact_boundary": "consumer resolves only within rgb-only; private is a sibling, not an OS access sandbox",
        },
    )
    return verify_bundle(output, current_sources=True)
