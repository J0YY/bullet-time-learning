"""Crash-safe artifact journal for the prelocked two-stage pilot policy.

This is a persistence component, not release authorization. A caller must validate
actual data, fit contracts and job isolation before using the journal. It never
opens labels, scores models, launches jobs or claims scientific gate passage.
"""

from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
import fcntl
import os
import re

from bullet_time.provenance import (
    atomic_json,
    fields,
    identity,
    sha256,
    strict_json,
)
from .assessment_policy import stage_inventory


def _read(path):
    return strict_json(Path(path).read_bytes())


def _sync(directory):
    fd = os.open(directory, os.O_RDONLY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


@contextmanager
def _exclusive(registry):
    registry = Path(registry)
    if registry.is_symlink():
        raise ValueError("registry cannot be a symlink")
    registry.mkdir(parents=True, exist_ok=True, mode=0o700)
    registry = registry.resolve(strict=True)
    mutex = registry / ".mutex"
    if mutex.is_symlink():
        raise ValueError("registry mutex cannot be a symlink")
    with mutex.open("a+b") as file:
        fcntl.flock(file, fcntl.LOCK_EX)
        try:
            yield registry
        finally:
            fcntl.flock(file, fcntl.LOCK_UN)


def _version(registry, version):
    if not isinstance(version, str) or not re.fullmatch(r"[a-z0-9][a-z0-9-]{0,95}", version):
        raise ValueError("invalid pilot version name")
    folder = registry / version
    if folder.is_symlink():
        raise ValueError("version cannot be a symlink")
    return folder


def _validate_lock(payload):
    fields(
        payload,
        {
            "schema_version",
            "version",
            "pool_sha256",
            "protocol_sha256",
            "pipeline_sha256",
            "source_runtime_sha256",
            "admission_sha256",
            "early_resume_sha256",
            "stages",
        },
    )
    if payload["schema_version"] != "bullet-time.assessment-lock.v1":
        raise ValueError("unknown assessment lock")
    for name in payload:
        if name.endswith("_sha256"):
            sha256(payload[name])
    inventory = stage_inventory()["stages"]
    if set(payload["stages"]) != set(inventory):
        raise ValueError("both assessment stages must be locked together")
    for stage, descriptors in inventory.items():
        slots = payload["stages"][stage]
        if set(slots) != set(descriptors):
            raise ValueError("lock must retain every declared stage slot")
        for slot in slots.values():
            fields(slot, {"recipe_sha256", "expected_inputs_sha256", "predictor_sha256"})
            sha256(slot["recipe_sha256"])
            sha256(slot["expected_inputs_sha256"])
            if slot["predictor_sha256"] is not None:
                sha256(slot["predictor_sha256"])
            elif stage == "H3":
                raise ValueError("H3 predictors must exist at the whole-version lock")


def create_version(registry, payload):
    """Reserve version and pool once; retry only an identical interrupted creation.

    Hashes are commitments supplied by the admission layer, not proof of their
    underlying scientific contents. Keep one registry for the whole pilot lineage.
    """
    _validate_lock(payload)
    with _exclusive(registry) as root:
        folder = _version(root, payload["version"])
        for other in root.iterdir():
            if other.is_dir():
                if other.is_symlink():
                    raise ValueError("registry cannot contain linked versions")
                reservation = other / "reservation.json"
                if reservation.exists():
                    prior = _read(reservation)
                    if prior["pool_sha256"] == payload["pool_sha256"] and other != folder:
                        raise ValueError("new version requires a fresh assessment pool")
        claim_path = root / f".{payload['version']}.reservation.json"
        claim = {"lock_sha256": identity(payload), "pool_sha256": payload["pool_sha256"]}
        for path in root.glob(".*.reservation.json"):
            if path.is_symlink():
                raise ValueError("registry claim cannot be a symlink")
            prior = _read(path)
            if path == claim_path and prior != claim:
                raise ValueError("cannot replace an existing version lock")
            if path != claim_path and prior["pool_sha256"] == payload["pool_sha256"]:
                raise ValueError("new version requires a fresh assessment pool")
        # Commit the claim before mkdir. Even a failure during directory/inner
        # reservation creation can resume identically without releasing the pool.
        if not claim_path.exists():
            atomic_json(claim_path, claim)
            _sync(root)
        folder.mkdir(mode=0o700, exist_ok=True)
        reservation_path = folder / "reservation.json"
        if reservation_path.exists():
            if _read(reservation_path) != claim:
                raise ValueError("cannot replace an existing version lock")
        else:
            if any(
                not p.is_file() or p.is_symlink() or not p.name.startswith(".reservation.json")
                for p in folder.iterdir()
            ):
                raise ValueError("unreserved version directory contains unexpected artifacts")
            atomic_json(reservation_path, claim)
            _sync(folder)
            _sync(root)
        if (folder / "lock.json").exists():
            if _read(folder / "lock.json") != payload:
                raise ValueError("persisted lock changed")
        else:
            atomic_json(folder / "lock.json", payload)
            _sync(folder)
        return _status(folder)


def _locked(folder):
    if folder.is_symlink() or any(p.is_symlink() for p in folder.rglob("*")):
        raise ValueError("version journal cannot contain symlinks")
    payload = _read(folder / "lock.json")
    _validate_lock(payload)
    reserved = _read(folder / "reservation.json")
    if (
        identity(payload) != reserved["lock_sha256"]
        or payload["pool_sha256"] != reserved["pool_sha256"]
    ):
        raise ValueError("lock differs from reserved identity")
    return payload


def _release(path):
    record = _read(path / "release.json")
    expected = record.pop("release_sha256")
    if identity(record) != expected:
        raise ValueError("frozen release changed")
    return record


def _status(folder):
    payload = _locked(folder)
    state = "locked"
    for stage in ("H3", "H4"):
        path = folder / stage
        if not (path / "release.json").exists():
            break
        release = _release(path)
        if release["lock_sha256"] != identity(payload):
            raise ValueError("release differs from version lock")
        if not (path / "receipt.json").exists():
            state = f"{stage}_released"
            break
        receipt = _read(path / "receipt.json")
        report = _read(path / "report.json")
        reserved_result = _read(path / "result-reservation.json")
        if any(receipt.get(k) != v for k, v in reserved_result.items()):
            raise ValueError("stage receipt differs from its reserved outcome")
        if receipt["release_sha256"] != identity(release) or receipt["report_sha256"] != identity(
            report
        ):
            raise ValueError("stage receipt changed")
        if stage == "H4" or receipt["outcome"] != "pass":
            state = "closed"
            break
        state = "H3_passed"
    return {
        "version": payload["version"],
        "lock_sha256": identity(payload),
        "state": state,
        "assessment_authorized": False,
        "scientific_gate_pass": False,
    }


def status(registry, version):
    with _exclusive(registry) as root:
        return _status(_version(root, version))


def freeze_stage(registry, version, stage, exports):
    """Freeze complete delivered/failed slot commitments before the caller scores.

    Each delivered export commits its already-validated predictor/recipe, expected
    inventory and prediction bytes; each failed slot carries an immutable reason.
    The caller owns immutable byte storage and must validate those bytes again
    before scoring. This function stores hashes, never data or labels.
    """
    if stage not in ("H3", "H4"):
        raise ValueError("unknown assessment stage")
    with _exclusive(registry) as root:
        folder = _version(root, version)
        payload = _locked(folder)
        planned = payload["stages"][stage]
        if not isinstance(exports, dict) or set(exports) != set(planned):
            raise ValueError("release must retain every declared stage slot")
        for sid, export in exports.items():
            if export.get("status") == "failed":
                fields(export, {"status", "error"})
                if not isinstance(export["error"], str) or not export["error"].strip():
                    raise ValueError("failed slot needs its actual reason")
                continue
            fields(
                export,
                {
                    "status",
                    "predictor_sha256",
                    "recipe_sha256",
                    "expected_inputs_sha256",
                    "expected_keys_sha256",
                    "predictions_sha256",
                },
            )
            if export["status"] != "delivered":
                raise ValueError("unknown export status")
            for name, value in export.items():
                if name.endswith("_sha256"):
                    sha256(value)
            for key in ("recipe_sha256", "expected_inputs_sha256", "predictor_sha256"):
                if planned[sid][key] is not None and export[key] != planned[sid][key]:
                    raise ValueError("export differs from locked slot")
        release = {
            "schema_version": "bullet-time.assessment-release.v1",
            "stage": stage,
            "lock_sha256": identity(payload),
            "exports": exports,
        }
        path = folder / stage
        if (path / "release.json").exists():
            if _release(path) != release:
                raise ValueError("stage already released; alternate artifacts are forbidden")
            return _status(folder)
        state = _status(folder)["state"]
        if state != ("locked" if stage == "H3" else "H3_passed"):
            raise ValueError("stage order forbids release")
        path.mkdir(exist_ok=True, mode=0o700)
        atomic_json(path / "release.json", {**release, "release_sha256": identity(release)})
        _sync(path)
        _sync(folder)
        return _status(folder)


def finish_stage(registry, version, stage, report, *, outcome):
    """Append a caller-validated score receipt; identical replay only.

    A receipt outcome is an operational state, not scientific proof. H3 pass needs
    complete delivered slots and the caller's validated gate report. H4 closes the
    version even when incomplete. Scorer/admission integration supplies the report.
    """
    if stage not in ("H3", "H4") or outcome not in ("pass", "fail", "incomplete"):
        raise ValueError("unknown assessment stage/outcome")
    with _exclusive(registry) as root:
        folder = _version(root, version)
        _locked(folder)
        path = folder / stage
        release = _release(path)
        if outcome == "pass" and any(
            x["status"] != "delivered" for x in release["exports"].values()
        ):
            raise ValueError("failed slots cannot receive a passing stage receipt")
        committed = {
            "schema_version": "bullet-time.assessment-receipt.v1",
            "release_sha256": identity(release),
            "report_sha256": identity(report),
            "outcome": outcome,
        }
        # Reserve the report identity before publishing its bytes or receipt.
        # This survives a crash between files without permitting another report.
        report_path = path / "report.json"
        result_reservation = path / "result-reservation.json"
        if result_reservation.exists() and _read(result_reservation) != committed:
            raise ValueError("cannot replace the first stage report after an interruption")
        if report_path.exists() and _read(report_path) != report:
            raise ValueError("persisted stage report changed")
        receipt_path = path / "receipt.json"
        if receipt_path.exists():
            receipt = _read(receipt_path)
            if any(receipt[k] != v for k, v in committed.items()):
                raise ValueError("cannot change an existing stage receipt")
            return _status(folder)
        if _status(folder)["state"] != f"{stage}_released":
            raise ValueError("stage is not awaiting its score receipt")
        if not result_reservation.exists():
            atomic_json(result_reservation, committed)
            _sync(path)
        if not report_path.exists():
            atomic_json(report_path, report)
            _sync(path)
        atomic_json(
            receipt_path, {**committed, "recorded_at": datetime.now(timezone.utc).isoformat()}
        )
        _sync(path)
        return _status(folder)
