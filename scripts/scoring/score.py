#!/usr/bin/env python3
"""Score an explicit development plan without dropping failed slots."""

import argparse
import json
from bullet_time.evaluation.score_plan import run_plan

p = argparse.ArgumentParser(description=__doc__)
p.add_argument("--plan", required=True)
p.add_argument("--output", required=True)
a = p.parse_args()
r = run_plan(a.plan, a.output)
print(
    json.dumps(
        {
            k: r[k]
            for k in [
                "scope",
                "complete",
                "planned_slots",
                "complete_slots",
                "scientific_claim_pass",
            ]
        },
        indent=2,
    )
)
