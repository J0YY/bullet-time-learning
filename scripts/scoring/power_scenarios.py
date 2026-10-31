#!/usr/bin/env python3
"""Prospective 30/70-component power scenarios; no empirical sample-size choice."""

import argparse
from pathlib import Path

from bullet_time.evaluation.statistics import simulate_joint_power
from bullet_time.evaluation.score_plan import source_binding
from bullet_time.provenance import atomic_json, digest

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--output", required=True)
args = parser.parse_args()
path = Path(args.output)
if path.exists():
    parser.error("output already exists")
rows = []
for components in [30, 70]:
    for n in [5, 11, 36]:
        for ratio in [0.5, 1.0, 2.0]:
            for correlation in [0.0, 0.5, 1.0]:
                result = simulate_joint_power(
                    n, 20261030, [ratio] * components, 1.0, correlation, trials=5000
                )
                rows.append(
                    dict(
                        components=components,
                        paired_seeds=n,
                        paired_sd_in_margin_units=ratio,
                        equicorrelation=correlation,
                        global_power=result["global_power"],
                        monte_carlo_interval_95=result["monte_carlo_interval_95"],
                        component_power_range=[
                            min(result["component_power"]),
                            max(result["component_power"]),
                        ],
                    )
                )
report = dict(
    schema_version="bullet-time.prospective-power.v1",
    planning_only=True,
    scientific_claim_pass=False,
    assumptions="Gaussian paired run differences; zero true effect; each endpoint normalized by its future margin; common SD/margin ratio and nonnegative equicorrelation. These are sensitivity scenarios, not observed estimates or a freeze.",
    trials_per_scenario=5000,
    rng_seed=20261030,
    execution=source_binding(),
    script_sha256=digest(Path(__file__).read_bytes()),
    scenarios=rows,
)
atomic_json(path, report)
for row in rows:
    if row["paired_sd_in_margin_units"] == 1.0:
        print(row["components"], row["paired_seeds"], row["equicorrelation"], row["global_power"])
