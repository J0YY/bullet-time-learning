#!/usr/bin/env python3
"""Prepare private randomized labels and public commitments; never release scores."""

import argparse
import os
from pathlib import Path

from bullet_time.evaluation.label_contract import seal_assessment_labels
from bullet_time.evaluation import label_contract, scoring
from bullet_time import provenance
from bullet_time.provenance import atomic_json, canonical_bytes, digest, strict_json


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--private-labels", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    root = Path(args.output)
    if root.exists():
        parser.error("output already exists; sealed versions are immutable")
    rows = [strict_json(line) for line in Path(args.private_labels).read_bytes().splitlines()]
    sealed, public = seal_assessment_labels(rows)
    root.mkdir(mode=0o700, parents=True, exist_ok=False)
    (root / "private").mkdir(mode=0o700)
    (root / "public").mkdir()
    private = root / "private/labels.jsonl"
    with private.open("xb") as stream:
        os.chmod(private, 0o600)
        stream.write(b"".join(canonical_bytes(row) + b"\n" for row in sealed))
    atomic_json(root / "public/target-commitments.json", public)
    atomic_json(
        root / "public/sealing.json",
        {
            "schema_version": "bullet-time.label-sealing.v1",
            "records": len(sealed),
            "labels_sha256": digest(private.read_bytes()),
            "commitments_sha256": digest((root / "public/target-commitments.json").read_bytes()),
            "nonce_source": "secrets.token_hex(32), independent per record",
            "script_sha256": digest(Path(__file__).read_bytes()),
            "source_sha256": {
                module.__name__: digest(Path(module.__file__).read_bytes())
                for module in (label_contract, scoring, provenance)
            },
            "job_isolation_verified": False,
            "assessment_release_authorized": False,
        },
    )
    print(f"Sealed {len(sealed)} private targets; no assessment release authorized.")


if __name__ == "__main__":
    main()
