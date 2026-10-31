#!/usr/bin/env python3
"""Build or verify the bounded train/dev measurement integration drop."""

import argparse
import json
from bullet_time.generation.evaluation_bundle import build_measurements, verify_measurements

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--output", required=True)
parser.add_argument("--godot")
parser.add_argument("--development", action="store_true")
parser.add_argument("--verify-only", action="store_true")
args = parser.parse_args()
if args.verify_only:
    report = verify_measurements(args.output)
else:
    if not args.godot:
        parser.error("--godot is required to render")
    report = build_measurements(args.output, args.godot, development=args.development)
print(json.dumps(report, indent=2, sort_keys=True))
