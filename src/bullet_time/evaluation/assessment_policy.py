"""Fixed inventories and numerical H3 rules for the two-stage exploratory pilot.

This module does not open labels, authorize release, or certify input isolation.
"""

from collections import Counter, defaultdict

from bullet_time.provenance import identity
from bullet_time.training.plan import pilot_slots


POLICY = "bullet-time.pilot-assessment-policy.v1"
TASKS = ("collision", "order", "tracking")


def stage_inventory():
    """Derive both locked stages from the existing 360-fit execution plan."""
    plan = pilot_slots()
    h3 = {s["slot_id"]: s for s in plan["supervised_diagnostics"]}
    h4 = {
        s["slot_id"]: s
        for s in plan["readouts"]
        if s["task"] in TASKS and s["checkpoint_pass"] in (0, 20)
    }
    development = {s["slot_id"] for s in plan["readouts"]} - h4.keys()
    if (len(h3), len(h4), len(development)) != (7, 243, 117):
        raise ValueError("pilot fit inventory changed; version assessment policy explicitly")
    result = {
        "schema_version": POLICY,
        "stages": {"H3": h3, "H4": h4},
        "development_only": sorted(development),
        "assessment_episodes_per_task": 400,
        "pool_reuse": "same exploratory pool in both stages; not independent replication",
        "retry_policy": "same frozen artifacts only; no replacement or new inspection",
        "failure_policy": "retain failed version; outcome-driven repairs require fresh pool",
        "execution_plan_sha256": plan["plan_sha256"],
    }
    return {**result, "inventory_sha256": identity(result)}


def _paired_probabilities(rows):
    groups = defaultdict(list)
    for row in rows:
        groups[row["group_id"]].append(row)
    return bool(groups) and all(
        len(pair) == 2
        and {r["target"]["contact"] for r in pair} == {0, 1}
        and abs(
            pair[0]["prediction"]["contact_probability"]
            - pair[1]["prediction"]["contact_probability"]
        )
        <= 1e-6
        for pair in groups.values()
    )


def h3_verdict(reports):
    """Evaluate all seven complete 400-episode assessment diagnostics together.

    Call only with score_directory-format reports created by the locked scorer.
    This checks quantitative sensitivity; physical validity, identical restricted
    inputs and deterministic execution also require their separately bound audits.
    """
    planned = stage_inventory()["stages"]["H3"]
    if set(reports) != set(planned):
        raise ValueError("H3 requires exactly all seven declared diagnostics")
    scores = {}
    populations = {}
    incomplete = []
    for sid, descriptor in planned.items():
        report = reports[sid]
        task, mode = (descriptor["readout"][key] for key in ("task", "mode"))
        if (
            report.get("schema_version") != "bullet-time.score.v1"
            or report.get("split") != "assessment"
            or report.get("task_id") != task
            or report.get("expected_families") != ["projectile_arena"]
            or report.get("horizon") != ("tracking" if task == "tracking" else "0.5")
        ):
            raise ValueError("H3 score has wrong task, split, family or primary horizon")
        rows = report["rows"]
        population = {
            (r["episode_id"], r["query_id"], r["horizon_or_frame"]): (
                r["group_id"],
                r["family"],
                identity(r["target"]),
            )
            for r in rows
        }
        if len(population) != len(rows):
            raise ValueError("duplicate H3 measurement row")
        if task in populations and population != populations[task]:
            raise ValueError("H3 diagnostics must share exactly the same task pool and targets")
        populations[task] = population
        episodes = {r["episode_id"] for r in rows}
        groups = defaultdict(set)
        for row in rows:
            groups[row["group_id"]].add(row["episode_id"])
        if len(episodes) != 400 or any(
            len(members) != (1 if task == "tracking" else 2) for members in groups.values()
        ):
            raise ValueError("H3 requires all 400 episodes and complete declared groups per task")
        if task != "tracking" and len(rows) != 400:
            raise ValueError("one H3 primary classification query per episode required")
        if report.get("complete") is not True or any(r["status"] != "ok" for r in rows):
            incomplete.append(sid)
        scores[task, mode] = report
    if incomplete:
        return {
            "gate": "H3",
            "verdict": "incomplete",
            "incomplete_slots": incomplete,
            "checks": {},
            "expansion_allowed": False,
        }
    # Recompute metrics rather than trusting report-level values copied by a caller.
    from .metrics import summarize

    primary = {}
    for key, report in scores.items():
        recomputed = summarize(report["rows"], ["projectile_arena"])
        if (
            not recomputed["complete"]
            or recomputed["primary"] != report["primary"]
            or recomputed["families"] != report["families"]
        ):
            raise ValueError("H3 score summary differs from its actual rows")
        primary[key] = recomputed["primary"]
    checks = {}
    for task in ("collision", "order"):
        sequence = primary[task, "sequence"]
        final = primary[task, "final_frame"]
        checks[f"{task}_sequence_at_least_80pct"] = sequence >= 0.8
        checks[f"{task}_sequence_over_final_20points"] = sequence >= final + 0.2 - 1e-12
        checks[f"{task}_final_chance"] = abs(final - 0.5) <= 0.001 + 1e-12
        checks[f"{task}_final_paired_probabilities"] = _paired_probabilities(
            scores[task, "final_frame"]["rows"]
        )
    bag = primary["order", "bag"]
    checks["order_sequence_over_bag_20points"] = primary["order", "sequence"] >= bag + 0.2 - 1e-12
    checks["order_bag_chance"] = abs(bag - 0.5) <= 0.001 + 1e-12
    checks["order_bag_paired_probabilities"] = _paired_probabilities(scores["order", "bag"]["rows"])
    checks["tracking_sequence_at_least_70pct"] = primary["tracking", "sequence"] >= 0.7
    checks["tracking_sequence_over_current_10points"] = (
        primary["tracking", "sequence"] >= primary["tracking", "current_frame"] + 0.1 - 1e-12
    )
    return {
        "gate": "H3",
        "verdict": "pass" if all(checks.values()) else "fail",
        "checks": checks,
        "incomplete_slots": [],
        "expansion_allowed": False,
        "reason": "quantitative H3 only; locked access/input audits and early stability also required",
        "scores": {f"{task}/{mode}": value for (task, mode), value in primary.items()},
        "planned_slots": dict(Counter(d["readout"]["task"] for d in planned.values())),
    }
