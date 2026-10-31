#!/usr/bin/env python3
"""Run a byte-bound isolated job; this does not authorize assessment."""

import argparse
import json
from pathlib import Path

from bullet_time.evaluation.job_evidence import run_bound, verify_bound
from bullet_time.provenance import identity, strict_json


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="operation", required=True)
    run = commands.add_parser("run")
    run.add_argument("--inputs", required=True, help="JSON absolute file path to SHA-256 map")
    run.add_argument("--artifact-output", required=True)
    run.add_argument("--expected-output", action="append", required=True)
    run.add_argument("--deny-root", action="append", required=True)
    run.add_argument("--probe-file", action="append", required=True)
    run.add_argument("--output", required=True)
    run.add_argument("--cwd", required=True)
    run.add_argument("--timeout-seconds", type=int, required=True)
    run.add_argument("command", nargs=argparse.REMAINDER)
    verify = commands.add_parser("verify")
    verify.add_argument("--output", required=True)
    verify.add_argument("--request-sha256", required=True)
    verify.add_argument("--evidence-sha256", required=True)
    args = parser.parse_args()
    if args.operation == "verify":
        result = verify_bound(
            args.output,
            expected_request_sha256=args.request_sha256,
            expected_evidence_sha256=args.evidence_sha256,
        )
    else:
        command = args.command[1:] if args.command[:1] == ["--"] else args.command
        result = run_bound(
            command,
            inputs=strict_json(Path(args.inputs).read_bytes()),
            artifact_output=args.artifact_output,
            expected_outputs=args.expected_output,
            denied_roots=args.deny_root,
            probe_files=args.probe_file,
            output=args.output,
            cwd=args.cwd,
            timeout_seconds=args.timeout_seconds,
        )
    print(
        json.dumps(
            {
                "status": result["status"],
                "request_sha256": result["request_sha256"],
                "evidence_sha256": identity(result),
                "assessment_authorized": False,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
