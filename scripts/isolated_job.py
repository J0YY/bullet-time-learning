#!/usr/bin/env python3
"""Run an explicitly bounded local job with private roots inaccessible."""

import argparse

from bullet_time.evaluation.isolated_job import run_isolated


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--deny-root", action="append", required=True)
    parser.add_argument("--probe-file", action="append", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--cwd", required=True)
    parser.add_argument("--timeout-seconds", type=int, required=True)
    parser.add_argument("command", nargs=argparse.REMAINDER)
    args = parser.parse_args()
    command = args.command[1:] if args.command[:1] == ["--"] else args.command
    result = run_isolated(
        command,
        denied_roots=args.deny_root,
        probe_files=args.probe_file,
        output=args.output,
        cwd=args.cwd,
        timeout_seconds=args.timeout_seconds,
    )
    print(result["status"])
    raise SystemExit(0 if result["status"] == "complete" else 1)


if __name__ == "__main__":
    main()
