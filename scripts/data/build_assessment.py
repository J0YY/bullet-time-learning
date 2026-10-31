#!/usr/bin/env python3
"""Build a private native assessment prefix; never release or score assessment."""

import argparse
import json
from bullet_time.generation.assessment_capture import build_prefix, verify_source

p = argparse.ArgumentParser(description=__doc__)
p.add_argument("--output", required=True)
p.add_argument("--selection")
p.add_argument("--godot")
p.add_argument("--per-task", type=int, choices=(1, 8), default=1)
p.add_argument("--reuse-captures")
p.add_argument("--verify-only", action="store_true")
a = p.parse_args()
if a.verify_only:
    report = verify_source(a.output)
else:
    if not a.selection or not a.godot:
        p.error("capture requires --selection and --godot")
    report = build_prefix(
        a.output, a.godot, a.selection, per_task=a.per_task, reuse=a.reuse_captures
    )
print(json.dumps(report, indent=2))
