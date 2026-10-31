"""Verified local read-denial boundary for trusted training/inference commands.

This macOS backend is an engineering integration, not a hostile-code sandbox or
human blinding. Linux/CUDA execution needs a separately validated mount boundary.
"""

import json
import os
from pathlib import Path
import platform
import signal
import subprocess
import sys
import time

from bullet_time.provenance import atomic_json, digest, integer


PROBE = """
import json, os, sys
results = []
for path in json.loads(sys.argv[1]):
    try:
        fd = os.open(path, os.O_RDONLY)
    except PermissionError:
        results.append(True)
    except OSError:
        results.append(False)
    else:
        os.close(fd)
        results.append(False)
print(json.dumps(results))
"""


def bounded_command(command, *, log, cwd, environment, timeout):
    """Reap the job and its subprocess group on success, failure or timeout."""
    process = subprocess.Popen(
        command,
        cwd=cwd,
        env=environment,
        stdin=subprocess.DEVNULL,
        stdout=log,
        stderr=subprocess.STDOUT,
        start_new_session=True,
    )
    try:
        return process.wait(timeout=timeout)
    finally:
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        process.wait()


def prepare_boundary(denied_roots, probe_files):
    roots = [Path(p).resolve(strict=True) for p in denied_roots]
    probes = [Path(p).resolve(strict=True) for p in probe_files]
    if not roots or len(set(roots)) != len(roots) or len(probes) != len(roots):
        raise ValueError("one distinct denied root and one probe file per boundary required")
    for root, probe in zip(roots, probes, strict=True):
        if not root.is_dir() or not probe.is_file() or not probe.is_relative_to(root):
            raise ValueError("each probe must be an existing regular file inside its denied root")
        if any(ord(c) < 32 for c in str(root)):
            raise ValueError("control character in boundary path")
    # Explicitly deny private writes too, including a process renaming the root.
    profile = "(version 1)\n(allow default)\n(deny network*)\n"
    profile += "".join(
        f"(deny file-read* file-write* (subpath {json.dumps(str(root), ensure_ascii=False)}))\n"
        for root in roots
    )
    return roots, probes, profile


def run_isolated(command, *, denied_roots, probe_files, output, cwd, timeout_seconds):
    integer(timeout_seconds, "timeout_seconds", 1)
    backend = Path("/usr/bin/sandbox-exec")
    if platform.system() != "Darwin" or not backend.is_file():
        raise RuntimeError("verified isolation backend unavailable; no unconfined fallback")
    if not command or not Path(command[0]).is_absolute() or not Path(command[0]).is_file():
        raise ValueError("command requires an absolute executable path")
    roots, probes, profile = prepare_boundary(denied_roots, probe_files)
    output, cwd = Path(output).absolute(), Path(cwd).resolve(strict=True)
    if not cwd.is_dir() or output.exists():
        raise ValueError("existing cwd and a new job output directory required")
    # Resolving even before creation handles a symlink in an existing parent.
    if any(output.resolve().is_relative_to(root) for root in roots):
        raise ValueError("job receipt cannot be inside a denied root")
    output.mkdir(mode=0o700, parents=True, exist_ok=False)
    profile_path = output / "boundary.sb"
    profile_path.write_text(profile)
    environment = {"PATH": "/usr/bin:/bin:/usr/sbin:/sbin", "PYTHONNOUSERSITE": "1"}
    prefix = [str(backend), "-p", profile]
    receipt = {
        "schema_version": "bullet-time.isolated-job.v1",
        "platform": platform.platform(),
        "backend_sha256": digest(backend.read_bytes()),
        "launcher_sha256": digest(Path(__file__).read_bytes()),
        "profile_sha256": digest(profile.encode()),
        "denied_roots": [str(p) for p in roots],
        "probe_files": [str(p) for p in probes],
        "command": list(command),
        "cwd": str(cwd),
        "environment": environment,
        "timeout_seconds": timeout_seconds,
        "status": "preflight",
        "assessment_release_authorized": False,
    }
    receipt_path = output / "receipt.json"
    atomic_json(receipt_path, receipt)
    start = time.perf_counter()
    try:
        probe = subprocess.run(
            prefix + [sys.executable, "-I", "-c", PROBE, json.dumps([str(p) for p in probes])],
            capture_output=True,
            text=True,
            stdin=subprocess.DEVNULL,
            cwd=cwd,
            env=environment,
            timeout=30,
            check=True,
        )
        receipt["denial_probe"] = json.loads(probe.stdout)
        if receipt["denial_probe"] != [True] * len(probes):
            raise RuntimeError("access denial probe failed; job was not launched")
        receipt["status"] = "running"
        atomic_json(receipt_path, receipt)
        with (output / "job.log").open("xb") as log:
            returncode = bounded_command(
                prefix + list(command),
                cwd=cwd,
                environment=environment,
                log=log,
                timeout=timeout_seconds,
            )
        receipt["returncode"] = returncode
        receipt["status"] = "complete" if returncode == 0 else "failed"
    except (OSError, ValueError, RuntimeError, subprocess.SubprocessError) as error:
        receipt["status"] = "failed"
        # Store exception class only: subprocess exception text can contain output.
        receipt["failure_type"] = type(error).__name__
        raise
    finally:
        if receipt["status"] in ("preflight", "running"):
            receipt["status"] = "failed"
        receipt["seconds"] = time.perf_counter() - start
        log = output / "job.log"
        if log.is_file():
            receipt["log_sha256"] = digest(log.read_bytes())
        atomic_json(receipt_path, receipt)
    return receipt
