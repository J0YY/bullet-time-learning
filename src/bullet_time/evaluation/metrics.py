"""Operational metrics on validated prediction/label joins; never imports S4 code."""

from collections import defaultdict
import math
import numpy as np


def mean(values):
    return float(np.mean(values)) if values else None


def summarize(rows, families):
    """One task/horizon/predictor. Missing outputs invalidate scores, not denominators.

    Rows have episode_id, query_id, horizon_or_frame, family, group_id, status,
    prediction, target. Family inventory comes from the plan, never observed success.
    """
    if not rows or not families or len(set(families)) != len(families):
        raise ValueError("nonempty rows and distinct expected families required")
    if {r["family"] for r in rows} != set(families):
        raise ValueError("observed family inventory differs from plan")
    tasks = {r["task_id"] for r in rows}
    if len(tasks) != 1:
        raise ValueError("score one task at a time")
    task = next(iter(tasks))
    by_family = defaultdict(list)
    for row in rows:
        by_family[row["family"]].append(row)
    reports = {family: _family(task, by_family[family]) for family in families}
    complete = all(r["complete"] for r in reports.values())
    return {
        "task_id": task,
        "complete": complete,
        "primary": mean([r["primary"] for r in reports.values()]) if complete else None,
        "aggregation": "equal family mean" if len(families) > 1 else "single-family pilot score",
        "families": reports,
        "expected_families": families,
    }


def _family(task, rows):
    failed = [r for r in rows if r["status"] != "ok"]
    counts = {
        "expected": len(rows),
        "ok": len(rows) - len(failed),
        "failed": sum(r["status"] == "failed" for r in rows),
        "missing": sum(r["status"] == "missing" for r in rows),
    }
    base = {
        "coverage": counts,
        "complete": not failed,
        "primary": None,
        "episodes": len({r["episode_id"] for r in rows}),
        "groups": len({r["group_id"] for r in rows}),
    }
    if failed:
        base["reason"] = "incomplete prediction coverage; no successful-subset score"
        return base
    if task != "tracking" and len(rows) != len({r["episode_id"] for r in rows}):
        raise ValueError("one classification query per episode/horizon required")
    if task in ("collision", "order"):
        labels = [r["target"]["contact"] for r in rows]
        if set(labels) != {0, 1}:
            base.update(complete=False, reason="balanced accuracy needs both label classes")
            return base
        probabilities = [r["prediction"]["contact_probability"] for r in rows]
        recall = [
            mean([float((p >= 0.5) == y) for p, y in zip(probabilities, labels) if y == c])
            for c in [0, 1]
        ]
        base.update(
            primary=mean(recall),
            balanced_accuracy=mean(recall),
            class_recall=recall,
            brier=mean([(p - y) ** 2 for p, y in zip(probabilities, labels)]),
        )
    elif task == "ssv2":
        base["primary"] = base["top1"] = mean(
            [float(r["prediction"]["class_id"] == r["target"]["class_id"]) for r in rows]
        )
    elif task == "tracking":
        episodes = defaultdict(list)
        for row in rows:
            episodes[row["episode_id"]].append(row)
        primary, small, auxiliary, errors, visibility = [], [], [], [], []
        episode_scores = []
        for episode, windows in sorted(episodes.items()):
            scored = [r for r in windows if r["target"]["prediction_role"] == "primary"]
            frames = sorted(int(r["horizon_or_frame"]) for r in scored)
            if len(scored) != 3 or frames != list(range(frames[0], frames[0] + 3)):
                raise ValueError("tracking requires exactly three consecutive primary frames")
            if any(r["target"]["visible"] != 1 for r in scored):
                raise ValueError("primary tracking target is not visible")
            small_object = any(r["target"]["bbox_diagonal_pixels"] < 16 for r in scored)
            distances, visible, success = [], [], []
            for row in scored:
                y, p = row["target"], row["prediction"]
                distance = math.hypot(223 * (p["x"] - y["x"]), 223 * (p["y"] - y["y"]))
                tolerance = y["bbox_diagonal_pixels"] / 8
                correct_visibility = (p["visibility_probability"] >= 0.5) == bool(y["visible"])
                within = distance <= tolerance or math.isclose(
                    distance, tolerance, rel_tol=0, abs_tol=1e-12
                )
                success.append(within and correct_visibility)
                distances.append(distance / y["bbox_diagonal_pixels"])
                visible.append(float(correct_visibility))
            value = float(all(success))
            (small if small_object else primary).append(value)
            # Supporting metrics also weight episodes, not their number of queries.
            errors.append(mean(distances))
            visibility.append(mean(visible))
            aux = [r for r in windows if r["target"]["prediction_role"] == "auxiliary"]
            if aux:
                auxiliary.append(
                    mean(
                        [
                            float(
                                (r["prediction"]["visibility_probability"] >= 0.5)
                                == bool(r["target"]["visible"])
                            )
                            for r in aux
                        ]
                    )
                )
            episode_scores.append(
                {
                    "episode_id": episode,
                    "group_id": scored[0]["group_id"],
                    "small_object": small_object,
                    "reacquisition_success": value,
                    "normalized_errors": distances,
                    "success_by_tolerance": {
                        str(t): float(
                            all(
                                d <= t or math.isclose(d, t, abs_tol=1e-12, rel_tol=0)
                                for d in distances
                            )
                            and all(visible)
                        )
                        for t in [1 / 16, 1 / 8, 1 / 4]
                    },
                }
            )
        base.update(
            primary=mean(primary),
            primary_episodes=len(primary),
            small_object_episodes=len(small),
            small_object_success=mean(small),
            normalized_point_error=mean(errors),
            visibility_accuracy=mean(visibility),
            auxiliary_visibility_accuracy=mean(auxiliary),
            episode_scores=episode_scores,
        )
        if not primary:
            base.update(complete=False, reason="no eligible primary-size tracking episodes")
    else:
        raise ValueError("unsupported task")
    return base
