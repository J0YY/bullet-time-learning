#!/usr/bin/env python3
"""Prepare opaque assessment inputs in the private producer environment; no release."""

import argparse
import json

from bullet_time.generation.assessment_export import prepare_assessment, verify_preparation

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--private-source")
parser.add_argument("--output", required=True)
parser.add_argument("--verify-only", action="store_true")
args = parser.parse_args()
if args.verify_only:
    if args.private_source:
        parser.error("verify-only does not accept a source")
    result = verify_preparation(args.output)
else:
    if not args.private_source:
        parser.error("private-source is required for preparation")
    result = prepare_assessment(args.private_source, args.output)
print(json.dumps(result["result"], indent=2))
