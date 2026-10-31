"""Paired-seed inference and paired-group sensitivity; no confirmatory claim by default."""

from collections import defaultdict
import math
import numpy as np
from scipy.stats import t, norm, chi2
from bullet_time.provenance import integer, number
from .metrics import summarize


def paired_tost(differences, margin, alpha=0.05):
    values = np.asarray(differences, dtype=float)
    number(margin, "margin", 1e-12)
    number(alpha, "alpha", 1e-12, 0.499999)
    if values.ndim != 1 or len(values) < 2 or not np.isfinite(values).all():
        raise ValueError("at least two finite paired seed differences required")
    n = len(values)
    avg = float(values.mean())
    sd = float(values.std(ddof=1))
    se = sd / math.sqrt(n)
    result = {
        "n_paired_pretraining_seeds": n,
        "paired_differences": values.tolist(),
        "mean_difference": avg,
        "paired_sd": sd,
        "margin": margin,
        "alpha": alpha,
        "equivalent": False,
        "units": "score fraction; multiply by 100 for percentage points",
    }
    if se == 0:
        return {
            **result,
            "inference_available": False,
            "reason": "zero observed paired variance; no t-based equivalence claim",
            "component_interval": None,
            "conventional_interval": None,
            "p_tost": None,
            "p_superiority_two_sided": None,
        }
    half = float(t.ppf(1 - alpha, n - 1) * se)
    ci = [avg - half, avg + half]
    p_lower = float(t.sf((avg + margin) / se, n - 1))
    p_upper = float(t.cdf((avg - margin) / se, n - 1))
    conventional = float(t.ppf(0.975, n - 1) * se)
    result.update(
        inference_available=True,
        component_interval=ci,
        component_confidence=1 - 2 * alpha,
        conventional_interval=[avg - conventional, avg + conventional],
        conventional_confidence=0.95,
        p_lower=p_lower,
        p_upper=p_upper,
        p_tost=max(p_lower, p_upper),
        p_superiority_two_sided=float(2 * t.sf(abs(avg / se), n - 1)),
        equivalent=bool(ci[0] > -margin and ci[1] < margin),
        paired_sd_interval_95=[
            math.sqrt((n - 1) * sd * sd / chi2.ppf(0.975, n - 1)),
            math.sqrt((n - 1) * sd * sd / chi2.ppf(0.025, n - 1)),
        ],
    )
    return result


def holm(p_values, alpha=0.05):
    if not p_values:
        raise ValueError("empty multiple-testing family")
    for p in p_values.values():
        number(p, "p value", 0, 1)
    ordered = sorted(p_values, key=p_values.get)
    m = len(ordered)
    previous = 0
    out = {}
    for i, key in enumerate(ordered):
        adjusted = min(1.0, max(previous, (m - i) * p_values[key]))
        previous = adjusted
        out[key] = {
            "raw_p": p_values[key],
            "holm_adjusted_p": adjusted,
            "reject": adjusted <= alpha,
        }
    return out


def main_components(per_family=False):
    endpoints = ["collision", "tracking", "ssv2"]
    if per_family:
        endpoints = [
            f"{task}/{family}"
            for task in ["collision", "tracking"]
            for family in ["projectile_arena", "moving_platform_course", "object_handling_room"]
        ] + ["ssv2"]
    return [
        f"{objective}:{condition}-view:{endpoint}"
        for objective in ["videomae_raw_rgb", "vjepa"]
        for condition in ["mix25", "mix50", "mix75", "time", "joint"]
        for endpoint in endpoints
    ]


def conjunction(components, *, per_family=False):
    expected = main_components(per_family)
    missing = sorted(set(expected) - components.keys())
    extra = sorted(components.keys() - set(expected))
    complete = not missing and not extra
    return {
        "expected_components": len(expected),
        "missing": missing,
        "extra": extra,
        "complete": complete,
        "all_components_equivalent": complete
        and all(
            components[k].get("equivalent") is True
            and components[k].get("inference_available") is True
            and components[k].get("alpha") == 0.05
            for k in expected
        ),
        "claim": "all declared contrasts relative to View; not all-pairs equivalence",
        "scientific_claim_pass": False,
        "reason": "statistical component calculation alone does not establish frozen protocol or validity/learning gates",
    }


def _label_signature(report):
    return sorted(
        (
            r["task_id"],
            r["episode_id"],
            r["query_id"],
            r["horizon_or_frame"],
            r["family"],
            r["group_id"],
            tuple(sorted(r["target"].items())),
        )
        for r in report["rows"]
    )


def paired_reports(left, right, training_seeds, readout_seeds, margin):
    """Maps (pretraining seed, readout seed) to score reports; no seed pseudoreplication."""
    wanted = {(s, r) for s in training_seeds for r in readout_seeds}
    if len(wanted) != len(training_seeds) * len(readout_seeds) or len(readout_seeds) != 3:
        raise ValueError("require three distinct readout seeds and distinct pretraining seeds")
    missing = {
        "left": [list(x) for x in sorted(wanted - left.keys())],
        "reference": [list(x) for x in sorted(wanted - right.keys())],
    }
    if left.keys() - wanted or right.keys() - wanted:
        raise ValueError("unplanned seed cell")
    if any(missing.values()):
        return {"complete": False, "missing_seed_cells": missing, "inference": None}
    reports = list(left.values()) + list(right.values())
    if any(not r["complete"] for r in reports):
        return {
            "complete": False,
            "reason": "failed/missing prediction coverage",
            "inference": None,
        }
    reference = reports[0]
    signature = _label_signature(reference)
    for r in reports:
        if (
            r["expected_families"] != reference["expected_families"]
            or r["task_id"] != reference["task_id"]
            or r["horizon"] != reference["horizon"]
            or r["split"] != reference["split"]
            or _label_signature(r) != signature
        ):
            raise ValueError("unpaired evaluation inventory/labels/groups/families")
        if r.get("readout_training") != reference.get("readout_training"):
            raise ValueError("unpaired fitted readout training inventories/bindings")
    for side in (left, right):
        seen_checkpoints = set()
        for seed in training_seeds:
            checkpoints = set()
            for readout in readout_seeds:
                report = side[seed, readout]
                predictor = report["predictor"]
                if predictor["readout_seed"] != readout:
                    raise ValueError("readout seed differs from paired cell")
                # Supervised diagnostics identify the fitted head in the prediction
                # wire. Their bound parent backbone is the unit being paired here.
                backbone = report.get("backbone_identity", predictor)
                checkpoints.add((backbone["run_id"], backbone["checkpoint_id"]))
            if len(checkpoints) != 1:
                raise ValueError("readout seeds do not share one backbone checkpoint")
            checkpoint = next(iter(checkpoints))
            if checkpoint in seen_checkpoints:
                raise ValueError("same backbone counted as distinct pretraining seeds")
            seen_checkpoints.add(checkpoint)
    averages = []
    differences = []
    for seed in training_seeds:
        condition_scores = [left[seed, r]["primary"] for r in readout_seeds]
        ref = [right[seed, r]["primary"] for r in readout_seeds]
        delta = float(np.mean(condition_scores) - np.mean(ref))
        differences.append(delta)
        averages.append(
            {
                "pretraining_seed": seed,
                "condition_scores": condition_scores,
                "reference_scores": ref,
                "condition_mean": float(np.mean(condition_scores)),
                "reference_mean": float(np.mean(ref)),
                "condition_readout_sd": float(np.std(condition_scores, ddof=1)),
                "reference_readout_sd": float(np.std(ref, ddof=1)),
                "paired_difference": delta,
            }
        )
    return {
        "complete": True,
        "seed_averages": averages,
        "inference": paired_tost(differences, margin),
        "readout_seeds": readout_seeds,
        "pretraining_seeds": training_seeds,
        "scientific_claim_pass": False,
    }


def paired_group_bootstrap(
    left, right, training_seeds, readout_seeds, *, replicates=2000, seed=20261028, crossed=False
):
    """Resample whole paired groups within family/outcome strata, identically for all arms.

    Crossed sensitivity also resamples pretraining seeds. Readout seeds are averaged,
    never counted as independent pretraining seeds. It is not the primary TOST CI.
    """
    check = paired_reports(left, right, training_seeds, readout_seeds, margin=0.02)
    if not check["complete"]:
        return {"complete": False, "reason": "paired coverage incomplete"}
    integer(replicates, "replicates", 100)
    integer(seed, "bootstrap seed")
    baseline = next(iter(left.values()))
    task = baseline["task_id"]
    families = baseline["expected_families"]
    group_rows = defaultdict(list)
    for row in baseline["rows"]:
        group_rows[row["group_id"]].append(row)
    strata = defaultdict(list)
    for gid, rows in group_rows.items():
        if task == "tracking":
            primary = [r for r in rows if r["target"]["prediction_role"] == "primary"]
            outcome = (
                "small"
                if any(r["target"]["bbox_diagonal_pixels"] < 16 for r in primary)
                else "primary",
            )
        elif task in ("collision", "order"):
            outcome = tuple(sorted(r["target"]["contact"] for r in rows))
        else:
            outcome = ()  # video groups, no per-frame resampling
        strata[(rows[0]["family"], outcome)].append(gid)
    groups_by_report = {}
    for side, reports in [("condition", left), ("reference", right)]:
        for key, report in reports.items():
            lookup = defaultdict(list)
            for row in report["rows"]:
                lookup[row["group_id"]].append(row)
            groups_by_report[(side, *key)] = lookup
    rng = np.random.default_rng(seed)
    values = []
    for _ in range(replicates):
        sampled = [
            str(g)
            for groups in strata.values()
            for g in rng.choice(sorted(groups), size=len(groups), replace=True)
        ]
        seeds = (
            rng.choice(training_seeds, size=len(training_seeds), replace=True).tolist()
            if crossed
            else training_seeds
        )
        deltas = []
        for s in seeds:
            sides = []
            for side in ["condition", "reference"]:
                readouts = []
                for rs in readout_seeds:
                    lookup = groups_by_report[(side, s, rs)]
                    rows = []
                    for index, gid in enumerate(sampled):
                        rows.extend(
                            {
                                **r,
                                "episode_id": f"{index}/{r['episode_id']}",
                                "group_id": f"{index}/{gid}",
                            }
                            for r in lookup[gid]
                        )
                    report = summarize(rows, families)
                    if not report["complete"]:
                        raise ValueError("bootstrap lost valid metric coverage")
                    readouts.append(report["primary"])
                sides.append(float(np.mean(readouts)))
            deltas.append(sides[0] - sides[1])
        values.append(float(np.mean(deltas)))
    return {
        "complete": True,
        "replicates": replicates,
        "seed": seed,
        "crossed_seed_and_group": crossed,
        "percentile_interval_95": np.quantile(values, [0.025, 0.975]).tolist(),
        "bootstrap_sd": float(np.std(values, ddof=1)),
        "unit": "whole related group within family/outcome stratum; paired across arms and seeds",
        "interpretation": "sensitivity conditional on corpus; few training seeds limit tail reliability; not primary TOST",
    }


def simulate_joint_power(n, seeds, sd, margin, correlation, *, trials=5000, true_difference=0.0):
    """Gaussian paired differences with equicorrelation; prospective scenario only.

    n = paired training seeds; seeds = RNG seed (not repeated observations).
    Vector dimensions are the declared components, e.g. 30 or 70.
    """
    integer(n, "sample size", 2)
    integer(seeds, "simulation seed")
    integer(trials, "trials", 100)
    sigma = np.asarray(sd, dtype=float)
    margins = np.broadcast_to(np.asarray(margin, dtype=float), sigma.shape)
    if (
        sigma.ndim != 1
        or not len(sigma)
        or not np.isfinite(sigma).all()
        or np.any(sigma <= 0)
        or not np.isfinite(margins).all()
        or np.any(margins <= 0)
    ):
        raise ValueError("positive finite SD/margin vectors required")
    number(correlation, "equicorrelation", 0, 1)
    number(true_difference, "true difference")
    rng = np.random.default_rng(seeds)
    critical = t.ppf(0.95, n - 1)
    hits = 0
    component_hits = np.zeros(len(sigma), dtype=np.int64)
    for start in range(0, trials, 128):
        size = min(128, trials - start)
        z = np.sqrt(correlation) * rng.normal(size=(size, n, 1)) + np.sqrt(
            1 - correlation
        ) * rng.normal(size=(size, n, len(sigma)))
        x = z * sigma + true_difference
        avg = x.mean(axis=1)
        half = critical * x.std(axis=1, ddof=1) / math.sqrt(n)
        passed = (avg - half > -margins) & (avg + half < margins)
        hits += int(passed.all(axis=1).sum())
        component_hits += passed.sum(axis=0)
    p = hits / trials
    z = norm.ppf(0.975)
    den = 1 + z * z / trials
    center = (p + z * z / (2 * trials)) / den
    half = z * math.sqrt(p * (1 - p) / trials + z * z / (4 * trials * trials)) / den
    return {
        "planning_only": True,
        "n_paired_seeds": n,
        "components": len(sigma),
        "trials": trials,
        "rng_seed": seeds,
        "paired_sd": sigma.tolist(),
        "margins": margins.tolist(),
        "equicorrelation": correlation,
        "true_difference": true_difference,
        "global_power": p,
        "monte_carlo_interval_95": [center - half, center + half],
        "component_power": (component_hits / trials).tolist(),
        "assumption": "Gaussian equicorrelated paired run differences; no empirical variance/power or sample-size freeze",
    }
