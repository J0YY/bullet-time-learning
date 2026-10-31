#!/usr/bin/env python3
"""Create/verify private assessment selection; never print reconstruction material."""

import argparse
import json
from pathlib import Path

from bullet_time.generation.assessment_selection import plan_assessment, verify_selection
from bullet_time.provenance import digest, strict_json

p = argparse.ArgumentParser(description=__doc__)
p.add_argument("--output", required=True)
p.add_argument("--known-sources", help="JSON list of private receipt paths and SHA-256 hashes")
p.add_argument("--verify-only", action="store_true")
p.add_argument(
    "--resume-private-config", help="retain the stream from an incomplete private selection"
)
a = p.parse_args()
if a.verify_only:
    if a.known_sources or a.resume_private_config:
        p.error("verification uses the already pinned private source list")
    report = verify_selection(a.output)
else:
    if not a.known_sources:
        p.error("creation requires known development/prior-assessment receipts")
    report = plan_assessment(
        a.output,
        strict_json(Path(a.known_sources).read_bytes()),
        resume_private_config=a.resume_private_config,
    )
print(
    json.dumps(
        {
            "groups_per_task": report["groups_per_task"],
            "episodes": report["episodes"],
            "prospective_rgb_images": report["prospective_rgb_images"],
            "receipt_sha256": digest((Path(a.output) / "selection.json").read_bytes()),
            "assessment_authorized": False,
            "scientific_gate_pass": False,
        },
        indent=2,
    )
)
