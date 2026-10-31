"""Synthetic private selection tests; no assessment outcomes are inspected."""

from copy import deepcopy
from functools import lru_cache
from pathlib import Path

import pytest

from bullet_time.generation import assessment_selection as module
from bullet_time.generation.evaluation_motion import (
    select_collection,
    background_conflict,
    tracking_background,
)
from bullet_time.provenance import atomic_json, canonical_bytes, digest, identity, strict_json


@lru_cache(maxsize=1)
def known_rows():
    counts = {task: {"train": 1, "dev": 1} for task in module.TASKS}
    return select_collection(134, counts)[0]


@pytest.fixture
def known(tmp_path):
    root = tmp_path / "known"
    inventory = {}
    for row in known_rows():
        name = f"private/{row['group_id']}/request.json"
        path = root / name
        path.parent.mkdir(parents=True)
        path.write_bytes(canonical_bytes(row))
        inventory[name] = digest(path.read_bytes())
    path = root / "bundle.json"
    atomic_json(
        path,
        {
            "schema_version": "bullet-time.measurement-bundle.v1",
            "plan": {
                "schema_version": "bullet-time.measurement-plan.v2",
                "seed": 134,
                "groups_per_task": {task: {"train": 1, "dev": 1} for task in module.TASKS},
            },
            "inventory": inventory,
        },
    )
    return [{"path": str(path), "sha256": digest(path.read_bytes())}]


def tiny_counts(monkeypatch):
    monkeypatch.setattr(module, "pilot_counts", lambda: (20261028, dict.fromkeys(module.TASKS, 1)))
    # Fixed private nonce only in tests, never the production CLI.
    monkeypatch.setattr(module.secrets, "token_hex", lambda size: "1" * 64)


def test_actual_content_reservation_across_prior_pools():
    counts = dict.fromkeys(module.TASKS, 1)
    first, stats = module.select_requests(134, known_rows(), counts)
    second, _ = module.select_requests(134, [*known_rows(), *first], counts)
    for selected in (first, second):
        assert len(selected) == 3
        assert all(set(r["assigned_pools"].values()) == {"assessment"} for r in selected)
    for kind in module.KINDS:
        assert not {r["groups"][kind] for r in first} & {r["groups"][kind] for r in second}
    assert module.select_requests(134, known_rows(), counts) == (first, stats)
    with pytest.raises(ValueError, match="never shrink"):
        module.select_requests(134, known_rows(), counts, limit=1)


def test_background_proximity_is_reserved_separately_from_exact_asset_ids():
    counts = dict.fromkeys(module.TASKS, 1)
    original, _ = module.select_requests(134, [], counts)
    tracking = deepcopy(next(r for r in original if r["task"] == "tracking"))
    color = tracking["prototypes"]["asset"]
    color[0] += 1 if color[0] < 31 else -1
    tracking["groups"] = {kind: identity(["different-known", kind]) for kind in module.KINDS}
    selected, stats = module.select_requests(134, [tracking], counts)
    actual = next(r for r in selected if r["task"] == "tracking")
    assert stats["tracking"]["background_rejections"] >= 1
    assert not background_conflict(tracking_background(actual), tracking_background(tracking))


def test_private_selection_roundtrip_and_prior_dependencies(known, tmp_path, monkeypatch):
    tiny_counts(monkeypatch)
    output = tmp_path / "selection"
    report = module.plan_assessment(output, known)
    assert module.verify_selection(output) == report
    assert report["episodes"] == 5 and not report["assessment_authorized"]
    assert output.stat().st_mode & 0o777 == 0o700
    assert all(p.stat().st_mode & 0o777 == 0o600 for p in output.iterdir())
    prior = {
        "path": str(output / "selection.json"),
        "sha256": digest((output / "selection.json").read_bytes()),
    }
    with pytest.raises(ValueError, match="every prior"):
        module.read_known([prior])
    rows, _ = module.read_known([*known, prior])
    assert len(rows) == 9
    with pytest.raises(ValueError, match="new private"):
        module.plan_assessment(output, known)
    altered = dict(report, episodes=999, assessment_authorized=True)
    atomic_json(output / "selection.json", altered)
    with pytest.raises(ValueError, match="does not reconstruct"):
        module.verify_selection(output)


def test_known_inventory_hash_and_reconstruction_are_checked(known):
    path = Path(known[0]["path"])
    report = strict_json(path.read_bytes())
    name = next(iter(report["inventory"]))
    request = path.parent / name
    row = strict_json(request.read_bytes())
    row["objects"][0]["color"][0] += 0.01
    request.write_bytes(canonical_bytes(row))
    with pytest.raises(ValueError, match="request bytes changed"):
        module.read_known(known)
    report["inventory"][name] = digest(request.read_bytes())
    atomic_json(path, report)
    known[0]["sha256"] = digest(path.read_bytes())
    with pytest.raises(ValueError, match="does not reconstruct"):
        module.read_known(known)


def test_private_inventory_mutation_fails(known, tmp_path, monkeypatch):
    tiny_counts(monkeypatch)
    output = tmp_path / "selection"
    module.plan_assessment(output, known)
    path = output / "requests.jsonl"
    path.write_bytes(path.read_bytes() + b"\n")
    with pytest.raises(ValueError, match="bytes changed"):
        module.verify_selection(output)


def test_prefilter_matches_full_generator_and_retains_prior_selection():
    for task in module.TASKS:
        for index in range(128):
            row = module.candidate(134, task, index, "assessment")
            assert module.appearance_palette(134, task, index) == row["prototypes"]["asset"]
    rows, _ = module.select_requests(134, known_rows(), dict.fromkeys(module.TASKS, 1))
    # Indices captured from the unfiltered implementation before optimization.
    # Raw floating-point requests are runtime-bound; compare their full bytes
    # against unfiltered generation on this runtime, not a Mac-specific hash.
    expected = [
        module.candidate(134, task, index, "assessment")
        for task, index in (("collision", 184), ("order", 35), ("tracking", 102))
    ]
    assert canonical_bytes(rows) == canonical_bytes(expected)


def test_resume_retains_private_stream_and_requires_incomplete_attempt(
    known, tmp_path, monkeypatch
):
    tiny_counts(monkeypatch)
    original = module.select_requests

    def fail(*args, **kwargs):
        raise ValueError("synthetic candidate limit")

    monkeypatch.setattr(module, "select_requests", fail)
    first = tmp_path / "failed"
    with pytest.raises(ValueError, match="candidate limit"):
        module.plan_assessment(first, known)
    config = first / "private-config.json"
    before = config.read_bytes()
    monkeypatch.setattr(module, "select_requests", original)
    monkeypatch.setattr(module.secrets, "token_hex", lambda size: pytest.fail("must not resample"))
    output = tmp_path / "resumed"
    report = module.plan_assessment(output, known, resume_private_config=config)
    assert (output / "private-config.json").read_bytes() == before
    assert module.verify_selection(output) == report
    with pytest.raises(ValueError, match="already completed"):
        module.plan_assessment(
            tmp_path / "forbidden", known, resume_private_config=output / "private-config.json"
        )
