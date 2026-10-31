"""Bounded native assessment prefixes from an already verified private selection.

All raw/source output remains private. This proves captured geometry and exported
bytes for a prefix, never full-pool/cross-pool admission or assessment release.
"""

from collections import Counter
from pathlib import Path
import shutil
import subprocess

from bullet_time.provenance import atomic_json, canonical_bytes, digest, strict_json
from . import evaluation_bundle as measurement
from .assessment_selection import verify_selection, TASKS
from .bundle import ROOT, read, sha, verify_engine, invoke
from .progressive_arena import inventory, generation_runtime

SCHEMA = "bullet-time.private-assessment-source.v1"


def source_files():
    files = measurement.source_files()
    for name in (
        "src/bullet_time/generation/assessment_capture.py",
        "src/bullet_time/generation/assessment_selection.py",
        "src/bullet_time/generation/progressive_arena.py",
        "scripts/data/build_assessment.py",
    ):
        files[name] = sha(ROOT / name)
    return files


def prefix(selection, per_task):
    if type(per_task) is not int or per_task not in (1, 8):
        raise ValueError("this integration accepts only one or eight complete groups per task")
    rows = [
        strict_json(line) for line in (Path(selection) / "requests.jsonl").read_bytes().splitlines()
    ]
    counts, selected = Counter(), []
    for row in rows:
        if row["task"] not in TASKS or row["split"] != "assessment":
            raise ValueError("private selection contains another task/split")
        if counts[row["task"]] < per_task:
            selected.append(row)
            counts[row["task"]] += 1
    if counts != dict.fromkeys(TASKS, per_task):
        raise ValueError("incomplete private selection prefix")
    return selected


def _plan(per_task):
    pilot = read(ROOT / "configs/pilot-plan.json")
    if (
        pilot["family"] != "projectile_arena"
        or pilot["physics_hz"] != 64
        or pilot["evaluation_hz"] != 16
        or pilot["observed_frames"] != 16
        or pilot["rgb_shape"] != [224, 224, 3]
        or pilot["forecast_horizon_seconds"] != [0.25, 0.5, 1.0]
    ):
        raise ValueError("pilot geometry/cadence differs from native assessment implementation")
    plan = read(ROOT / "configs/generation/evaluation-development.json")
    plan.pop("seed")  # Actual reconstruction stream is bound privately by selection.
    plan.update(
        schema_version="bullet-time.private-assessment-prefix.v1",
        groups_per_task={task: {"assessment": per_task} for task in TASKS},
        scope="private native prefix only; cross-pool/complete assessment admission pending",
    )
    return plan


def _native(sources):
    names = (
        "game/project.godot",
        "game/arena_driver.gd",
        "game/evaluation_driver.gd",
        "game/LICENSE",
        "configs/rendering/godot-macos.json",
    )
    return {name: sources[name] for name in names}


def reuse_source(root, pin, sources):
    root = Path(root)
    if root.is_symlink():
        raise ValueError("raw capture root cannot be a symlink")
    root = root.resolve(strict=True)
    raw = (root / "source.json").read_bytes()
    report = strict_json(raw)
    if (
        report["schema_version"] != SCHEMA
        or report["engine_pin"] != pin
        or _native(report["source_files"]) != _native(sources)
        or report["runtime"] != generation_runtime()
    ):
        raise ValueError("native assessment capture source/runtime differs")
    if root.is_symlink() or inventory(root, exclude=("source.json",)) != report["inventory"]:
        raise ValueError("raw assessment capture bytes differ")
    if sha(root / "source.json") != digest(raw):
        raise ValueError("capture receipt changed during reuse verification")
    return root, digest(raw)


def build_prefix(output, binary, selection, *, per_task=1, reuse=None):
    output, selection = Path(output), Path(selection).resolve(strict=True)
    if output.exists() or output.is_symlink():
        raise ValueError("new private capture output required")
    destination = output.resolve()
    if destination.is_relative_to(selection) or (
        reuse is not None and destination.is_relative_to(Path(reuse).resolve(strict=True))
    ):
        raise ValueError("capture output must be outside immutable selection/reuse sources")
    verified = verify_selection(selection)
    if any(
        destination.is_relative_to(Path(b["path"]).resolve(strict=True).parent)
        for b in verified["known_bindings"]
    ):
        raise ValueError("capture output must be outside known immutable source bundles")
    selected = prefix(selection, per_task)
    plan, sources = _plan(per_task), source_files()
    pin = read(ROOT / "configs/rendering/godot-macos.json")
    binary = verify_engine(binary, pin)
    if subprocess.check_output(["git", "status", "--porcelain"], cwd=ROOT).strip():
        raise ValueError("commit producer before native capture")
    old = reuse_source(reuse, pin, sources) if reuse is not None else None
    output = output.resolve()
    output.mkdir(parents=True, mode=0o700, exist_ok=False)
    shutil.copytree(selection, output / "selection")
    if read(output / "selection/selection.json") != verified:
        raise ValueError("selection copy changed")
    inputs, labels, groups, images, summaries, commands = [], [], [], [], [], []
    for request in selected:
        gid = request["group_id"]
        private = output / "private" / gid
        if old and measurement.reusable_request(old[0], request):
            shutil.copytree(old[0] / "private" / gid, private)
            shutil.copytree(old[0] / "inputs/rgb" / gid, private / "rgb")
            commands.append({"reused_group": gid, "source_sha256": old[1]})
        else:
            for folder in ("rgb", "masks", "full-masks", "repeat"):
                (private / folder).mkdir(parents=True)
            atomic_json(private / "request.json", request)
            command = [
                str(binary),
                "--path",
                str(ROOT / "game"),
                "--rendering-method",
                "gl_compatibility",
                "--resolution",
                "224x224",
                "--position",
                "20,60",
                "--script",
                "res://evaluation_driver.gd",
                "--",
                str(private / "request.json"),
                str(private),
            ]
            commands.append(invoke(command, private / "render.log", 90))
        if "ERROR:" in (private / "render.log").read_text():
            raise ValueError("native assessment capture logged an error")
        records, evidence = measurement.validate_capture(private, request, plan, pin)
        inp, lab, grp = measurement.exports(request, records, evidence)
        inputs.extend(inp)
        labels.extend(lab)
        groups.extend(grp)
        rgb_root = output / "inputs/rgb" / gid
        rgb_root.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(private / "rgb"), rgb_root)
        images.extend(measurement.image_catalog(output / "inputs", request))
        summaries.append({"group_id": gid, "task": request["task"], **evidence})
        print(
            f"Validated private {request['task']} group ({len(summaries)}/{len(selected)})",
            flush=True,
        )
    measurement.write_lines(output / "inputs/images.jsonl", images)
    measurement.write_lines(output / "inputs/evaluation.jsonl", inputs)
    measurement.write_lines(output / "private/labels.jsonl", labels)
    (output / "private/labels.jsonl").chmod(0o600)
    atomic_json(
        output / "groups.json",
        {"schema_version": "bullet-time.evaluation-groups.v1", "records": groups},
    )
    atomic_json(
        output / "validation.json",
        {"summaries": summaries, "assessment_authorized": False, "scientific_gate_pass": False},
    )
    atomic_json(
        output / "generation.json",
        {
            "commands": commands,
            "source_commit": subprocess.check_output(
                ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
            ).strip(),
        },
    )
    if source_files() != sources or read(output / "selection/selection.json") != verified:
        raise ValueError("capture source or selection changed")
    atomic_json(
        output / "source.json",
        {
            "schema_version": SCHEMA,
            "per_task": per_task,
            "plan": plan,
            "selection_sha256": sha(output / "selection/selection.json"),
            "source_files": sources,
            "engine_pin": pin,
            "runtime": generation_runtime(),
            "inventory": inventory(output),
            "assessment_authorized": False,
            "scientific_gate_pass": False,
        },
    )
    # Already reconstructed the complete selection above; compare its exact copied
    # bytes again while validating all new captures/exports. Avoid repeating search.
    return verify_source(output, _verified_selection=verified)


def verify_source(output, *, _verified_selection=None):
    output = Path(output)
    if output.is_symlink():
        raise ValueError("private capture root cannot be a symlink")
    output = output.resolve(strict=True)
    raw = (output / "source.json").read_bytes()
    report = strict_json(raw)
    if (
        report["schema_version"] != SCHEMA
        or report["source_files"] != source_files()
        or report["runtime"] != generation_runtime()
    ):
        raise ValueError("private capture producer/runtime changed")
    if report["assessment_authorized"] is not False or report["scientific_gate_pass"] is not False:
        raise ValueError("capture receipt cannot grant assessment admission")
    if output.stat().st_mode & 0o077:
        raise ValueError("raw assessment source must remain private")
    before = inventory(output, exclude=("source.json",))
    if before != report["inventory"]:
        raise ValueError("private capture artifact bytes changed")
    selection = output / "selection"
    verified = verify_selection(selection) if _verified_selection is None else _verified_selection
    if (
        read(selection / "selection.json") != verified
        or sha(selection / "selection.json") != report["selection_sha256"]
    ):
        raise ValueError("private selection receipt changed")
    for name, checksum in verified["inventory"].items():
        if digest((selection / name).read_bytes()) != checksum:
            raise ValueError("private selection copy bytes changed")
    selected = prefix(selection, report["per_task"])
    if report["plan"] != _plan(report["per_task"]) or report["engine_pin"] != read(
        ROOT / "configs/rendering/godot-macos.json"
    ):
        raise ValueError("native capture geometry/engine pin changed")
    inputs, labels, groups, images, summaries = [], [], [], [], []
    for request in selected:
        gid = request["group_id"]
        private = output / "private" / gid
        if canonical_bytes(read(private / "request.json")) != canonical_bytes(request):
            raise ValueError("captured request differs from fixed selection")
        records, evidence = measurement.validate_capture(
            private,
            request,
            report["plan"],
            report["engine_pin"],
            rgb_root=output / "inputs/rgb" / gid,
        )
        inp, lab, grp = measurement.exports(request, records, evidence)
        inputs.extend(inp)
        labels.extend(lab)
        groups.extend(grp)
        images.extend(measurement.image_catalog(output / "inputs", request))
        summaries.append({"group_id": gid, "task": request["task"], **evidence})
    for name, rows in (
        ("inputs/images.jsonl", images),
        ("inputs/evaluation.jsonl", inputs),
        ("private/labels.jsonl", labels),
    ):
        if (output / name).read_bytes() != b"".join(canonical_bytes(row) + b"\n" for row in rows):
            raise ValueError("private source export differs from actual native evidence")
    if read(output / "groups.json") != {
        "schema_version": "bullet-time.evaluation-groups.v1",
        "records": groups,
    } or read(output / "validation.json") != {
        "summaries": summaries,
        "assessment_authorized": False,
        "scientific_gate_pass": False,
    }:
        raise ValueError("private source validation summary differs")
    if (
        inventory(output, exclude=("source.json",)) != before
        or source_files() != report["source_files"]
        or sha(output / "source.json") != digest(raw)
    ):
        raise ValueError("private source artifacts changed during verification")
    return {
        "schema_version": "bullet-time.assessment-prefix-check.v1",
        "source_sha256": digest(raw),
        "groups": len(selected),
        "episodes": len(groups),
        "images": len(images),
        "queries": len(inputs),
        "per_task": report["per_task"],
        "native_source_validated": True,
        "assessment_authorized": False,
        "scientific_gate_pass": False,
        "limits": [
            "Prefix only; no complete pool, cross-pool RGB/common lineage, opaque consumer or job/release admission"
        ],
    }
