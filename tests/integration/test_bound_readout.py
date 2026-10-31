"""Actual tiny fit/predict CLI inside the native boundary; no assessment release."""

import json
from pathlib import Path
import platform
import sys

import pytest

from bullet_time.evaluation.job_evidence import file_hash, run_bound, verify_bound
from bullet_time.provenance import identity
import test_readout_cli as readout_cli


@pytest.mark.skipif(platform.system() != "Darwin", reason="native macOS boundary integration")
def test_actual_consumer_fit_and_prediction_have_bound_execution_evidence(tmp_path, monkeypatch):
    private = tmp_path / "assessment-private"
    private.mkdir()
    probe = private / "labels.jsonl"
    probe.write_text("synthetic forbidden assessment placeholder")
    repo = Path(__file__).resolve().parents[2]
    original = readout_cli.run
    completed = []

    def bound(*args, ok=True):
        if not ok:
            return original(*args, ok=False)
        args = list(map(str, args))
        artifact = Path(args[args.index("--output") + 1])
        operation = args[0]
        assert operation in ("fit-readout", "predict-readout")
        paths = {
            p
            for p in (repo / "src/bullet_time").rglob("*")
            if p.is_file() and p.suffix in (".py", ".json", ".md")
        }
        paths.update({repo / "pyproject.toml", repo / "requirements-lock.txt"})
        for option in (
            "--images",
            "--inputs",
            "--labels",
            "--groups",
            "--readout-config",
            "--expected",
            "--backbone",
            "--checkpoint",
        ):
            if option in args:
                path = Path(args[args.index(option) + 1]).resolve()
                paths.add(path)
                if option in ("--backbone", "--checkpoint"):
                    paths.add(Path(str(path) + ".json"))
        manifest = Path(args[args.index("--images") + 1])
        paths.update(
            manifest.parent / json.loads(line)["rgb_path"]
            for line in manifest.read_text().splitlines()
        )
        job = tmp_path / (operation + "-evidence")
        expected_outputs = (
            ["fit.json", "readout.pt", "readout.pt.json"]
            if operation == "fit-readout"
            else ["run.json", "coverage.json", "predictions.csv"]
        )
        result = run_bound(
            [sys.executable, "-m", "bullet_time.cli", *args],
            inputs={str(path.resolve()): file_hash(path) for path in paths},
            artifact_output=artifact,
            expected_outputs=expected_outputs,
            denied_roots=[private],
            probe_files=[probe],
            output=job,
            cwd=repo,
            timeout_seconds=60,
        )
        assert (
            verify_bound(
                job,
                expected_request_sha256=result["request_sha256"],
                expected_evidence_sha256=identity(result),
            )
            == result
        )
        completed.append(operation)
        return json.loads((job / "isolation/job.log").read_text())

    monkeypatch.setattr(readout_cli, "run", bound)
    readout_cli.test_reference_fit_predict_cli_and_wrong_run_rejection(
        tmp_path, "frozen", "sequence"
    )
    assert completed == ["fit-readout", "predict-readout"]
