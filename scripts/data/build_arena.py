#!/usr/bin/env python3
"""Generate/verify the bounded real Godot integration bundle."""

import argparse
import json
from pathlib import Path
from bullet_time.generation.bundle import ROOT, build_bundle, verify_bundle

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--output", type=Path, required=True)
parser.add_argument("--count", type=int, choices=[1, 8], default=1)
parser.add_argument(
    "--godot", type=Path, default=ROOT / ".cache/godot/4.5.1/Godot.app/Contents/MacOS/Godot"
)
parser.add_argument("--plan", type=Path, default=ROOT / "configs/generation/arena-integration.json")
parser.add_argument("--reuse-preview", type=Path)
parser.add_argument("--development", action="store_true")
parser.add_argument("--verify-only", action="store_true")
args = parser.parse_args()
result = (
    verify_bundle(args.output)
    if args.verify_only
    else build_bundle(
        args.output, args.count, args.godot, args.plan, args.reuse_preview, args.development
    )
)
print(json.dumps({k: v for k, v in result.items() if k != "summaries"}, indent=2))
