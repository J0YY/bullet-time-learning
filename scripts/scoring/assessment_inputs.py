#!/usr/bin/env python3
"""Compile a label-free expected-input inventory; never lock or release assessment."""

import argparse
import json
from pathlib import Path

from bullet_time.evaluation.assessment_inputs import compile_inputs
from bullet_time.provenance import atomic_json

p = argparse.ArgumentParser(description=__doc__)
p.add_argument("--public", required=True)
p.add_argument("--output", required=True)
p.add_argument(
    "--allow-partial", action="store_true", help="diagnostic inventories only; no pilot admission"
)
a = p.parse_args()
output = Path(a.output)
if output.resolve().is_relative_to(Path(a.public).resolve()):
    raise ValueError("inventory output must be outside immutable public inputs")
if output.exists() or output.is_symlink():
    raise ValueError("expected-input inventory output already exists")
report = compile_inputs(a.public, allow_partial=a.allow_partial)
atomic_json(output, report)
print(
    json.dumps(
        {key: report[key] for key in ("counts", "pilot_counts_complete", "assessment_authorized")},
        indent=2,
    )
)
