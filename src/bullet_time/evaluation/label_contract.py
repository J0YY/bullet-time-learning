"""Private label headers and randomized assessment commitments.

Commitments prevent guessing a low-entropy target from its public hash. They do
not make the private data inaccessible; job isolation is a separate requirement.
"""

import secrets

from bullet_time.provenance import fields, identity, sha256

LABEL_FIELDS = {
    "schema_version",
    "task_id",
    "episode_id",
    "query_id",
    "horizon_or_frame",
    "split",
    "target",
}


def validate_label_header(row):
    version = row.get("schema_version") if isinstance(row, dict) else None
    if version == "bullet-time.labels.v1":
        fields(row, LABEL_FIELDS)
        if row["split"] == "assessment":
            raise ValueError("inaccessible assessment: labels require randomized v2 commitments")
        if row["split"] not in ("train", "dev"):
            raise ValueError("unsupported label split")
    elif version == "bullet-time.labels.v2":
        fields(row, LABEL_FIELDS | {"commitment_nonce"})
        if row["split"] != "assessment":
            raise ValueError("label v2 is reserved for assessment")
        sha256(row["commitment_nonce"])  # 256 private random bits, lower-case hex.
    else:
        raise ValueError("unsupported label schema")


def seal_assessment_labels(rows):
    """Convert private producer v1 rows; never seed nonces from public RNG/config."""
    # Import here to retain one operational target validator without making the
    # training consumer import scoring code. This function is producer-only.
    from .scoring import label_key, validate_target

    sealed, commitments, keys = [], [], set()
    for original in rows:
        fields(original, LABEL_FIELDS)
        if (
            original["schema_version"] != "bullet-time.labels.v1"
            or original["split"] != "assessment"
        ):
            raise ValueError("sealing expects private unsealed v1 assessment records")
        row = dict(
            original, schema_version="bullet-time.labels.v2", commitment_nonce=secrets.token_hex(32)
        )
        validate_target(row)
        key = label_key(row)
        if key in keys:
            raise ValueError("duplicate assessment target")
        keys.add(key)
        sealed.append(row)
        commitments.append(
            {
                **{
                    k: row[k]
                    for k in ("task_id", "episode_id", "query_id", "horizon_or_frame", "split")
                },
                "target_reference_sha256": identity(row),
            }
        )
    if not sealed:
        raise ValueError("empty assessment labels")
    return sealed, commitments
