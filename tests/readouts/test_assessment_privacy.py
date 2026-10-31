import json
import platform
import subprocess
import sys

import pytest

from bullet_time.evaluation.label_contract import seal_assessment_labels, validate_label_header
from bullet_time.evaluation.isolated_job import prepare_boundary, run_isolated, PROBE
from bullet_time.evaluation.scoring import validate_target, score_directory
from bullet_time.evaluation.training import Targets
from bullet_time.evaluation.inputs import EvaluationInputs
from bullet_time.provenance import identity
from fixtures.consumer.evaluation import fixtures


def raw_labels():
    return [
        dict(
            schema_version="bullet-time.labels.v1",
            task_id="collision",
            episode_id=f"episode-{i}",
            query_id="query",
            horizon_or_frame="0.5",
            split="assessment",
            target={"contact": i},
        )
        for i in (0, 1)
    ]


def test_private_nonce_commits_full_record_without_exporting_low_entropy_hash():
    original = raw_labels()
    sealed, public = seal_assessment_labels(original)
    second, _ = seal_assessment_labels(original)
    assert original == raw_labels()
    assert len({r["commitment_nonce"] for r in sealed + second}) == 4
    for raw, row, commitment in zip(original, sealed, public, strict=True):
        validate_target(row)
        assert set(commitment) == {
            "task_id",
            "episode_id",
            "query_id",
            "horizon_or_frame",
            "split",
            "target_reference_sha256",
        }
        assert commitment["target_reference_sha256"] == identity(row)
        assert commitment["target_reference_sha256"] not in {
            identity(dict(raw, target={"contact": guessed})) for guessed in (0, 1)
        }
        assert identity(dict(row, target={"contact": 1 - row["target"]["contact"]})) != identity(
            row
        )
        with pytest.raises(ValueError, match="v2"):
            validate_target(raw)
    for mutation in ({"commitment_nonce": "public-seed"}, {"split": "dev"}, {"extra": 1}):
        with pytest.raises(ValueError):
            validate_label_header(dict(sealed[0], **mutation))
    with pytest.raises(ValueError, match="duplicate"):
        seal_assessment_labels([original[0], original[0]])
    with pytest.raises(ValueError, match="empty"):
        seal_assessment_labels([])


def test_v2_targets_join_actual_inputs_but_do_not_enable_fitting_or_scoring(tmp_path):
    path, store, base = fixtures(tmp_path / "input")
    path.write_text(
        "".join(
            json.dumps(dict(base, episode_id=f"episode-{i}", split="assessment")) + "\n"
            for i in (0, 1)
        )
    )
    inputs = EvaluationInputs(path, store, allowed_splits=("assessment",))
    sealed, public = seal_assessment_labels(raw_labels())
    labels = tmp_path / "labels.jsonl"
    labels.write_text("".join(json.dumps(r) + "\n" for r in sealed))
    with pytest.raises(ValueError, match="inaccessible"):
        Targets(labels, inputs)
    authorized_reader = Targets(labels, inputs, allowed_splits=("assessment",))
    assert [authorized_reader.reference_hash(e) for e in inputs.examples] == [
        r["target_reference_sha256"] for r in public
    ]
    with pytest.raises(ValueError, match="locked release"):
        score_directory(
            "missing", "missing", "missing", "missing", split="assessment", families=["fixture"]
        )


def test_sealing_cli_keeps_private_material_out_of_public_export(tmp_path):
    source = tmp_path / "source.jsonl"
    source.write_text("".join(json.dumps(r) + "\n" for r in raw_labels()))
    output = tmp_path / "sealed"
    args = [
        sys.executable,
        "scripts/data/seal_assessment.py",
        "--private-labels",
        str(source),
        "--output",
        str(output),
    ]
    subprocess.run(args, check=True, capture_output=True)
    private = (output / "private/labels.jsonl").read_text()
    public = "".join(p.read_text() for p in (output / "public").iterdir())
    for row in map(json.loads, private.splitlines()):
        assert row["commitment_nonce"] not in public
        assert '"target"' not in public
    assert (output / "private/labels.jsonl").stat().st_mode & 0o777 == 0o600
    assert subprocess.run(args, capture_output=True).returncode != 0
    assert (output / "private/labels.jsonl").read_text() == private


def test_boundary_paths_are_canonical_and_fail_closed(tmp_path, monkeypatch):
    private = tmp_path / 'private "quoted"'
    private.mkdir()
    probe = private / "labels"
    probe.write_text("synthetic")
    alias = tmp_path / "alias"
    alias.symlink_to(private, target_is_directory=True)
    roots, probes, profile = prepare_boundary([alias], [probe])
    assert roots == [private] and probes == [probe]
    assert '\\"quoted\\"' in profile and "deny network*" in profile
    with pytest.raises(FileNotFoundError):
        prepare_boundary([private], [tmp_path / "absent"])
    with pytest.raises(ValueError):
        prepare_boundary([private, alias], [probe, probe])
    monkeypatch.setattr(platform, "system", lambda: "Linux")
    with pytest.raises(RuntimeError, match="no unconfined fallback"):
        run_isolated(
            [sys.executable, "-c", "raise Exception('must not run')"],
            denied_roots=[private],
            probe_files=[probe],
            output=tmp_path / "job",
            cwd=tmp_path,
            timeout_seconds=1,
        )
    assert not (tmp_path / "job").exists()


@pytest.mark.skipif(platform.system() != "Darwin", reason="native macOS boundary integration")
def test_native_boundary_denies_child_and_symlink_access_but_allows_public(tmp_path):
    private = tmp_path / 'private "quoted"'
    private.mkdir()
    secret = private / "labels"
    secret.write_text("synthetic-private")
    alias = tmp_path / "alias"
    alias.symlink_to(secret)
    public = tmp_path / "public"
    public.write_text("permitted")
    program = """
import json, os, pathlib, subprocess, sys
assert pathlib.Path(sys.argv[1]).read_text() == 'permitted'
result = subprocess.run([sys.executable, '-I', '-c', sys.argv[2], sys.argv[3]], capture_output=True, text=True, check=True)
assert json.loads(result.stdout) == [True, True]
secret = pathlib.Path(json.loads(sys.argv[3])[0])
for operation, source, destination in [(os.link, secret, secret.parent.parent / 'linked'), (os.rename, secret.parent, secret.parent.parent / 'renamed')]:
    try:
        operation(source, destination)
    except PermissionError:
        pass
    else:
        raise AssertionError('private path alias operation unexpectedly allowed')
print('public read succeeded; child direct and symlink private reads denied')
"""
    result = run_isolated(
        [
            sys.executable,
            "-I",
            "-c",
            program,
            str(public),
            PROBE,
            json.dumps([str(secret), str(alias)]),
        ],
        denied_roots=[private],
        probe_files=[secret],
        output=tmp_path / "job",
        cwd=tmp_path,
        timeout_seconds=10,
    )
    assert result["status"] == "complete" and result["denial_probe"] == [True]
    assert not result["assessment_release_authorized"]
    assert "synthetic-private" not in (tmp_path / "job/job.log").read_text()


@pytest.mark.skipif(platform.system() != "Darwin", reason="native macOS boundary integration")
def test_native_timeout_is_failure_and_kills_child(tmp_path):
    private = tmp_path / "private"
    private.mkdir()
    probe = private / "labels"
    probe.write_text("fixture")
    output = tmp_path / "job"
    program = "import subprocess,sys,time; subprocess.Popen([sys.executable, '-c', 'import time,pathlib; time.sleep(2); pathlib.Path(\"escaped\").write_text(\"bad\")']); time.sleep(10)"
    with pytest.raises(subprocess.TimeoutExpired):
        run_isolated(
            [sys.executable, "-I", "-c", program],
            denied_roots=[private],
            probe_files=[probe],
            output=output,
            cwd=tmp_path,
            timeout_seconds=1,
        )
    # Wait beyond the child's delayed write to verify group cleanup, not only its parent.
    import time

    time.sleep(1.5)
    assert not (tmp_path / "escaped").exists()
    receipt = json.loads((output / "receipt.json").read_text())
    assert receipt["status"] == "failed" and receipt["failure_type"] == "TimeoutExpired"
