#!/usr/bin/env python3
"""Calculate fixed H4 numerical screens from already-scored, hash-bound reports."""

import argparse
import json
from pathlib import Path

from bullet_time.evaluation.assessment_policy import h4_inventory, h4_verdict
from bullet_time.evaluation import assessment_policy
from bullet_time.evaluation.score_plan import source_binding, bound_file
from bullet_time.provenance import atomic_json, digest, fields, identity, strict_json

p = argparse.ArgumentParser(description=__doc__)
p.add_argument("--plan", required=True)
p.add_argument("--output", required=True)
a = p.parse_args()
plan_path, output = Path(a.plan).resolve(strict=True), Path(a.output).resolve()
if output.exists() or Path(a.output).is_symlink():
    raise ValueError("H4 calculation output already exists")
plan_bytes = plan_path.read_bytes()
plan = strict_json(plan_bytes)
fields(plan, {"schema_version", "reports"})
if plan["schema_version"] != "bullet-time.h4-numerical-plan.v1":
    raise ValueError("unsupported H4 numerical plan")
if set(plan["reports"]) != set(h4_inventory()):
    raise ValueError("plan must retain all 324 H4 final/reference slots")
binding = {
    "policy_sha256": digest(Path(assessment_policy.__file__).read_bytes()),
    "cli_sha256": digest(Path(__file__).read_bytes()),
    "scoring": source_binding(),
    "inventory_sha256": identity(h4_inventory()),
}
paths = {sid: bound_file(plan_path.parent, record) for sid, record in plan["reports"].items()}
reports = {sid: strict_json(path.read_bytes()) for sid, path in paths.items()}
result = h4_verdict(reports)
if plan_path.read_bytes() != plan_bytes:
    raise ValueError("H4 plan changed during calculation")
for sid, path in paths.items():
    if digest(path.read_bytes()) != plan["reports"][sid]["sha256"]:
        raise ValueError("H4 input report changed during calculation")
if (
    digest(Path(assessment_policy.__file__).read_bytes()) != binding["policy_sha256"]
    or digest(Path(__file__).read_bytes()) != binding["cli_sha256"]
    or source_binding() != binding["scoring"]
    or identity(h4_inventory()) != binding["inventory_sha256"]
):
    raise ValueError("H4 calculation source changed")
result.update(
    schema_version="bullet-time.h4-numerical-report.v1",
    plan_sha256=digest(plan_bytes),
    source_binding=binding,
    report_sha256={sid: record["sha256"] for sid, record in plan["reports"].items()},
)
atomic_json(output, result)
print(
    json.dumps(
        {k: result[k] for k in ("gate", "verdict", "planned_slots", "main_launch_allowed")},
        indent=2,
    )
)
