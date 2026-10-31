from copy import deepcopy
import json

import pytest

from bullet_time.evaluation import assessment_state as state
from bullet_time.evaluation.assessment_policy import stage_inventory
from bullet_time.provenance import identity


def payload(version="pilot-fixture-v1", pool="pool"):
    result = {
        "schema_version": "bullet-time.assessment-lock.v1",
        "version": version,
        **{
            k: identity(k)
            for k in (
                "protocol_sha256",
                "pipeline_sha256",
                "source_runtime_sha256",
                "admission_sha256",
                "early_resume_sha256",
            )
        },
        "pool_sha256": identity(pool),
        "stages": {},
    }
    for stage, slots in stage_inventory()["stages"].items():
        result["stages"][stage] = {
            sid: {
                "recipe_sha256": identity(descriptor),
                "expected_inputs_sha256": identity(
                    descriptor.get("task", descriptor["readout"]["task"])
                ),
                "predictor_sha256": identity(sid) if stage == "H3" else None,
            }
            for sid, descriptor in slots.items()
        }
    return result


def exports(lock, stage):
    return {
        sid: {
            **slot,
            "status": "delivered",
            "predictor_sha256": identity(sid),
            "expected_keys_sha256": identity([sid, "keys"]),
            "predictions_sha256": identity([sid, "predictions"]),
        }
        for sid, slot in lock["stages"][stage].items()
    }


def test_both_stages_have_one_fixed_release_and_cached_receipts(tmp_path):
    lock = payload()
    assert state.create_version(tmp_path, lock)["state"] == "locked"
    assert state.create_version(tmp_path, lock)["state"] == "locked"
    for stage, ending in [("H3", "H3_passed"), ("H4", "closed")]:
        records = exports(lock, stage)
        assert (
            state.freeze_stage(tmp_path, lock["version"], stage, records)["state"]
            == f"{stage}_released"
        )
        result = state.finish_stage(
            tmp_path, lock["version"], stage, {"fixture": stage}, outcome="pass"
        )
        assert result["state"] == ending
        assert not result["assessment_authorized"] and not result["scientific_gate_pass"]
        assert state.freeze_stage(tmp_path, lock["version"], stage, records) == result
        receipt = (tmp_path / lock["version"] / stage / "receipt.json").read_bytes()
        assert (
            state.finish_stage(tmp_path, lock["version"], stage, {"fixture": stage}, outcome="pass")
            == result
        )
        assert (tmp_path / lock["version"] / stage / "receipt.json").read_bytes() == receipt
        changed = deepcopy(records)
        changed[next(iter(changed))]["predictions_sha256"] = "0" * 64
        with pytest.raises(ValueError, match="alternate"):
            state.freeze_stage(tmp_path, lock["version"], stage, changed)


def test_stage_order_failed_slots_and_failed_h3_close_version(tmp_path):
    lock = payload()
    state.create_version(tmp_path, lock)
    with pytest.raises(ValueError, match="stage order"):
        state.freeze_stage(tmp_path, lock["version"], "H4", exports(lock, "H4"))
    records = exports(lock, "H3")
    records[next(iter(records))] = {"status": "failed", "error": "planned fit failed"}
    state.freeze_stage(tmp_path, lock["version"], "H3", records)
    with pytest.raises(ValueError, match="failed slots"):
        state.finish_stage(tmp_path, lock["version"], "H3", {}, outcome="pass")
    assert (
        state.finish_stage(tmp_path, lock["version"], "H3", {}, outcome="incomplete")["state"]
        == "closed"
    )
    with pytest.raises(ValueError, match="stage order"):
        state.freeze_stage(tmp_path, lock["version"], "H4", exports(lock, "H4"))
    with pytest.raises(ValueError, match="fresh assessment pool"):
        state.create_version(tmp_path, payload("pilot-fixture-v2"))
    state.create_version(tmp_path, payload("pilot-fixture-v2", "fresh-pool"))


@pytest.mark.parametrize(
    "mutation",
    [
        lambda p: p["stages"]["H4"].pop(next(iter(p["stages"]["H4"]))),
        lambda p: p["stages"]["H3"][next(iter(p["stages"]["H3"]))].update(predictor_sha256=None),
        lambda p: p.update(pipeline_sha256="bad"),
    ],
)
def test_invalid_locks_fail_before_reserving_pool(tmp_path, mutation):
    lock = payload()
    mutation(lock)
    with pytest.raises(ValueError):
        state.create_version(tmp_path, lock)
    assert not (tmp_path / lock["version"]).exists()


def test_future_checkpoint_is_append_only_and_recipe_cannot_change(tmp_path):
    lock = payload()
    state.create_version(tmp_path, lock)
    state.freeze_stage(tmp_path, lock["version"], "H3", exports(lock, "H3"))
    state.finish_stage(tmp_path, lock["version"], "H3", {}, outcome="pass")
    records = exports(lock, "H4")
    sid = next(iter(records))
    wrong = deepcopy(records)
    wrong[sid]["recipe_sha256"] = "0" * 64
    with pytest.raises(ValueError, match="locked slot"):
        state.freeze_stage(tmp_path, lock["version"], "H4", wrong)
    state.freeze_stage(tmp_path, lock["version"], "H4", records)
    records[sid]["predictor_sha256"] = "0" * 64
    with pytest.raises(ValueError, match="alternate"):
        state.freeze_stage(tmp_path, lock["version"], "H4", records)


def test_interrupted_report_publication_cannot_change_first_result(tmp_path, monkeypatch):
    lock = payload()
    state.create_version(tmp_path, lock)
    state.freeze_stage(tmp_path, lock["version"], "H3", exports(lock, "H3"))
    original = state.atomic_json

    def fail_report(path, value):
        if path.name == "report.json":
            raise OSError("simulated power loss after result reservation")
        return original(path, value)

    monkeypatch.setattr(state, "atomic_json", fail_report)
    with pytest.raises(OSError, match="power loss"):
        state.finish_stage(tmp_path, lock["version"], "H3", {"first": 1}, outcome="pass")
    monkeypatch.setattr(state, "atomic_json", original)
    with pytest.raises(ValueError, match="first stage report"):
        state.finish_stage(tmp_path, lock["version"], "H3", {"first": 2}, outcome="pass")
    with pytest.raises(ValueError, match="first stage report"):
        state.finish_stage(tmp_path, lock["version"], "H3", {"first": 1}, outcome="fail")
    assert (
        state.finish_stage(tmp_path, lock["version"], "H3", {"first": 1}, outcome="pass")["state"]
        == "H3_passed"
    )


def test_reserved_creation_resumes_only_same_lock_and_blocks_pool_reuse(tmp_path, monkeypatch):
    lock = payload()
    original = state.atomic_json

    def fail_lock(path, value):
        if path.name == "lock.json":
            raise OSError("simulated interruption")
        return original(path, value)

    monkeypatch.setattr(state, "atomic_json", fail_lock)
    with pytest.raises(OSError):
        state.create_version(tmp_path, lock)
    monkeypatch.setattr(state, "atomic_json", original)
    with pytest.raises(ValueError, match="fresh assessment pool"):
        state.create_version(tmp_path, payload("other-version"))
    wrong = deepcopy(lock)
    wrong["pipeline_sha256"] = "0" * 64
    with pytest.raises(ValueError, match="replace"):
        state.create_version(tmp_path, wrong)
    assert state.create_version(tmp_path, lock)["state"] == "locked"


def test_corrupted_releases_and_path_links_are_rejected(tmp_path):
    lock = payload()
    state.create_version(tmp_path, lock)
    state.freeze_stage(tmp_path, lock["version"], "H3", exports(lock, "H3"))
    path = tmp_path / lock["version"] / "H3" / "release.json"
    data = json.loads(path.read_bytes())
    data["exports"].pop(next(iter(data["exports"])))
    path.write_text(json.dumps(data))
    with pytest.raises(ValueError, match="frozen release changed"):
        state.status(tmp_path, lock["version"])
    (tmp_path / "linked-version").symlink_to(tmp_path / lock["version"], target_is_directory=True)
    with pytest.raises(ValueError, match="linked versions"):
        state.create_version(tmp_path, payload("new-version", "fresh-pool"))
    with pytest.raises(ValueError, match="version name"):
        state.status(tmp_path, "../elsewhere")


def test_concurrent_alternate_releases_commit_exactly_one(tmp_path):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Barrier

    lock = payload()
    state.create_version(tmp_path, lock)
    first = exports(lock, "H3")
    second = deepcopy(first)
    second[next(iter(second))]["predictions_sha256"] = "0" * 64
    barrier = Barrier(2)

    def attempt(records):
        barrier.wait(timeout=5)
        try:
            state.freeze_stage(tmp_path, lock["version"], "H3", records)
            return "committed"
        except ValueError as error:
            assert "alternate" in str(error)
            return "rejected"

    with ThreadPoolExecutor(max_workers=2) as executor:
        answers = list(executor.map(attempt, (first, second)))
    assert sorted(answers) == ["committed", "rejected"]
    assert state.status(tmp_path, lock["version"])["state"] == "H3_released"
