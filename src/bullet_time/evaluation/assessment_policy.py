"""Fixed inventories and numerical H3/H4 screens for the exploratory pilot.

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


def h4_inventory():
    """All final/reference heads, including internal-development SSv2 heads."""
    result = {s["slot_id"]: s for s in pilot_slots()["readouts"] if s["checkpoint_pass"] in (0, 20)}
    if len(result) != 324:
        raise ValueError("H4 inventory changed; version policy explicitly")
    return result


def _h4_score(report, descriptor):
    from .metrics import summarize
    from .scoring import validate_target
    from bullet_time.provenance import integer, number, sha256, text_id

    task = descriptor["task"]
    external = task == "ssv2"
    split = "dev" if external else "assessment"
    horizon = "clip" if external else "tracking" if task == "tracking" else "0.5"
    if (
        report.get("schema_version") != "bullet-time.score.v1"
        or report.get("split") != split
        or report.get("task_id") != task
        or report.get("horizon") != horizon
    ):
        raise ValueError("H4 report task/split/primary horizon differs")
    families = report["expected_families"]
    if (not external and families != ["projectile_arena"]) or len(families) != 1:
        raise ValueError("H4 requires one fixed task family")
    predictor = report["predictor"]
    if predictor["task_id"] != task or predictor["readout_seed"] != descriptor["readout"]["seed"]:
        raise ValueError("H4 predictor task/readout seed differs from slot")
    integer(predictor["label_budget"], "actual label budget", 1)
    if not external and predictor["label_budget"] != 300:
        raise ValueError("H4 game heads require the fixed 300-label budget")
    for key in ("run_id", "checkpoint_id"):
        sha256(predictor[key])
    rows = report["rows"]
    population, groups, episodes = {}, defaultdict(set), {}
    for row in rows:
        for key in ("episode_id", "query_id", "horizon_or_frame", "group_id", "family"):
            text_id(row[key], key)
        if row["task_id"] != task or row["family"] != families[0]:
            raise ValueError("H4 row task/family differs")
        if task != "tracking" and row["horizon_or_frame"] != horizon:
            raise ValueError("H4 row primary horizon differs")
        # Reuse target validation with a transient dev header; no labels file is
        # opened, and the report's real split above remains assessment for games.
        validate_target(
            {
                "schema_version": "bullet-time.labels.v1",
                "split": "dev",
                **{
                    k: row[k]
                    for k in ("task_id", "episode_id", "query_id", "horizon_or_frame", "target")
                },
            }
        )
        key = tuple(row[k] for k in ("episode_id", "query_id", "horizon_or_frame"))
        if key in population:
            raise ValueError("duplicate H4 row")
        population[key] = (row["group_id"], row["family"], identity(row["target"]))
        eid, gid = row["episode_id"], row["group_id"]
        if eid in episodes and episodes[eid] != gid:
            raise ValueError("H4 episode spans multiple groups")
        episodes[eid] = gid
        groups[gid].add(eid)
        if row["status"] == "ok":
            p = row["prediction"]
            if task in ("collision", "order"):
                number(p["contact_probability"], "probability", 0, 1)
            elif task == "tracking":
                for name in ("x", "y", "visibility_probability"):
                    number(p[name], name, 0, 1)
            elif integer(p["class_id"], "class ID") >= 174:
                raise ValueError("invalid H4 class ID")
        elif row["status"] not in ("failed", "missing") or not row["error"] or row["prediction"]:
            raise ValueError("invalid H4 failed prediction")
    if not external:
        group_size = 1 if task == "tracking" else 2
        if len(episodes) != 400 or any(len(g) != group_size for g in groups.values()):
            raise ValueError("H4 requires 400 game episodes in complete groups")
        if task != "tracking":
            pairs = defaultdict(list)
            for row in rows:
                pairs[row["group_id"]].append(row["target"]["contact"])
            if any(sorted(pair) != [0, 1] for pair in pairs.values()):
                raise ValueError("H4 classification groups need opposite-label pairs")
    actual = summarize(rows, families)
    if any(report.get(k) != actual[k] for k in actual):
        raise ValueError("H4 score summary differs from actual rows")
    return actual, population


def h4_verdict(reports):
    """Recompute fixed numerical screens; never authorize a launch or claim H4.

    Input reports must already have validated slot-to-fit and execution bindings.
    This is arithmetic/coverage validation only, not that admission adapter. The
    precision/resource gate, early stability, H1/H2/H3 and locked stage access are
    separate. SSv2 must be internal dev, never official validation/final test.
    """
    from .metrics import mean
    from bullet_time.provenance import text_id

    planned = h4_inventory()
    if set(reports) != set(planned):
        raise ValueError("H4 requires all 324 final/reference slots, with explicit failures")
    populations, run_ids, actual_runs, budgets, values = {}, {}, {}, {}, {}
    incomplete = []
    for sid, descriptor in planned.items():
        report = reports[sid]
        if report.get("status") == "failed":
            if set(report) != {"status", "error"}:
                raise ValueError("invalid H4 failed slot")
            text_id(report["error"], "H4 slot failure")
            incomplete.append(sid)
            continue
        actual, population = _h4_score(report, descriptor)
        task, run = descriptor["task"], descriptor["run_id"]
        if task in populations and populations[task] != population:
            raise ValueError("H4 slots must share exactly the same task pool and targets")
        populations[task] = population
        predictor = report["predictor"]
        model = (predictor["run_id"], predictor["checkpoint_id"])
        if run in run_ids and run_ids[run] != model:
            raise ValueError("H4 heads for a planned run must use the same checkpoint")
        if model in actual_runs and actual_runs[model] != run:
            raise ValueError("H4 different planned runs cannot reuse one actual predictor")
        run_ids[run], actual_runs[model] = model, run
        if task in budgets and budgets[task] != predictor["label_budget"]:
            raise ValueError("H4 task label budgets differ")
        budgets[task] = predictor["label_budget"]
        if not actual["complete"]:
            incomplete.append(sid)
        values[sid] = actual["primary"]
    result = {
        "gate": "H4 numerical screens",
        "verdict": "incomplete",
        "checks": {},
        "incomplete_slots": incomplete,
        "slot_scores": values,
        "planned_slots": len(planned),
        "assessment_authorized": False,
        "scientific_gate_pass": False,
        "main_launch_allowed": False,
        "reason": "Numerical screens only; admitted fixed slots, H1/H2/H3, early stability, precision/resources and stage access remain required",
    }
    if incomplete:
        return result
    # Average readout seeds within checkpoint, then pretraining seeds, then the
    # three predeclared coherent conditions. No frame/episode pooling across heads.
    checkpoint_values = defaultdict(list)
    for sid, descriptor in planned.items():
        checkpoint_values[descriptor["run_id"], descriptor["task"]].append(values[sid])
    checkpoints = {key: mean(v) for key, v in checkpoint_values.items()}
    plan = pilot_slots()
    run_descriptors = {s["run_id"]: s for s in plan["training"] + plan["references"]}
    grouped = defaultdict(list)
    for (run, task), value in checkpoints.items():
        descriptor = run_descriptors[run]
        grouped[descriptor["kind"], descriptor.get("condition", descriptor["kind"]), task].append(
            value
        )
    arm = {key: mean(v) for key, v in grouped.items()}
    tasks = (*TASKS, "ssv2")
    coherent = {
        t: mean([arm["controlled", c, t] for c in ("view", "time", "mix50")]) for t in tasks
    }
    untrained = {t: arm["untrained", "untrained", t] for t in tasks}
    learning = {t: coherent[t] - untrained[t] for t in ("collision", "tracking")}
    grouping = {t: coherent[t] - arm["controlled", "regrouped", t] for t in tasks}
    native_deltas = {
        f"{condition}/{task}": checkpoints[f"pilot-v1-controlled-{condition}-s17", task]
        - checkpoints[f"pilot-v1-native-{condition}-s17", task]
        for condition in ("view", "time")
        for task in tasks
    }
    external = arm["external_image", "external_image", "ssv2"]
    transfer_threshold = untrained["ssv2"] + max(0.05, 0.5 * (external - untrained["ssv2"]))
    checks = {
        "learning_game_gain_at_least_5points": any(v >= 0.05 - 1e-12 for v in learning.values()),
        **{
            f"native_recipe/{key}": v >= (-0.02 if key.endswith("/ssv2") else -0.05) - 1e-12
            for key, v in native_deltas.items()
        },
        "external_reference_over_untrained_5points": external >= untrained["ssv2"] + 0.05 - 1e-12,
        "controlled_external_competence": coherent["ssv2"] >= transfer_threshold - 1e-12,
        "grouping_sensitivity": any(
            grouping[t] >= margin - 1e-12
            for t, margin in (("collision", 0.02), ("tracking", 0.02), ("ssv2", 0.01))
        ),
    }
    result.update(
        verdict="pass" if all(checks.values()) else "fail",
        checks=checks,
        checkpoint_scores={f"{r}/{t}": v for (r, t), v in checkpoints.items()},
        arm_scores={"/".join(k): v for k, v in arm.items()},
        coherent_scores=coherent,
        learning_differences=learning,
        native_recipe_differences=native_deltas,
        grouping_differences=grouping,
        external_competence_threshold=transfer_threshold,
    )
    return result
