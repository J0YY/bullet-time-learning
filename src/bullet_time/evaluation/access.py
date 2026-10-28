"""Prediction identity and split eligibility carried by a fitted checkpoint."""

from dataclasses import asdict
from bullet_time.provenance import identity


def prediction_access(config, backbone_source):
    # SSv2 pilot development is drawn only from official training. Early or partial
    # learned checkpoints may not inspect game assessment either.
    if config.task == "ssv2" or not backbone_source["assessment_eligible"]:
        return ["dev"]
    return ["dev", "assessment"]


def prediction_ids(config, backbone_source, readout_sha256):
    if config.kind == "diagnostic":
        # A fine-tuned sequence/final/bag model is a different predictor even when
        # all start from the same external image checkpoint.
        return {
            "run_id": identity(
                {"backbone_run_id": backbone_source["run_id"], "diagnostic_config": asdict(config)}
            ),
            "checkpoint_id": readout_sha256,
        }
    return {
        "run_id": backbone_source["run_id"],
        "checkpoint_id": backbone_source["checkpoint_sha256"],
    }
