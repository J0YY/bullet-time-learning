#!/usr/bin/env python3
"""Check collaboration scaffolding only; no renderer/model/science validation."""

import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys
from urllib.parse import unquote, urlsplit


ROOT = Path(__file__).resolve().parents[1]
REQUIRED = (
    "SPEC.md", "README.md", "AGENTS.md", "CLAUDE.md", "SHARED_CONTEXT.md",
    "RUNBOOK.md", "division-of-labor.md", "joy-devlog.md", "sudarshan-devlog.md",
    "meta-feedback.md", "docs/interfaces.md", "reports/decisions.md",
    "reports/setup-audit.md", "reports/spec-source.json", ".gitignore",
    ".gitattributes", ".github/workflows/scaffold.yml", "scripts/check_scaffold.py",
)
IGNORED = (
    ".env", ".env.local", "credentials.key", "credentials.pem",
    ".venv/bin/python", "game/.godot/editor/state", "__pycache__/module.pyc",
    "data/raw/frame.png", "data/rendered/frame.png", "data/processed/bundle.bin",
    "data/cache/item.bin", "data/private/labels.json", "data/heldout/labels.json",
    "private/labels.json", "artifacts/grid.png", "runs/run.json", "results/scores.csv",
    "logs/run.log", "checkpoints/model.bin", "model.pt", "model.safetensors",
)
PUBLIC = (
    ".env.example", "game/project.godot", "data/manifests/example.json",
    "data/splits/example.json", "configs/pilot.yaml", "reports/example.md",
    "docs/example.md", "src/bullet_time/schema.py", "tests/test_loading.py",
    "paper/figures/example.png", ".github/workflows/scaffold.yml",
)


def git(*args, **kwargs):
    return subprocess.run(["git", "-C", str(ROOT), *args], check=True,
                          capture_output=True, **kwargs).stdout


def main():
    errors = []
    for name in REQUIRED:
        if not (ROOT / name).is_file():
            errors.append(f"Missing required file: {name}")
    if errors:
        return finish(errors)

    provenance = json.loads((ROOT / "reports/spec-source.json").read_text())
    original = git("show", f"{provenance['import_commit']}:{provenance['imported_path']}")
    if hashlib.sha256(original).hexdigest() != provenance["sha256"]:
        errors.append("Original SPEC Git blob does not match source SHA-256")
    if len(original) != provenance["size_bytes"]:
        errors.append("Original SPEC Git blob size does not match source size")
    current_hash = hashlib.sha256((ROOT / "SPEC.md").read_bytes()).hexdigest()
    if current_hash != provenance["sha256"]:
        decisions = (ROOT / "reports/decisions.md").read_text()
        if current_hash not in decisions:
            errors.append("Changed SPEC needs its current SHA-256 in reports/decisions.md")

    if (ROOT / "CLAUDE.md").read_text().strip() != "@AGENTS.md":
        errors.append("CLAUDE.md must import @AGENTS.md")

    # Include staged/untracked docs, avoiding ignored data and environment folders.
    names = git("ls-files", "--cached", "--others", "--exclude-standard", "-z")
    markdown = sorted({name.decode() for name in names.split(b"\0")
                       if name.endswith(b".md")})
    links = 0
    for name in markdown:
        path = ROOT / name
        if not path.is_file():  # A deleted optional document is not an input.
            continue
        fence = None
        for number, line in enumerate(path.read_text().splitlines(), 1):
            marker = re.match(r"^\s{0,3}(`{3,}|~{3,})", line)
            if marker:
                token = marker.group(1)
                if fence is None:
                    fence = token
                elif token[0] == fence[0] and len(token) >= len(fence):
                    fence = None
                continue
            if fence:
                continue
            # Scaffold uses inline Markdown links. URL fragments are not checked.
            for match in re.finditer(r"\[[^\]]*\]\((<[^>]+>|[^\s)]+)\)", line):
                href = match.group(1).strip("<>")
                parts = urlsplit(href)
                if parts.scheme or parts.netloc or not parts.path:
                    continue
                target = (path.parent / unquote(parts.path)).resolve()
                links += 1
                if not target.is_relative_to(ROOT) or not target.exists():
                    errors.append(f"{name}:{number}: invalid local link {href}")

    for should_ignore, paths in ((True, IGNORED), (False, PUBLIC)):
        for path in paths:
            result = subprocess.run(
                ["git", "-C", str(ROOT), "check-ignore", "--no-index", "-q", path],
                capture_output=True,
            )
            if result.returncode not in (0, 1):
                errors.append(f"Cannot check ignore rule: {path}")
            elif (result.returncode == 0) != should_ignore:
                errors.append(f"Unexpected ignore status: {path} (expected {should_ignore})")

    if errors:
        return finish(errors)
    print(f"PASS: {len(REQUIRED)} required files; {len(markdown)} Markdown files; "
          f"{links} local links; {len(IGNORED) + len(PUBLIC)} ignore checks")
    print(f"PASS: original SPEC provenance; current SPEC SHA-256 {current_hash}")
    print("Scope: scaffold integrity only; scientific implementation remains unvalidated.")
    return 0


def finish(errors):
    for error in errors:
        print(f"FAIL: {error}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (OSError, ValueError, KeyError, subprocess.CalledProcessError) as error:
        print(f"FAIL: {error}", file=sys.stderr)
        sys.exit(1)
