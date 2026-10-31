"""Known-answer H4 arithmetic; synthetic rows are not assessment evidence."""

from copy import deepcopy
from functools import lru_cache

import pytest

from bullet_time.evaluation.assessment_policy import h4_inventory, h4_verdict
from bullet_time.evaluation.metrics import summarize
from bullet_time.provenance import identity
from scoring.test_assessment_policy import reports as h3_reports


@lru_cache(None)
def template(task, correct):
    if task == "ssv2":
        rows = [
            dict(
                task_id=task,
                episode_id=f"video-{e}",
                query_id="q",
                horizon_or_frame="clip",
                group_id=f"video-{e // 2}",
                family="ssv2",
                target={"class_id": e % 2},
                prediction={"class_id": e % 2 if e < correct else 1 - e % 2},
                status="ok",
                error="",
            )
            for e in range(400)
        ]
        families, split, horizon = ["ssv2"], "dev", "clip"
    else:
        rows = h3_reports()[f"pilot-v1-supervised-{task}-sequence"]["rows"]
        for row in rows:
            e = int(row["episode_id"].rsplit("-", 1)[1])
            if task == "tracking":
                row["prediction"]["x"] = 0.5 if e < correct else 0
            else:
                row["prediction"]["contact_probability"] = (
                    row["target"]["contact"] if e < correct else 1 - row["target"]["contact"]
                )
        families, split, horizon = (
            ["projectile_arena"],
            "assessment",
            "tracking" if task == "tracking" else "0.5",
        )
    return dict(
        schema_version="bullet-time.score.v1",
        split=split,
        horizon=horizon,
        rows=rows,
        **summarize(rows, families),
    )


def fixtures(overrides=None):
    overrides = overrides or {}
    reports = {}
    for sid, slot in h4_inventory().items():
        run, task = slot["run_id"], slot["task"]
        correct = 240
        if "-untrained-" in run:
            correct = 200 if task == "ssv2" else 220
        elif "-dinov2-" in run:
            correct = 280
        elif "-native-" in run:
            correct = 248 if task == "ssv2" else 260
        elif "-regrouped-" in run:
            correct = 236 if task == "ssv2" else 232
        correct = overrides.get((run, task), correct)
        report = dict(template(task, correct))
        report["predictor"] = dict(
            run_id=identity(run),
            checkpoint_id=identity([run, "checkpoint"]),
            task_id=task,
            label_budget=300 if task != "ssv2" else 2000,
            readout_seed=slot["readout"]["seed"],
        )
        reports[sid] = report
    return reports


def test_exact_boundaries_and_full_inventory_pass_without_granting_h4_or_launch():
    planned = h4_inventory()
    assert len(planned) == 324
    assert sum(p["task"] == "ssv2" for p in planned.values()) == 81
    result = h4_verdict(fixtures())
    assert result["verdict"] == "pass" and all(result["checks"].values())
    assert result["coherent_scores"]["collision"] == pytest.approx(0.6)
    assert result["learning_differences"]["tracking"] == pytest.approx(0.05)
    assert result["external_competence_threshold"] == pytest.approx(0.6)
    assert len(result["checkpoint_scores"]) == 108
    assert not result["assessment_authorized"] and not result["scientific_gate_pass"]
    assert not result["main_launch_allowed"]


def test_readout_and_pretraining_seed_hierarchy_preserves_each_arm():
    overrides = {
        (f"pilot-v1-controlled-{c}-s{s}", t): n
        for c, n in (("view", 200), ("time", 240), ("mix50", 280))
        for s in (17, 29, 43)
        for t in ("collision", "order", "tracking", "ssv2")
    }
    data = fixtures(overrides)
    sid = "pilot-v1-controlled-view-s17-p20-collision-r101"
    data[sid] = {**template("collision", 320), "predictor": data[sid]["predictor"]}
    result = h4_verdict(data)
    assert result["checkpoint_scores"]["pilot-v1-controlled-view-s17/collision"] == pytest.approx(
        0.6
    )
    assert result["arm_scores"]["controlled/view/collision"] == pytest.approx((0.6 + 0.5 + 0.5) / 3)
    assert result["coherent_scores"]["collision"] == pytest.approx(
        ((0.6 + 0.5 + 0.5) / 3 + 0.6 + 0.7) / 3
    )
    assert result["checks"]["native_recipe/view/collision"]
    assert not result["checks"]["native_recipe/view/order"]


@pytest.mark.parametrize("task", ["order", "ssv2"])
def test_one_native_endpoint_below_tolerance_fails_even_if_pooled_scores_pass(task):
    data = fixtures({("pilot-v1-native-time-s17", task): 249 if task == "ssv2" else 261})
    result = h4_verdict(data)
    assert result["verdict"] == "fail"
    assert not result["checks"][f"native_recipe/time/{task}"]


def test_order_only_improvement_cannot_rescue_primary_grouping_or_learning():
    data = fixtures(
        {
            (f"pilot-v1-controlled-{c}-s{s}", t): 220 if c != "regrouped" else 220
            for c in ("view", "time", "mix50", "regrouped")
            for s in (17, 29, 43)
            for t in ("collision", "tracking", "ssv2")
        }
    )
    result = h4_verdict(data)
    assert not result["checks"]["learning_game_gain_at_least_5points"]
    assert not result["checks"]["grouping_sensitivity"]
    assert result["grouping_differences"]["order"] == pytest.approx(0.02)


@pytest.mark.parametrize("mode", ["whole_slot", "prediction"])
def test_failed_unused_image_reference_still_makes_entire_inventory_incomplete(mode):
    data = fixtures()
    sid = "pilot-v1-image_mae-image_only-s43-p20-order-r103"
    if mode == "whole_slot":
        data[sid] = {"status": "failed", "error": "synthetic fit failure"}
    else:
        data[sid] = deepcopy(data[sid])
        r = data[sid]
        r["rows"][0].update(status="missing", error="synthetic missing prediction", prediction={})
        r.update(summarize(r["rows"], r["expected_families"]))
    result = h4_verdict(data)
    assert result["verdict"] == "incomplete" and result["incomplete_slots"] == [sid]
    assert result["checks"] == {} and "coherent_scores" not in result


@pytest.mark.parametrize(
    "mutation,match",
    [
        ("drop", "324"),
        ("early", "324"),
        ("split", "split"),
        ("summary", "summary"),
        ("pool", "same task pool"),
        ("duplicate", "duplicate"),
        ("checkpoint", "same checkpoint"),
        ("seed", "seed"),
        ("budget", "budget"),
        ("probability", "outside allowed range"),
    ],
)
def test_changed_slots_counts_pools_bindings_and_report_claims_rejected(mutation, match):
    data = fixtures()
    sid = "pilot-v1-controlled-view-s17-p20-collision-r101"
    report = deepcopy(data[sid])
    data[sid] = report
    if mutation == "drop":
        data.pop(sid)
    elif mutation == "early":
        data[sid.replace("p20", "p4")] = data.pop(sid)
    elif mutation == "split":
        report["split"] = "dev"
    elif mutation == "summary":
        report["primary"] = 1
    elif mutation == "pool":
        report["rows"][0]["query_id"] = "changed"
    elif mutation == "duplicate":
        report["rows"].append(deepcopy(report["rows"][0]))
    elif mutation == "checkpoint":
        report["predictor"]["checkpoint_id"] = "a" * 64
    elif mutation == "seed":
        report["predictor"]["readout_seed"] = 102
    elif mutation == "budget":
        report["predictor"]["label_budget"] = 600
    elif mutation == "probability":
        report["rows"][0]["prediction"]["contact_probability"] = 2
    with pytest.raises(ValueError, match=match):
        h4_verdict(data)


def test_cli_binds_actual_reports_and_keeps_failed_slots(tmp_path):
    import json
    from pathlib import Path
    import subprocess
    import sys
    from bullet_time.provenance import atomic_json, digest

    failed = tmp_path / "failed.json"
    atomic_json(failed, {"status": "failed", "error": "synthetic undelivered fit"})
    plan = tmp_path / "plan.json"
    atomic_json(
        plan,
        {
            "schema_version": "bullet-time.h4-numerical-plan.v1",
            "reports": {
                sid: {"path": failed.name, "sha256": digest(failed.read_bytes())}
                for sid in h4_inventory()
            },
        },
    )
    output = tmp_path / "result.json"
    script = Path(__file__).resolve().parents[2] / "scripts/scoring/pilot_h4.py"
    command = [sys.executable, str(script), "--plan", str(plan), "--output", str(output)]
    run = subprocess.run(command, text=True, capture_output=True)
    assert run.returncode == 0, run.stderr
    result = json.loads(output.read_bytes())
    assert result["verdict"] == "incomplete" and len(result["incomplete_slots"]) == 324
    assert result["plan_sha256"] == digest(plan.read_bytes())
    assert not result["main_launch_allowed"]
    failed.write_text("{}")
    command[-1] = str(tmp_path / "changed.json")
    run = subprocess.run(command, text=True, capture_output=True)
    assert run.returncode != 0 and "hash mismatch" in run.stderr
    assert not Path(command[-1]).exists()
