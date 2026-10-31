"""Command/inventory failure fixtures; real execution is tested separately on macOS."""

from pathlib import Path
import sys
import zipfile

import pytest

from bullet_time.evaluation import readout_execution as execution
from bullet_time.provenance import atomic_json, digest, identity
from fixtures.consumer.evaluation import fixtures


@pytest.fixture
def planned(tmp_path):
    inputs, store, _ = fixtures(tmp_path / "data")
    for name in ("labels.jsonl", "groups.json", "config.json", "backbone.pt", "backbone.pt.json"):
        (tmp_path / name).write_text("{}")
    options = dict(
        images=store.path,
        inputs=inputs,
        labels=tmp_path / "labels.jsonl",
        groups=tmp_path / "groups.json",
        backbone=tmp_path / "backbone.pt",
        **{"readout-config": tmp_path / "config.json"},
        output=tmp_path / "new-fit",
    )
    command = [sys.executable, "-m", "bullet_time.cli", "fit-readout"]
    for key, path in options.items():
        command.extend(["--" + key, str(path.resolve())])
    return command, Path(__file__).resolve().parents[2], tmp_path


def test_collector_covers_actual_rgb_models_config_and_consumer_sources_without_writes(planned):
    command, repo, root = planned
    before = sorted(root.rglob("*"))
    files = execution.readout_job_inputs(command, repo)
    assert files[str(root / "backbone.pt")] == digest(b"{}")
    assert str(root / "backbone.pt.json") in files
    assert str(repo / "src/bullet_time/cli.py") in files
    assert str(repo / "requirements-lock.txt") in files
    assert any(name.endswith(".png") for name in files)
    assert not any(
        "/generation/" in name or name.endswith("/readout_execution.py") for name in files
    )
    assert sorted(root.rglob("*")) == before


@pytest.mark.parametrize(
    "change",
    ["shell", "operation", "duplicate", "abbreviated", "relative", "threads", "missing", "cwd"],
)
def test_only_fixed_unambiguous_commands_are_accepted(planned, change):
    command, repo, root = planned
    if change == "shell":
        command[:3] = ["/bin/sh", "-c", "arbitrary"]
    elif change == "operation":
        command[3] = "train"
    elif change == "duplicate":
        command.extend(["--images", command[5]])
    elif change == "abbreviated":
        command[command.index("--images")] = "--imag"
    elif change == "relative":
        command[command.index("--images") + 1] = "images.jsonl"
    elif change == "threads":
        command[3:] = ["--threads"]
    elif change == "missing":
        del command[command.index("--groups") : command.index("--groups") + 2]
    else:
        repo = root
    with pytest.raises(ValueError):
        execution.readout_job_inputs(command, repo)


@pytest.mark.parametrize("missing", ["config", "rgb", "source", "dependencies"])
def test_unpinned_required_bytes_rejected_even_when_generic_receipt_is_verified(
    planned, monkeypatch, missing
):
    command, repo, root = planned
    files = execution.readout_job_inputs(command, repo)
    if missing == "config":
        name = str(root / "config.json")
    elif missing == "rgb":
        name = next(p for p in files if p.endswith(".png"))
    elif missing == "source":
        name = str(repo / "src/bullet_time/cli.py")
    else:
        name = str(repo / "requirements-lock.txt")
    files.pop(name)
    request = dict(
        command=command,
        cwd=str(repo),
        inputs=files,
        artifact_output=str(root / "new-fit"),
        denied_roots=[str(root / "private")],
    )
    job = root / "fake-job"
    job.mkdir()
    atomic_json(job / "request.json", request)
    # Scope: exercise the adapter's checks after a generic verifier. This stub
    # is not evidence of sandboxing or actual execution.
    monkeypatch.setattr(
        execution,
        "verify_bound",
        lambda *a, **kw: {"outputs": dict.fromkeys(execution.FIT_OUTPUTS, "0" * 64)},
    )
    record = dict(path=str(job), request_sha256=identity(request), evidence_sha256="0" * 64)
    with pytest.raises(ValueError, match="not pinned"):
        execution._job(record, "fit-readout", [])


def test_external_source_must_already_be_extracted_and_byte_pinned(planned, monkeypatch):
    from bullet_time.models import external

    command, repo, root = planned
    cache = root / "cache"
    cache.mkdir()
    archive = cache / "source.zip"
    with zipfile.ZipFile(archive, "w") as bundle:
        bundle.writestr("dinov2-fixture/model.py", b"fixture = True\n")
    source = cache / "dinov2-fixture"
    source.mkdir()
    model = source / "model.py"
    model.write_bytes(b"fixture = True\n")
    monkeypatch.setattr(
        external,
        "lock",
        lambda: dict(revision="fixture", archive_sha256=digest(archive.read_bytes())),
    )
    command.extend(["--external-cache", str(cache)])
    files = execution.readout_job_inputs(command, repo)
    assert str(model) in files and str(archive) in files
    model.write_text("changed")
    with pytest.raises(ValueError, match="differs from archive"):
        execution.readout_job_inputs(command, repo)
    model.unlink()
    with pytest.raises(FileNotFoundError):
        execution.readout_job_inputs(command, repo)
    assert not model.exists()  # the verifier must not repair/extract missing files
