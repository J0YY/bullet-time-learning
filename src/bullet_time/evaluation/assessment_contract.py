"""Compare delivered fits with pre-H3 recipes without freezing unknown outcomes.

These checks validate artifact metadata, not data admission, actual checkpoint
execution, isolation or release authority. Use the execution boundary's byte-bound
receipts for those checks before the staged scorer is enabled.
"""

from copy import deepcopy
from pathlib import Path

from bullet_time.provenance import digest, identity, sha256
from .access import prediction_access
from .training import ReadoutConfig
from .scoring import EXPECTED, file_json, load_expected, read_predictions
from .score_plan import validate_fit, source_binding
from bullet_time.training.runner import code_identity


FIXED_FIT_FIELDS = (
    "config",
    "consumer_admission",
    "dev_episodes",
    "execution",
    "horizon_seconds",
    "image_manifest_sha256",
    "input_sha256",
    "label_sha256",
    "selection",
    "train_episodes",
    "training_episode_ids",
)


def fit_recipe(fit, *, inference_execution, input_sha256, image_manifest_sha256):
    """The fixed recipe can be constructed before a future fit/checkpoint exists.

    Include exact data/subset/source/runtime/initialization and full configurations.
    Exclude only fit outcomes (history, losses, fitted parameter hashes) and a
    learned backbone's future checkpoint bytes. Reference checkpoint bytes are
    already available and remain pinned. Actual delivered hashes append later.
    """
    fixed = {key: deepcopy(fit[key]) for key in FIXED_FIT_FIELDS}
    source = deepcopy(fit["backbone_source"])
    if "reference_status" in source["binding"]:
        sha256(source["checkpoint_sha256"])
    elif "checkpoint_sha256" in source:
        sha256(source.pop("checkpoint_sha256"))
    fixed["backbone_source"] = source
    return {
        "schema_version": "bullet-time.assessment-fit-recipe.v1",
        "fit": fixed,
        "inference": {
            "execution": deepcopy(inference_execution),
            "input_sha256": sha256(input_sha256),
            "image_manifest_sha256": sha256(image_manifest_sha256),
        },
    }


def expected_input_identity(rows):
    """Public task/query/group/target commitments, independent of future predictor IDs."""
    keys = EXPECTED - {"run_id", "checkpoint_id", "label_budget", "readout_seed"}
    normalized = [{key: row[key] for key in keys} for row in rows]

    def order(row):
        return tuple(
            row[key] for key in ("task_id", "episode_or_video_id", "query_id", "horizon_or_frame")
        )

    if not normalized or len({order(row) for row in normalized}) != len(normalized):
        raise ValueError("expected inputs must be nonempty and unique")
    return identity(sorted(normalized, key=order))


def verifier_binding():
    return {
        "consumer_sha256": code_identity(),
        "scoring": source_binding(),
        "contract_sha256": digest(Path(__file__).read_bytes()),
    }


def verify_predictor(
    fit_path, predictions, expected_path, design, recipe_sha256, *, split="assessment"
):
    """Verify one actual fit/export against an already committed recipe hash.

    Does not open labels. Expected keys must come from the separate locked pool
    inventory, not this prediction export. Missing rows remain explicit failures.
    Development mode supports testing and historical audits; neither grants release.
    """
    if split not in ("dev", "assessment"):
        raise ValueError("unsupported prediction contract split")
    fit_path, predictions, expected_path = map(Path, (fit_path, predictions, expected_path))
    execution = verifier_binding()
    artifacts = {
        "fit": fit_path,
        "expected": expected_path,
        **{name: predictions / name for name in ("run.json", "coverage.json", "predictions.csv")},
    }
    before = {name: digest(path.read_bytes()) for name, path in artifacts.items()}
    fit_bytes = fit_path.read_bytes()
    fit = file_json(fit_path)
    metadata = file_json(predictions / "run.json")
    if metadata.get("split") != split:
        raise ValueError("prediction metadata split differs from locked pool")
    config = ReadoutConfig(**fit["config"])
    config.validate()
    allowed = prediction_access(config, fit["backbone_source"])
    if metadata.get("allowed_prediction_splits") != allowed or split not in allowed:
        raise ValueError("predictor is not eligible for this split")
    if sha256(metadata["inference_execution"]["source_sha256"]) != sha256(
        fit["execution"]["source_sha256"]
    ):
        raise ValueError("inference consumer differs from fitted consumer")
    recipe = fit_recipe(
        fit,
        inference_execution=metadata["inference_execution"],
        input_sha256=metadata["input_sha256"],
        image_manifest_sha256=metadata["image_manifest_sha256"],
    )
    if identity(recipe) != sha256(recipe_sha256):
        raise ValueError("actual fit/inference recipe differs from the pre-H3 lock")
    expected = load_expected(expected_path, split)
    first = next(iter(expected.values()))
    if any(first[k] != design[k] for k in ("task_id", "label_budget", "readout_seed")):
        raise ValueError("expected inventory differs from declared task/seed/budget")
    horizons = {r["horizon_or_frame"] for r in expected.values()}
    if design["task_id"] == "tracking":
        if design["horizon"] != "tracking":
            raise ValueError("expected tracking horizon differs")
    elif horizons != {design["horizon"]}:
        raise ValueError("expected classification horizon differs")
    fit_check = validate_fit(design, first, fit, metadata, digest(fit_bytes))
    observed, provenance = read_predictions(predictions, expected, config.classes)
    predictor = {
        "prediction_identity": metadata["prediction_identity"],
        "fit_sha256": digest(fit_bytes),
        "readout_sha256": sha256(metadata["readout_sha256"]),
        "backbone_checkpoint_sha256": sha256(fit["backbone_source"]["checkpoint_sha256"]),
    }
    # Prevent mutation between the parsing/hash and the actual contract comparison.
    if before != {name: digest(path.read_bytes()) for name, path in artifacts.items()}:
        raise ValueError("fit/export/expected artifacts changed during contract verification")
    if verifier_binding() != execution:
        raise ValueError("contract verifier source/runtime changed")
    return {
        "schema_version": "bullet-time.assessment-predictor-binding.v1",
        "execution": execution,
        "artifacts": before,
        "predictor": predictor,
        "predictor_sha256": identity(predictor),
        "recipe_sha256": identity(recipe),
        "expected_inputs_sha256": expected_input_identity(expected.values()),
        "expected_keys_sha256": before["expected"],
        "provenance": provenance,
        "fit_check": fit_check,
        "complete": all(row["status"] == "ok" for row in observed.values()),
        "expected_rows": len(expected),
        "assessment_authorized": False,
        "scientific_gate_pass": False,
    }
