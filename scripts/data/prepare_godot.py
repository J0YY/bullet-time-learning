#!/usr/bin/env python3
"""Install the checksum-pinned official macOS build into the project cache."""

import hashlib
import json
from pathlib import Path
import platform
import subprocess
import urllib.request

ROOT = Path(__file__).resolve().parents[2]
pin = json.loads((ROOT / "configs/rendering/godot-macos.json").read_text())
if platform.system() != "Darwin":
    raise SystemExit("This pin is macOS-only; add and validate an explicit platform pin first")
cache = ROOT / ".cache/godot/4.5.1"
cache.mkdir(parents=True, exist_ok=True)
archive = cache / "Godot.zip"
if not archive.exists():
    temporary = cache / "download.part"
    urllib.request.urlretrieve(pin["url"], temporary)
    if hashlib.sha256(temporary.read_bytes()).hexdigest() != pin["archive_sha256"]:
        raise SystemExit("Godot archive checksum mismatch")
    temporary.rename(archive)
if hashlib.sha256(archive.read_bytes()).hexdigest() != pin["archive_sha256"]:
    raise SystemExit("Godot archive checksum mismatch")
binary = cache / "Godot.app/Contents/MacOS/Godot"
if not binary.exists():
    subprocess.run(["ditto", "-x", "-k", str(archive), str(cache)], check=True)
if hashlib.sha256(binary.read_bytes()).hexdigest() != pin["binary_sha256"]:
    raise SystemExit("Godot binary checksum mismatch")
if subprocess.check_output([str(binary), "--version"], text=True).strip() != pin["version"]:
    raise SystemExit("Godot version mismatch")
print(binary)
