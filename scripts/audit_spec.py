#!/usr/bin/env python3
"""Reproduce mathematical checks of the proposal, not research experiments.

Default: standard-library grid enumeration and workload arithmetic.
--power: also integrate exact paired-Gaussian TOST power using SciPy.
This is not the production scheduler, an empirical power estimate, or a model test.
"""

import argparse
from collections import Counter
import hashlib
from itertools import combinations
import json
import math
from pathlib import Path
import platform
import random


def grid_checks():
    cells = [(t, c) for t in range(16) for c in range(16)]
    expected = Counter(cells)
    cases = 0

    def check(clips):
        nonlocal cases
        assert len(clips) == 16 and all(len(clip) == 16 for clip in clips)
        assert Counter(cell for clip in clips for cell in clip) == expected
        cases += 1

    time = [[(t, c) for t in range(16)] for c in range(16)]
    check(time)
    for direction in (-1, 1):
        for phase in range(16):
            check([[(t, (direction * c + phase) % 16) for c in range(16)]
                   for t in range(16)])
        check([[(t, (direction * t + phase) % 16) for t in range(16)]
               for phase in range(16)])

    # Enumerate every possible four-pass orientation assignment for each fraction.
    mixture_assignments = 0
    view = [[(t, c) for c in range(16)] for t in range(16)]
    for temporal_passes in range(5):
        for selected in combinations(range(4), temporal_passes):
            counts = Counter()
            for pass_id in range(4):
                clips = time if pass_id in selected else view
                check(clips)
                counts.update(cell for clip in clips for cell in clip)
            assert counts == Counter({cell: 4 for cell in cells})
            assert len(selected) == temporal_passes
            mixture_assignments += 1

    for seed in range(32):
        rng = random.Random(seed)
        check([rng.sample(clip, len(clip)) for clip in time])
        shuffled = rng.sample(cells, len(cells))
        check([shuffled[i:i + 16] for i in range(0, 256, 16)])

    return {"valid_partition_checks": cases,
            "four_pass_orientation_assignments": mixture_assignments,
            "scope": "Index identities only; no renderer/loader/masks/optimizer validation"}


def power_checks():
    import scipy
    from scipy.integrate import quad
    from scipy.stats import chi2, norm, t

    def power(n, sd):
        # At true difference 0 and margin 1 percentage point, accept iff
        # |mean| + t(.95,n-1)*s/sqrt(n) < 1. Conditional on sample variance,
        # mean is Gaussian and independent; integrate over chi-square variance.
        df = n - 1
        critical = t.ppf(.95, df)
        scaled_margin = math.sqrt(n) / sd
        upper = df * (scaled_margin / critical) ** 2
        value, error = quad(
            lambda y: chi2.pdf(y, df) * max(
                0, 2 * norm.cdf(scaled_margin - critical * math.sqrt(y / df)) - 1),
            0, upper, epsabs=1e-10,
        )
        assert error < 1e-7
        return value

    rows = []
    for sd, rounded_expected in ((.5, .95), (1, .29), (2, .02)):
        p5 = power(5, sd)
        assert abs(p5 - rounded_expected) < .01
        n80 = next(n for n in range(2, 100) if power(n, sd) >= .8)
        rows.append({"paired_sd_pp": sd, "n5_power": p5,
                     "first_n_at_least_80_percent": n80,
                     "power_at_that_n": power(n80, sd)})
    return {"scipy_version": scipy.__version__,
            "assumptions": "iid Gaussian paired run differences, true mean 0, margin +/-1 pp, alpha .05; one contrast only",
            "single_contrast": rows,
            "hypothetical_independent_95_percent_components_all30": .95 ** 30,
            "hypothetical_independent_95_percent_components_all70": .95 ** 70,
            "note": "Actual contrasts share View and endpoints; independence powers are illustrations, not project forecasts"}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--power", action="store_true", help="Requires SciPy; no installation performed")
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    result = {
        "scope": "Proposal arithmetic and index audit only; no empirical research results",
        "python_version": platform.python_version(),
        "spec_sha256": hashlib.sha256((root / "SPEC.md").read_bytes()).hexdigest(),
        "audit_script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "grid": grid_checks(),
        "workload": {
            "full_images": 12000 * 256,
            "full_raw_rgb_decimal_GB": 12000 * 256 * 224 * 224 * 3 / 1e9,
            "pilot_raw_rgb_decimal_GB": 1000 * 256 * 224 * 224 * 3 / 1e9,
            "clips_per_full_pass": 12000 * 16,
            "clips_per_run_20_passes": 20 * 12000 * 16,
            "main_runs_at_n5_n11_n36": [16 * n for n in (5, 11, 36)],
            "main80_gpu_hours_at_100_clips_per_second": 80 * 20 * 12000 * 16 / 100 / 3600,
            "main80_gpu_hours_at_20_clips_per_second": 80 * 20 * 12000 * 16 / 20 / 3600,
            "render_hours_at_10_images_per_second": 12000 * 256 / 10 / 3600,
            "render_hours_at_1_image_per_second": 12000 * 256 / 3600,
        },
        "contrast_scope": {
            "view_relative_primary": 5 * 2 * 3,
            "view_relative_family_specific": 5 * 2 * 7,
            "all_pairs_primary_if_requested": math.comb(6, 2) * 2 * 3,
            "all_pairs_family_specific_if_requested": math.comb(6, 2) * 2 * 7,
            "counterexample_pp": {"view": 0, "arm_a": -.9, "arm_b": .9,
                                  "each_within_1_of_view": True, "a_b_difference": 1.8},
        },
    }
    if args.power:
        result["tost_power"] = power_checks()
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
