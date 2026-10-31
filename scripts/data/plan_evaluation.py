#!/usr/bin/env python3
"""Select the full pilot train/dev groups without rendering or accessing assessment."""

import argparse
import json

from bullet_time.generation.evaluation_selection import plan_collection, verify_selection

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--output", required=True)
parser.add_argument("--verify-only", action="store_true")
args = parser.parse_args()
report = verify_selection(args.output) if args.verify_only else plan_collection(args.output)
print(json.dumps(report["summary"], indent=2))
