from copy import deepcopy
from collections import Counter

import pytest

from bullet_time.evaluation.assessment_policy import stage_inventory, h3_verdict
from bullet_time.evaluation.metrics import summarize


def reports():
    result = {}
    for sid, descriptor in stage_inventory()["stages"]["H3"].items():
        task, mode = (descriptor["readout"][k] for k in ("task", "mode"))
        rows = []
        for episode in range(400):
            for frame in (25, 26, 27) if task == "tracking" else ("0.5",):
                if task == "tracking":
                    hit = episode < (280 if mode == "sequence" else 240)
                    target = dict(
                        x=0.5, y=0.5, visible=1, bbox_diagonal_pixels=32, prediction_role="primary"
                    )
                    prediction = dict(x=0.5 if hit else 0, y=0.5, visibility_probability=1)
                else:
                    label = episode % 2
                    target = {"contact": label}
                    correct = episode < 320
                    probability = (label if correct else 1 - label) if mode == "sequence" else 0.5
                    prediction = {"contact_probability": probability}
                rows.append(
                    dict(
                        task_id=task,
                        episode_id=f"{task}-{episode}",
                        query_id=str(frame),
                        horizon_or_frame=str(frame),
                        group_id=f"{task}-{episode if task == 'tracking' else episode // 2}",
                        family="projectile_arena",
                        target=target,
                        status="ok",
                        error="",
                        prediction=prediction,
                    )
                )
        result[sid] = dict(
            schema_version="bullet-time.score.v1",
            split="assessment",
            horizon="tracking" if task == "tracking" else "0.5",
            rows=rows,
            **summarize(rows, ["projectile_arena"]),
        )
    return result


def test_inventory_keeps_all_counts_and_excludes_early_and_ssv2():
    inventory = stage_inventory()
    assert len(inventory["stages"]["H3"]) == 7
    h4 = inventory["stages"]["H4"]
    assert len(h4) == 243 and len(inventory["development_only"]) == 117
    assert Counter(s["task"] for s in h4.values()) == dict.fromkeys(
        ("collision", "order", "tracking"), 81
    )
    assert all(s["checkpoint_pass"] in (0, 20) for s in h4.values())
    assert all(s["input_access"] == "train_dev_then_pilot_assessment" for s in h4.values())
    assert inventory == stage_inventory()


def test_all_exact_numeric_boundaries_pass_without_authorizing_expansion():
    result = h3_verdict(reports())
    assert result["verdict"] == "pass" and all(result["checks"].values())
    assert result["scores"]["tracking/sequence"] == 0.7
    assert not result["expansion_allowed"]


@pytest.mark.parametrize(
    "task,mode", [("collision", "sequence"), ("order", "sequence"), ("tracking", "sequence")]
)
def test_one_episode_below_threshold_fails(task, mode):
    data = reports()
    sid = f"pilot-v1-supervised-{task}-{mode}"
    report = data[sid]
    row = report["rows"][0]
    if task == "tracking":
        row["prediction"]["visibility_probability"] = 0
    else:
        row["prediction"]["contact_probability"] = 1 - row["target"]["contact"]
    report.update(summarize(report["rows"], ["projectile_arena"]))
    assert h3_verdict(data)["verdict"] == "fail"


def test_restricted_probability_shortcut_fails_even_if_ba_stays_at_chance():
    data = reports()
    report = data["pilot-v1-supervised-order-bag"]
    report["rows"][0]["prediction"]["contact_probability"] = 0.50001
    report.update(summarize(report["rows"], ["projectile_arena"]))
    result = h3_verdict(data)
    assert result["checks"]["order_bag_chance"]
    assert not result["checks"]["order_bag_paired_probabilities"]
    assert result["verdict"] == "fail"


def test_missing_prediction_blocks_all_h3_instead_of_scoring_success_subset():
    data = reports()
    sid = "pilot-v1-supervised-collision-sequence"
    data[sid]["rows"][0].update(status="missing", error="interrupted", prediction={})
    data[sid].update(summarize(data[sid]["rows"], ["projectile_arena"]))
    result = h3_verdict(data)
    assert result["verdict"] == "incomplete" and result["incomplete_slots"] == [sid]
    assert not result["checks"]


@pytest.mark.parametrize(
    "change,match",
    [
        (lambda d: d.pop("pilot-v1-supervised-order-bag"), "seven"),
        (lambda d: d["pilot-v1-supervised-order-bag"].update(split="dev"), "split"),
        (lambda d: d["pilot-v1-supervised-order-bag"]["rows"].pop(), "same task pool"),
        (
            lambda d: d["pilot-v1-supervised-order-bag"]["rows"].append(
                deepcopy(d["pilot-v1-supervised-order-bag"]["rows"][0])
            ),
            "duplicate",
        ),
        (lambda d: d["pilot-v1-supervised-order-sequence"].update(primary=1.0), "summary"),
    ],
)
def test_wrong_inventory_pool_or_claimed_score_is_rejected(change, match):
    data = reports()
    change(data)
    with pytest.raises(ValueError, match=match):
        h3_verdict(data)
