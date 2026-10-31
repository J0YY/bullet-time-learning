#!/usr/bin/env python3
"""Prepare progressive pretraining grids; this command never launches learning."""

import argparse
import json
from pathlib import Path

from bullet_time.generation.bundle import ROOT
from bullet_time.generation.progressive_arena import build_progressive, verify_progressive

p = argparse.ArgumentParser(description=__doc__)
p.add_argument("--output", type=Path, required=True)
p.add_argument("--count", type=int, choices=[1, 8, 100, 1000], default=1)
p.add_argument(
    "--godot", type=Path, default=ROOT / ".cache/godot/4.5.1/Godot.app/Contents/MacOS/Godot"
)
p.add_argument("--reuse-captures", type=Path)
p.add_argument("--development", action="store_true")
p.add_argument("--verify-only", action="store_true")
a = p.parse_args()
result = (
    verify_progressive(a.output)
    if a.verify_only
    else build_progressive(
        a.output, a.count, a.godot, reuse=a.reuse_captures, development=a.development
    )
)
print(json.dumps(result, indent=2))
