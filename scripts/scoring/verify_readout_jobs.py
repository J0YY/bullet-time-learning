#!/usr/bin/env python3
"""Verify already-completed fit/inference jobs; never authorize assessment release."""

import argparse
import json
from pathlib import Path

from bullet_time.evaluation.readout_execution import verify_readout_execution
from bullet_time.provenance import atomic_json, digest, fields, strict_json

p = argparse.ArgumentParser(description=__doc__)
p.add_argument("--plan", required=True)
p.add_argument("--output", required=True)
a = p.parse_args()
plan_path, output = Path(a.plan), Path(a.output)
if output.exists() or output.is_symlink():
    raise ValueError("readout verification output already exists")
raw = plan_path.read_bytes()
plan = strict_json(raw)
fields(
    plan,
    {
        "schema_version",
        "fit_job",
        "prediction_job",
        "expected_path",
        "design",
        "recipe_sha256",
        "private_roots",
        "assessment_roots",
        "split",
    },
)
if plan.pop("schema_version") != "bullet-time.readout-execution-plan.v1":
    raise ValueError("unsupported readout execution plan")
result = verify_readout_execution(**plan)
if plan_path.read_bytes() != raw:
    raise ValueError("readout verification plan changed")
result.update(plan_sha256=digest(raw), cli_sha256=digest(Path(__file__).read_bytes()))
atomic_json(output, result)
print(
    json.dumps(
        {k: result[k] for k in ("complete", "assessment_authorized", "scientific_gate_pass")},
        indent=2,
    )
)
