"""Per-group raw-capture receipts for interruption-safe private source reuse.

Only atomically completed receipts are eligible for reuse. Every raw byte and
current request still gets checked by the native producer before admission.
"""

from pathlib import Path
import re

from bullet_time.provenance import (
    atomic_json,
    canonical_bytes,
    digest,
    fields,
    identity,
    strict_json,
)
from .progressive_arena import inventory, generation_runtime

HEADER = "bullet-time.private-assessment-capture-journal.v1"
GROUP = "bullet-time.private-assessment-raw-group.v1"
FINAL = "bullet-time.private-assessment-source.v1"
NATIVE = (
    "game/project.godot",
    "game/arena_driver.gd",
    "game/evaluation_driver.gd",
    "game/LICENSE",
    "configs/rendering/godot-macos.json",
)


def native_sources(sources):
    return {name: sources[name] for name in NATIVE}


def group_files(root, gid):
    if not isinstance(gid, str) or not re.fullmatch(
        r"(collision|order|tracking)-[0-9a-f]{16}", gid
    ):
        raise ValueError("invalid private capture group ID")
    result = {}
    for relative in (f"private/{gid}", f"inputs/rgb/{gid}"):
        directory = root
        for part in Path(relative).parts:
            directory = directory / part
            if directory.is_symlink():
                raise ValueError("raw group path components cannot be linked")
        if not directory.is_dir():
            raise ValueError("complete regular raw group directories required")
        members = inventory(directory)
        if not members:
            raise ValueError("raw group is empty")
        result.update({f"{relative}/{name}": checksum for name, checksum in members.items()})
    if f"private/{gid}/request.json" not in result:
        raise ValueError("raw group has no saved request")
    return result


def begin(root, *, source_files, engine_pin, selection_sha256, per_task, source_commit):
    path = Path(root) / "capture.json"
    if path.exists():
        raise ValueError("capture journal already exists")
    atomic_json(
        path,
        {
            "schema_version": HEADER,
            "source_files": source_files,
            "engine_pin": engine_pin,
            "runtime": generation_runtime(),
            "selection_sha256": selection_sha256,
            "per_task": per_task,
            "source_commit": source_commit,
            "assessment_authorized": False,
            "scientific_gate_pass": False,
        },
    )


def record_group(root, request, command):
    root = Path(root)
    gid = request["group_id"]
    files = group_files(root, gid)
    if canonical_bytes(
        strict_json((root / "private" / gid / "request.json").read_bytes())
    ) != canonical_bytes(request):
        raise ValueError("raw group request differs before receipt")
    path = root / "captures" / (gid + ".json")
    if path.exists():
        raise ValueError("completed group receipt already exists")
    body = {
        "schema_version": GROUP,
        "group_id": gid,
        "request_sha256": identity(request),
        "capture_header_sha256": digest((root / "capture.json").read_bytes()),
        "inventory": files,
        "command": command,
    }
    atomic_json(path, {**body, "receipt_sha256": identity(body)})


def validate_records(root):
    root = Path(root)
    header_path = root / "capture.json"
    header_bytes = header_path.read_bytes()
    header = strict_json(header_bytes)
    if (
        header["schema_version"] != HEADER
        or header["assessment_authorized"] is not False
        or header["scientific_gate_pass"] is not False
    ):
        raise ValueError("invalid private capture journal")
    folder = root / "captures"
    if folder.is_symlink():
        raise ValueError("capture receipt directory cannot be linked")
    groups = set()
    for path in sorted(folder.glob("*.json")):
        # A killed atomic write may leave a dot-prefixed temporary file. It is
        # never a completed receipt and is deliberately ignored, without deletion.
        if path.name.startswith("."):
            continue
        if path.is_symlink():
            raise ValueError("capture receipt cannot be linked")
        record = strict_json(path.read_bytes())
        fields(
            record,
            {
                "schema_version",
                "group_id",
                "request_sha256",
                "capture_header_sha256",
                "inventory",
                "command",
                "receipt_sha256",
            },
        )
        recorded = record.pop("receipt_sha256")
        gid = record["group_id"]
        if (
            record["schema_version"] != GROUP
            or identity(record) != recorded
            or path.name != gid + ".json"
            or record["capture_header_sha256"] != digest(header_bytes)
        ):
            raise ValueError("raw capture receipt changed")
        files = group_files(root, gid)
        if files != record["inventory"]:
            raise ValueError("raw captured group bytes changed")
        request = strict_json((root / "private" / gid / "request.json").read_bytes())
        if request["group_id"] != gid or identity(request) != record["request_sha256"]:
            raise ValueError("captured group request binding differs")
        groups.add(gid)
    if header_path.read_bytes() != header_bytes:
        raise ValueError("capture header changed during verification")
    return header, groups


def load_reusable(root, pin, sources):
    root = Path(root)
    if root.is_symlink():
        raise ValueError("raw capture root cannot be a symlink")
    root = root.resolve(strict=True)
    complete = (root / "source.json").exists()
    path = root / ("source.json" if complete else "capture.json")
    if path.is_symlink():
        raise ValueError("raw capture receipt cannot be linked")
    raw = path.read_bytes()
    report = strict_json(raw)
    if (
        report["schema_version"] != (FINAL if complete else HEADER)
        or report["engine_pin"] != pin
        or native_sources(report["source_files"]) != native_sources(sources)
        or report["runtime"] != generation_runtime()
    ):
        raise ValueError("native assessment capture source/runtime differs")
    if complete and inventory(root, exclude=("source.json",)) != report["inventory"]:
        raise ValueError("raw assessment capture bytes differ")
    if (root / "capture.json").exists():
        header, groups = validate_records(root)
        if any(
            header[key] != report[key]
            for key in ("engine_pin", "runtime", "source_files", "selection_sha256", "per_task")
        ):
            raise ValueError("completed source differs from initial capture journal")
    else:
        groups = {p.parent.name for p in (root / "private").glob("*/request.json")}
    if path.read_bytes() != raw:
        raise ValueError("capture receipt changed during reuse verification")
    return root, digest(raw), groups
