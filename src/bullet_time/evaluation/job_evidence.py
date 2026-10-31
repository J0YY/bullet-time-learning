"""Bind a trusted isolated execution to declared input bytes and new output files.

This records execution evidence, not scientific admission. The application adapter
must declare every relevant artifact and validate the command's meaning.
"""

from pathlib import Path
import hashlib

from bullet_time.provenance import atomic_json, identity, sha256, strict_json
from .isolated_job import prepare_boundary, run_isolated


def file_hash(path):
    result = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            result.update(block)
    return result.hexdigest()


def _inputs(records):
    if not isinstance(records, dict) or not records:
        raise ValueError("nonempty declared input inventory required")
    normalized = {}
    for name, checksum in records.items():
        path = Path(name)
        if not path.is_absolute() or not path.is_file():
            raise ValueError("declared inputs require absolute existing files")
        # Canonical names prevent aliases from creating two different declarations.
        if path.resolve(strict=True) != path:
            raise ValueError("declared inputs must use canonical paths, without aliases")
        if str(path) in normalized:
            raise ValueError("duplicate aliased input")
        if file_hash(path) != sha256(checksum):
            raise ValueError("declared input bytes changed")
        normalized[str(path)] = checksum
    return normalized


def _output_inventory(root):
    if root.is_symlink() or not root.is_dir():
        raise ValueError("artifact output must be a regular directory")
    result = {}
    for path in root.rglob("*"):
        if path.is_symlink() or not (path.is_file() or path.is_dir()):
            raise ValueError("output contains linked or special files")
        if path.is_file():
            result[path.relative_to(root).as_posix()] = file_hash(path)
    return result


def _execution():
    from . import isolated_job

    return {
        "evidence_source_sha256": file_hash(__file__),
        "isolation_source_sha256": file_hash(isolated_job.__file__),
    }


def run_bound(
    command,
    *,
    inputs,
    artifact_output,
    expected_outputs,
    denied_roots,
    probe_files,
    output,
    cwd,
    timeout_seconds,
):
    """Run once into new output locations, retaining failures without granting release.

    A successful command must leave its declared inputs unchanged and produce
    exactly the expected regular files. The executable itself is always bound.
    The caller must include scripts, source, dependencies, configs and model/data
    files as appropriate; this function does not infer them from arbitrary argv.
    """
    roots, probes, _ = prepare_boundary(denied_roots, probe_files)
    if not command or not Path(command[0]).is_absolute() or not Path(command[0]).is_file():
        raise ValueError("absolute existing executable required")
    command = [str(value) for value in command]
    pinned = _inputs(inputs)
    executable = Path(command[0]).resolve(strict=True)
    pinned[str(executable)] = file_hash(executable)
    if any(Path(name).is_relative_to(root) for name in pinned for root in roots):
        raise ValueError("declared job inputs cannot be inside denied roots")
    artifact_output, output = Path(artifact_output), Path(output)
    if any(path.exists() or path.is_symlink() for path in (artifact_output, output)):
        raise ValueError("bound jobs require new artifact and receipt directories")
    artifact_output, output = artifact_output.resolve(), output.resolve()
    if artifact_output.is_relative_to(output) or output.is_relative_to(artifact_output):
        raise ValueError("artifact and receipt directories must be separate")
    if any(path.is_relative_to(root) for path in (artifact_output, output) for root in roots):
        raise ValueError("job outputs cannot be inside denied roots")
    if (
        not isinstance(expected_outputs, list)
        or not expected_outputs
        or any(
            not isinstance(name, str)
            or not name
            or Path(name).is_absolute()
            or ".." in Path(name).parts
            or Path(name).as_posix() != name
            or "\\" in name
            for name in expected_outputs
        )
        or len(set(expected_outputs)) != len(expected_outputs)
    ):
        raise ValueError("unique normalized relative output files required")
    request = {
        "schema_version": "bullet-time.bound-job-request.v1",
        "command": command,
        "executable": str(executable),
        "cwd": str(Path(cwd).resolve(strict=True)),
        "inputs": pinned,
        "artifact_output": str(artifact_output),
        "expected_outputs": sorted(expected_outputs),
        "denied_roots": [str(p) for p in roots],
        "probe_files": [str(p) for p in probes],
        "timeout_seconds": timeout_seconds,
        "execution": _execution(),
    }
    output.mkdir(parents=True, mode=0o700, exist_ok=False)
    atomic_json(output / "request.json", request)
    evidence = {
        "schema_version": "bullet-time.bound-job-evidence.v1",
        "request_sha256": identity(request),
        "status": "failed",
        "assessment_authorized": False,
        "scientific_gate_pass": False,
        "scope": "declared artifact bytes and isolated command only; not a complete model/data admission",
    }
    try:
        receipt = run_isolated(
            command,
            denied_roots=roots,
            probe_files=probes,
            output=output / "isolation",
            cwd=request["cwd"],
            timeout_seconds=timeout_seconds,
        )
        if receipt["status"] != "complete":
            raise RuntimeError("isolated command failed; retain its receipt and logs")
        if _inputs(pinned) != pinned or _execution() != request["execution"]:
            raise ValueError("declared inputs or execution source changed during job")
        if strict_json((output / "request.json").read_bytes()) != request:
            raise ValueError("bound job request changed during execution")
        # Also re-resolve argv[0]; a changed executable symlink must not be accepted.
        if Path(command[0]).resolve(strict=True) != executable:
            raise ValueError("command executable binding changed")
        inventory = _output_inventory(artifact_output)
        if set(inventory) != set(expected_outputs):
            raise ValueError("actual output files differ from declared inventory")
        evidence.update(status="complete", outputs=inventory)
    except BaseException as error:
        evidence["failure_type"] = type(error).__name__
        raise
    finally:
        receipt_path = output / "isolation/receipt.json"
        if receipt_path.is_file():
            evidence["isolation_receipt_sha256"] = file_hash(receipt_path)
        atomic_json(output / "evidence.json", evidence)
    return evidence


def verify_bound(output, *, expected_request_sha256, expected_evidence_sha256):
    """Recheck actual files and the pinned receipt before an application consumes it."""
    output = Path(output)
    if output.is_symlink() or any(p.is_symlink() for p in output.rglob("*")):
        raise ValueError("job evidence cannot contain symlinks")
    request = strict_json((output / "request.json").read_bytes())
    evidence = strict_json((output / "evidence.json").read_bytes())
    if identity(evidence) != sha256(expected_evidence_sha256):
        raise ValueError("job evidence differs from pinned execution outcome")
    if (
        request.get("schema_version") != "bullet-time.bound-job-request.v1"
        or evidence.get("schema_version") != "bullet-time.bound-job-evidence.v1"
        or evidence.get("assessment_authorized") is not False
        or evidence.get("scientific_gate_pass") is not False
    ):
        raise ValueError("unsupported evidence contract")
    if identity(request) != sha256(expected_request_sha256) or evidence.get(
        "request_sha256"
    ) != identity(request):
        raise ValueError("job request differs from required execution")
    if evidence.get("status") != "complete" or request["execution"] != _execution():
        raise ValueError("job failed or execution verifier changed")
    receipt_path = output / "isolation/receipt.json"
    if file_hash(receipt_path) != evidence["isolation_receipt_sha256"]:
        raise ValueError("isolation receipt changed")
    receipt = strict_json(receipt_path.read_bytes())
    if receipt["status"] != "complete" or receipt.get("returncode") != 0:
        raise ValueError("isolated execution did not complete")
    for key in ("command", "cwd", "denied_roots", "probe_files", "timeout_seconds"):
        if receipt[key] != request[key]:
            raise ValueError("isolation receipt differs from bound command/boundary")
    if receipt["denial_probe"] != [True] * len(request["denied_roots"]):
        raise ValueError("private read denial was not verified")
    if receipt["launcher_sha256"] != request["execution"]["isolation_source_sha256"]:
        raise ValueError("isolation launcher changed")
    profile = output / "isolation/boundary.sb"
    if (
        file_hash(profile) != receipt["profile_sha256"]
        or file_hash(output / "isolation/job.log") != receipt["log_sha256"]
    ):
        raise ValueError("isolation profile or log changed")
    if _inputs(request["inputs"]) != request["inputs"]:
        raise ValueError("input identity changed")
    executable = str(Path(request["command"][0]).resolve(strict=True))
    if executable != request["executable"] or executable not in request["inputs"]:
        raise ValueError("executable binding changed")
    inventory = _output_inventory(Path(request["artifact_output"]))
    if inventory != evidence["outputs"] or set(inventory) != set(request["expected_outputs"]):
        raise ValueError("output identity changed")
    if (
        strict_json((output / "request.json").read_bytes()) != request
        or strict_json((output / "evidence.json").read_bytes()) != evidence
        or file_hash(receipt_path) != evidence["isolation_receipt_sha256"]
        or _execution() != request["execution"]
    ):
        raise ValueError("job evidence changed during verification")
    return evidence
