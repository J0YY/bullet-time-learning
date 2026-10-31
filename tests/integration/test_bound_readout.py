"""Actual tiny fit/predict CLI inside the native boundary; no assessment release."""

import json
from pathlib import Path
import platform
import sys

import pytest

from bullet_time.evaluation.job_evidence import run_bound, verify_bound
from bullet_time.evaluation.readout_execution import readout_job_inputs, verify_readout_execution
from bullet_time.evaluation.assessment_contract import fit_recipe
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
    jobs = {}
    bindings = []

    def bound(*args, ok=True):
        if not ok:
            return original(*args, ok=False)
        args = list(map(str, args))
        artifact = Path(args[args.index("--output") + 1])
        operation = args[0]
        assert operation in ("fit-readout", "predict-readout")
        command = [sys.executable, "-m", "bullet_time.cli", *args]
        job = tmp_path / (operation + "-evidence")
        expected_outputs = (
            ["fit.json", "readout.pt", "readout.pt.json"]
            if operation == "fit-readout"
            else ["run.json", "coverage.json", "predictions.csv"]
        )
        result = run_bound(
            command,
            inputs=readout_job_inputs(command, repo),
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
        jobs[operation] = dict(
            path=str(job), request_sha256=result["request_sha256"], evidence_sha256=identity(result)
        )
        if operation == "predict-readout":
            fit = json.loads((tmp_path / "fit/fit.json").read_bytes())
            meta = json.loads((artifact / "run.json").read_bytes())
            design = dict(
                task_id="collision",
                horizon="0.5",
                model_kind="untrained",
                condition="untrained",
                objective="untrained",
                checkpoint_pass=0,
                label_budget=2,
                pretraining_seed=17,
                readout_seed=101,
                corpus_sha256="0" * 64,
                readout_recipe_sha256=identity(
                    {k: v for k, v in fit["config"].items() if k != "seed"}
                ),
            )
            recipe = fit_recipe(
                fit,
                inference_execution=meta["inference_execution"],
                input_sha256=meta["input_sha256"],
                image_manifest_sha256=meta["image_manifest_sha256"],
            )
            kwargs = dict(
                expected_path=tmp_path / "expected.json",
                design=design,
                recipe_sha256=identity(recipe),
                private_roots=[private],
                assessment_roots=[private],
                split="dev",
            )
            verified = verify_readout_execution(
                jobs["fit-readout"], jobs["predict-readout"], **kwargs
            )
            assert verified["complete"] and not verified["assessment_authorized"]
            bindings.append(verified)
            import subprocess
            from bullet_time.provenance import atomic_json, digest

            plan_path = tmp_path / "verify-jobs-plan.json"
            atomic_json(
                plan_path,
                dict(
                    schema_version="bullet-time.readout-execution-plan.v1",
                    fit_job=jobs["fit-readout"],
                    prediction_job=jobs["predict-readout"],
                    **{
                        **kwargs,
                        "expected_path": str(kwargs["expected_path"]),
                        "private_roots": [str(private)],
                        "assessment_roots": [str(private)],
                    },
                ),
            )
            output = tmp_path / "verified-jobs.json"
            cli = subprocess.run(
                [
                    sys.executable,
                    str(repo / "scripts/scoring/verify_readout_jobs.py"),
                    "--plan",
                    str(plan_path),
                    "--output",
                    str(output),
                ],
                text=True,
                capture_output=True,
            )
            assert cli.returncode == 0, cli.stderr
            saved = json.loads(output.read_bytes())
            assert saved["complete"] and saved["plan_sha256"] == digest(plan_path.read_bytes())
            assert saved["contract"] == verified["contract"]
            undeclared = tmp_path / "unblocked-private-copy"
            undeclared.mkdir()
            with pytest.raises(ValueError, match="not denied"):
                verify_readout_execution(
                    jobs["fit-readout"],
                    jobs["predict-readout"],
                    **{**kwargs, "private_roots": [undeclared]},
                )
            with pytest.raises(ValueError, match="required expected inventory"):
                verify_readout_execution(
                    jobs["fit-readout"],
                    jobs["predict-readout"],
                    **{**kwargs, "expected_path": tmp_path / "fit/fit.json"},
                )
        completed.append(operation)
        return json.loads((job / "isolation/job.log").read_text())

    monkeypatch.setattr(readout_cli, "run", bound)
    readout_cli.test_reference_fit_predict_cli_and_wrong_run_rejection(
        tmp_path, "frozen", "sequence"
    )
    assert completed == ["fit-readout", "predict-readout"]
    assert len(bindings) == 1
