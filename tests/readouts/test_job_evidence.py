import json
from pathlib import Path
import platform
import subprocess
import sys

import pytest

from bullet_time.evaluation.job_evidence import file_hash, run_bound, verify_bound
from bullet_time.provenance import identity


@pytest.fixture
def job(tmp_path):
    private = tmp_path / "private"
    private.mkdir()
    probe = private / "labels"
    probe.write_text("synthetic secret")
    source = tmp_path / "input"
    source.write_text("permitted input")
    artifact = tmp_path / "artifacts"
    script = tmp_path / "worker.py"
    script.write_text("""import pathlib, sys
source, output, private = map(pathlib.Path, sys.argv[1:])
try:
    private.read_bytes()
except PermissionError:
    pass
else:
    raise RuntimeError("denial missing")
output.mkdir()
(output / "result.txt").write_bytes(source.read_bytes())
""")
    return dict(
        command=[sys.executable, "-I", str(script), str(source), str(artifact), str(probe)],
        inputs={str(p): file_hash(p) for p in (source, script)},
        artifact_output=artifact,
        expected_outputs=["result.txt"],
        denied_roots=[private],
        probe_files=[probe],
        output=tmp_path / "job",
        cwd=tmp_path,
        timeout_seconds=10,
    )


def verify(job, result):
    return verify_bound(
        job["output"],
        expected_request_sha256=result["request_sha256"],
        expected_evidence_sha256=identity(result),
    )


@pytest.mark.skipif(platform.system() != "Darwin", reason="native macOS isolated execution")
def test_native_job_pins_actual_outputs_and_detects_later_mutations(job):
    result = run_bound(**job)
    assert result["status"] == "complete"
    assert not result["assessment_authorized"]
    assert verify(job, result) == result
    paths = [
        job["artifact_output"] / "result.txt",
        Path(next(iter(job["inputs"]))),
        job["output"] / "isolation/job.log",
        job["output"] / "isolation/receipt.json",
        job["output"] / "isolation/boundary.sb",
        job["output"] / "request.json",
        job["output"] / "evidence.json",
    ]
    for path in paths:
        before = path.read_bytes()
        if path.suffix == ".json":
            data = json.loads(before)
            data["unexpected_change"] = True
            path.write_text(json.dumps(data))
        else:
            path.write_bytes(before + b"changed")
        with pytest.raises(ValueError):
            verify(job, result)
        path.write_bytes(before)
    assert verify(job, result) == result
    with pytest.raises(ValueError, match="new artifact"):
        run_bound(**job)


@pytest.mark.skipif(platform.system() != "Darwin", reason="native macOS isolated execution")
@pytest.mark.parametrize(
    "mutation",
    ["change_input", "extra_output", "missing_output", "command_failure", "linked_output"],
)
def test_bad_actual_execution_retains_failure(job, mutation):
    script = Path(job["command"][2])
    suffix = {
        "change_input": 'source.write_text("changed")',
        "extra_output": '(output / "extra").write_text("unexpected")',
        "missing_output": '(output / "result.txt").unlink()',
        "command_failure": 'raise RuntimeError("fixture failure")',
        "linked_output": '(output / "result.txt").unlink(); (output / "result.txt").symlink_to(source)',
    }[mutation]
    with script.open("a") as stream:
        stream.write(suffix + "\n")
    job["inputs"][str(script)] = file_hash(script)
    with pytest.raises((ValueError, RuntimeError)):
        run_bound(**job)
    result = json.loads((job["output"] / "evidence.json").read_text())
    assert result["status"] == "failed" and not result["assessment_authorized"]
    assert result["failure_type"] in ("ValueError", "RuntimeError")
    with pytest.raises(ValueError, match="failed"):
        verify(job, result)


@pytest.mark.parametrize("mutation", ["hash", "private_input", "duplicate_alias", "bad_output"])
def test_invalid_request_fails_before_job_creation(job, mutation):
    source = Path(next(iter(job["inputs"])))
    if mutation == "hash":
        job["inputs"][str(source)] = "0" * 64
    elif mutation == "private_input":
        path = job["probe_files"][0]
        job["inputs"][str(path)] = file_hash(path)
    elif mutation == "duplicate_alias":
        alias = source.parent / "alias"
        alias.symlink_to(source)
        job["inputs"][str(alias)] = file_hash(source)
    else:
        job["expected_outputs"] = ["../escape"]
    with pytest.raises(ValueError):
        run_bound(**job)
    assert not job["output"].exists() and not job["artifact_output"].exists()


@pytest.mark.skipif(platform.system() != "Darwin", reason="native macOS isolated execution")
def test_cli_run_and_pinned_verification(job):
    manifest = job["cwd"] / "inputs.json"
    manifest.write_text(json.dumps(job["inputs"]))
    command = [
        sys.executable,
        "scripts/bound_job.py",
        "run",
        "--inputs",
        str(manifest),
        "--artifact-output",
        str(job["artifact_output"]),
        "--expected-output",
        "result.txt",
        "--deny-root",
        str(job["denied_roots"][0]),
        "--probe-file",
        str(job["probe_files"][0]),
        "--output",
        str(job["output"]),
        "--cwd",
        str(job["cwd"]),
        "--timeout-seconds",
        "10",
        "--",
        *job["command"],
    ]
    run = subprocess.run(command, check=True, capture_output=True, text=True)
    report = json.loads(run.stdout)
    verified = subprocess.run(
        [
            sys.executable,
            "scripts/bound_job.py",
            "verify",
            "--output",
            str(job["output"]),
            "--request-sha256",
            report["request_sha256"],
            "--evidence-sha256",
            report["evidence_sha256"],
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    assert json.loads(verified.stdout) == report


@pytest.mark.skipif(platform.system() != "Darwin", reason="native macOS isolated execution")
def test_concurrent_jobs_cannot_claim_one_artifact_destination(job, monkeypatch):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Event
    from bullet_time.evaluation import job_evidence

    entered, release = Event(), Event()
    original = job_evidence.run_isolated
    calls = []

    def paused(*args, **kwargs):
        calls.append(kwargs["output"])
        assert len(calls) == 1, "second job must be rejected before launch"
        entered.set()
        assert release.wait(5)
        return original(*args, **kwargs)

    monkeypatch.setattr(job_evidence, "run_isolated", paused)
    with ThreadPoolExecutor(max_workers=1) as workers:
        first = workers.submit(run_bound, **job)
        try:
            assert entered.wait(5)
            assert not job["artifact_output"].exists()
            second = dict(job, output=job["cwd"] / "other-job")
            with pytest.raises(FileExistsError):
                run_bound(**second)
            failure = json.loads((second["output"] / "evidence.json").read_text())
            assert failure["status"] == "failed"
        finally:
            release.set()
        result = first.result(timeout=10)
    assert len(calls) == 1 and verify(job, result) == result
