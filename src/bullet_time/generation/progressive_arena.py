"""Immutable 1/8/100/1,000-grid preparation with reusable per-grid capture receipts.

This is data production, not joint split admission or authorization to train.
Every current request and native capture is revalidated before aggregate admission.
"""

from collections import Counter
from pathlib import Path
import platform
import shutil
import subprocess
import numpy as np
import PIL

from bullet_time.provenance import atomic_json as write, canonical_bytes, integer
from .arena import make_request, fingerprint
from .bundle import (
    ROOT,
    read,
    sha,
    confined,
    verify_engine,
    validate_grid,
    command,
    invoke,
)

COUNTS = (1, 8, 100, 1000)
SCOPE = "progressive pretraining data preparation; no joint evaluation admission or learning"


def generation_runtime():
    return {
        "python": platform.python_version(),
        "platform": platform.platform(),
        "numpy": np.__version__,
        "pillow": PIL.__version__,
    }


def source_files():
    names = [
        "game/project.godot",
        "game/arena_driver.gd",
        "game/LICENSE",
        "src/bullet_time/generation/arena.py",
        "src/bullet_time/generation/bundle.py",
        "src/bullet_time/generation/progressive_arena.py",
        "src/bullet_time/provenance.py",
        "scripts/data/build_pilot_arena.py",
        "configs/generation/arena-integration.json",
        "configs/pilot-plan.json",
        "configs/rendering/godot-macos.json",
    ]
    return {name: sha(ROOT / name) for name in names}


def native_sources(sources):
    expected = {
        "game/project.godot",
        "game/arena_driver.gd",
        "game/LICENSE",
        "configs/rendering/godot-macos.json",
    }
    if not expected <= sources.keys():
        raise ValueError("missing native capture source binding")
    return {name: sources[name] for name in sorted(expected)}


def pilot_plan():
    pilot = read(ROOT / "configs/pilot-plan.json")
    if (
        pilot["schema_version"] != "bullet-time.pilot-plan.v1"
        or pilot["grid_handoffs"] != list(COUNTS)
        or pilot["pretraining_grids"] != 1000
        or pilot["family"] != "projectile_arena"
        or pilot["physics_hz"] != 64
        or pilot["grid_shape"] != [16, 16]
        or pilot["rgb_shape"] != [224, 224, 3]
    ):
        raise ValueError("unsupported pilot geometry/counts")
    integer(pilot["data_seed"], "data seed")
    base = read(ROOT / "configs/generation/arena-integration.json")
    plan = dict(base, seed=pilot["data_seed"], maximum_grids=1000, scope=SCOPE)
    make_request(plan, 0)  # Existing producer validates physics/camera/cadence fields.
    for key in (
        "minimum_projectile_pixels",
        "minimum_target_pixels",
        "minimum_visible_cameras_per_state",
    ):
        value = integer(plan[key], key, 1)
        if value > (16 if key == "minimum_visible_cameras_per_state" else 224 * 224):
            raise ValueError("impossible visibility threshold")
    return plan


def locations(gid):
    return (
        f"requests/{gid}.json",
        f"private/states/{gid}.json",
        f"private/states/{gid}-repeat.json",
        f"rgb-only/rgb/{gid}",
        f"private/masks/{gid}",
        f"validation/render/{gid}",
    )


def inventory(root, *, exclude=()):
    if any(p.is_symlink() for p in root.rglob("*")):
        raise ValueError("capture files must not be symlinks")
    return {
        str(p.relative_to(root)): sha(p)
        for p in sorted(root.rglob("*"))
        if p.is_file() and str(p.relative_to(root)) not in exclude
    }


def verify_inventory(root, declared, *, exact=False, exclude=()):
    if exact:
        actual = inventory(root, exclude=exclude)
        if set(actual) != set(declared):
            raise ValueError("bundle inventory differs")
        if actual != declared:
            raise ValueError("capture bytes differ")
        return
    for name, checksum in declared.items():
        if sha(confined(root, name)) != checksum:
            raise ValueError(f"capture bytes differ: {name}")


def capture_inventory(root, gid):
    result = {}
    for name in locations(gid):
        path = root / name
        if path.is_symlink():
            raise ValueError("capture path must not be a symlink")
        if path.is_dir():
            files = inventory(path)
            if not files:
                raise ValueError("empty raw capture directory")
            result.update({f"{name}/{p}": value for p, value in files.items()})
        else:
            result[name] = sha(confined(root, name))
    return result


def reuse_source(root, pin, native):
    """Allow complete legacy/v2 bundles or a stopped v2 capture journal.

    No prior aggregate verdict is inherited. A journal means only that its listed
    groups completed native capture; the new consumer validates each reused group.
    """
    root = Path(root).resolve(strict=True)
    header_path = root / "capture.json"
    legacy = not header_path.exists()
    if legacy:
        header_path = root / "bundle.json"
        header = read(header_path)
        if (
            header["schema_version"] != "bullet-time.arena-bundle.v1"
            or header["scope"] != "integration"
        ):
            raise ValueError("unsupported legacy capture source")
        verify_inventory(root, header["inventory"], exact=True, exclude=("bundle.json",))
    else:
        header = read(header_path)
        if header["schema_version"] != "bullet-time.arena-capture.v1":
            raise ValueError("unsupported capture journal")
    if (
        header["development"]
        or header["engine_pin"] != pin
        or native_sources(header["producer_sources"]) != native
    ):
        raise ValueError("capture native source/runtime/development mismatch")
    return root, header, sha(header_path), legacy


def reuse_grid(source, output, request):
    root, header, source_hash, legacy = source
    gid = request["grid_id"]
    if legacy:
        if not (root / f"requests/{gid}.json").is_file():
            return None
        declared = {
            name: h
            for name, h in header["inventory"].items()
            if any(
                name == location or name.startswith(location + "/") for location in locations(gid)
            )
        }
        origin = {"source_bundle_sha256": source_hash}
    else:
        receipt_path = root / f"private/capture-receipts/{gid}.json"
        if not receipt_path.exists():
            return None
        receipt = read(receipt_path)
        if (
            receipt["schema_version"] != "bullet-time.arena-grid-capture.v1"
            or receipt["capture_header_sha256"] != source_hash
        ):
            raise ValueError("capture receipt/header mismatch")
        declared = receipt["inventory"]
        origin = {"source_capture_sha256": source_hash, "source_receipt_sha256": sha(receipt_path)}
    if capture_inventory(root, gid) != declared:
        raise ValueError("capture inventory/hash mismatch")
    old_request = read(root / f"requests/{gid}.json")
    if not legacy and receipt["request_sha256"] != fingerprint(old_request):
        raise ValueError("capture receipt/request mismatch")
    if canonical_bytes(old_request) != canonical_bytes(request):
        return None
    for name in locations(gid):
        src, dst = root / name, output / name
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(src, dst) if src.is_dir() else shutil.copy2(src, dst)
    if capture_inventory(output, gid) != declared:
        raise ValueError("copied capture bytes changed")
    return {"reused_grid": gid, **origin}


def render_grid(output, request, binary):
    gid = request["grid_id"]
    write(output / f"requests/{gid}.json", request)
    (output / "private/states").mkdir(parents=True, exist_ok=True)
    (output / "logs").mkdir(exist_ok=True)
    commands = []
    for suffix in ("", "-repeat"):
        args = command(
            binary,
            "simulate",
            output / f"requests/{gid}.json",
            output / f"private/states/{gid}{suffix}.json",
        )
        commands.append(invoke(args, output / f"logs/{gid}{suffix}-simulate.log", 30))
    staging = output / f"validation/render/{gid}"
    for name in ("rgb", "masks", "repeat"):
        (staging / name).mkdir(parents=True)
    commands.append(
        invoke(
            command(binary, "render", output / f"private/states/{gid}.json", staging),
            output / f"logs/{gid}-render.log",
            180,
        )
    )
    if any("ERROR:" in (output / "logs" / row["log"]).read_text() for row in commands):
        raise ValueError("Godot logged an error; retain rejected capture")
    for name, destination in (("rgb", "rgb-only/rgb"), ("masks", "private/masks")):
        target = output / destination / gid
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(staging / name), target)
    return commands


def summarize(records, summaries):
    if len({fingerprint(s["renderer"]) for s in summaries}) != 1:
        raise ValueError("mixed native rendering runtime")
    for kind in ("configuration", "asset", "trajectory", "rollout"):
        groups = [s["groups"][kind] for s in summaries]
        if len(groups) != len(set(groups)):
            raise ValueError(f"duplicate {kind} lineage")
    images = {}
    for record in records:
        for cell in record["cells"]:
            old = images.setdefault(cell["rgb_sha256"], record["grid_id"])
            if old != record["grid_id"]:
                raise ValueError("identical RGB across distinct pretraining rollouts")
    return {
        "grids": len(records),
        "images": len(records) * 256,
        "cadences_ticks": {
            str(k): v for k, v in sorted(Counter(s["stride_ticks"] for s in summaries).items())
        },
        "repeated_cells": sum(s["repeated_cells"] for s in summaries),
        "joint_evaluation_admission": "pending; lineage and cross-split pixel checks required",
        "scientific_gate_pass": False,
    }


def verify_progressive(root):
    root = Path(root).resolve(strict=True)
    bundle = read(root / "bundle.json")
    if bundle["schema_version"] != "bullet-time.arena-bundle.v2" or bundle["scope"] != SCOPE:
        raise ValueError("unsupported progressive bundle")
    header = read(root / "capture.json")
    if (
        header["schema_version"] != "bullet-time.arena-capture.v1"
        or type(header["development"]) is not bool
        or header["engine_pin"] != read(ROOT / "configs/rendering/godot-macos.json")
        or header["runtime"] != generation_runtime()
    ):
        raise ValueError("capture header/runtime differs")
    if header["producer_sources"] != source_files() or header["plan"] != pilot_plan():
        raise ValueError("producer/plan changed; use the pinned revision")
    count = integer(header["requested_grids"], "requested grids", 1)
    if count not in COUNTS or bundle["grid_indices"] != list(range(count)):
        raise ValueError("wrong progressive grid count/index inventory")
    verify_inventory(root, bundle["inventory"], exact=True, exclude=("bundle.json",))
    records, summaries = [], []
    for index in range(count):
        request = make_request(header["plan"], index)
        gid = request["grid_id"]
        if canonical_bytes(read(root / f"requests/{gid}.json")) != canonical_bytes(request):
            raise ValueError("request differs from selected pilot plan")
        receipt = read(root / f"private/capture-receipts/{gid}.json")
        if (
            receipt["schema_version"] != "bullet-time.arena-grid-capture.v1"
            or receipt["capture_header_sha256"] != sha(root / "capture.json")
            or receipt["request_sha256"] != fingerprint(request)
            or receipt["inventory"] != capture_inventory(root, gid)
        ):
            raise ValueError("capture receipt differs")
        record, summary = validate_grid(root, request, header["plan"], header["engine_pin"])
        records.append(record)
        summaries.append(summary)
    expected = b"".join(canonical_bytes(r) + b"\n" for r in records)
    if (root / "rgb-only/pretrain.jsonl").read_bytes() != expected:
        raise ValueError("RGB manifest differs from validated grids")
    allowed = {"pretrain.jsonl"} | {cell["rgb_path"] for r in records for cell in r["cells"]}
    actual = {
        str(p.relative_to(root / "rgb-only")) for p in (root / "rgb-only").rglob("*") if p.is_file()
    }
    if actual != allowed:
        raise ValueError("RGB-only tree contains unlisted files")
    result = summarize(records, summaries)
    if canonical_bytes(read(root / "validation/grids.json")) != canonical_bytes(
        {"summaries": summaries, "result": result}
    ):
        raise ValueError("grid validation report differs")
    if header["producer_sources"] != source_files():
        raise ValueError("producer changed during verification")
    return {
        **result,
        "corpus_sha256": sha(root / "rgb-only/pretrain.jsonl"),
        "bundle_sha256": sha(root / "bundle.json"),
        "development": header["development"],
    }


def build_progressive(output, count, binary, *, reuse=None, development=False):
    integer(count, "grid count", 1)
    if type(development) is not bool:
        raise ValueError("development must be boolean")
    if count not in COUNTS:
        raise ValueError("choose one of the planned 1/8/100/1,000 grid drops")
    output = Path(output).resolve()
    if output.exists():
        raise ValueError("refusing to overwrite a grid drop")
    plan, pin, sources = (
        pilot_plan(),
        read(ROOT / "configs/rendering/godot-macos.json"),
        source_files(),
    )
    if subprocess.check_output(["git", "status", "--porcelain"], cwd=ROOT) and not development:
        raise ValueError("commit producer before accepted generation")
    binary = verify_engine(binary, pin)
    old = reuse_source(reuse, pin, native_sources(sources)) if reuse is not None else None
    output.mkdir(parents=True)
    write(
        output / "capture.json",
        {
            "schema_version": "bullet-time.arena-capture.v1",
            "requested_grids": count,
            "plan": plan,
            "engine_pin": pin,
            "producer_sources": sources,
            "development": development,
            "host": platform.platform(),
            "runtime": generation_runtime(),
            "source_commit": subprocess.check_output(
                ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
            ).strip(),
            "scope": "raw capture journal; not aggregate admission",
        },
    )
    records, summaries = [], []
    for index in range(count):
        request = make_request(plan, index)
        reused = reuse_grid(old, output, request) if old else None
        commands = [reused] if reused is not None else render_grid(output, request, binary)
        record, summary = validate_grid(output, request, plan, pin)
        if source_files() != sources:
            raise ValueError("producer changed during capture; retain completed raw receipts")
        write(
            output / f"private/capture-receipts/{request['grid_id']}.json",
            {
                "schema_version": "bullet-time.arena-grid-capture.v1",
                "capture_header_sha256": sha(output / "capture.json"),
                "request_sha256": fingerprint(request),
                "commands": commands,
                "inventory": capture_inventory(output, request["grid_id"]),
            },
        )
        records.append(record)
        summaries.append(summary)
        print(
            f"Validated {request['grid_id']}: 256 RGBs; {'reused' if reused else 'new capture'}",
            flush=True,
        )
    (output / "rgb-only/pretrain.jsonl").write_bytes(
        b"".join(canonical_bytes(r) + b"\n" for r in records)
    )
    write(
        output / "validation/grids.json",
        {"summaries": summaries, "result": summarize(records, summaries)},
    )
    write(
        output / "bundle.json",
        {
            "schema_version": "bullet-time.arena-bundle.v2",
            "scope": SCOPE,
            "grid_indices": list(range(count)),
            "inventory": inventory(output),
        },
    )
    return verify_progressive(output)
