"""Bind launch scope to evidence, without mistaking receipts for scientific proof."""

from pathlib import Path
from dataclasses import asdict
from bullet_time.provenance import strict_json, fields, digest, inside, identity, sha256, integer


def admit(corpus, model, config, scope, *, receipt_path=None, stop_after_updates=None):
    if scope == "synthetic":
        marker = strict_json((corpus.root / "fixture.json").read_bytes())
        if (
            marker.get("synthetic_only") is not True
            or marker.get("manifest_sha256") != corpus.manifest_sha256
        ):
            raise ValueError("synthetic scope requires a matching explicit fixture marker")
        return {
            "scope": "synthetic",
            "scientific_gate_pass": False,
            "reason": "consumer fixture validation only",
        }
    if scope == "integration":
        if stop_after_updates is None or stop_after_updates > 1:
            raise ValueError("integration scope is a bounded single-update check")
        return {
            "scope": "integration",
            "scientific_gate_pass": False,
            "reason": "actual-input code check; renderer/split evidence separate",
        }
    if scope not in ("pilot_early", "pilot_full", "reference"):
        raise ValueError("unknown scope")
    if receipt_path is None:
        raise ValueError(
            "real pilot requires hashed H1/H2/resource admission; full expansion also H3/early stability"
        )
    path = Path(receipt_path).resolve(strict=True)
    receipt = strict_json(path.read_bytes())
    required = {
        "schema_version",
        "scope",
        "corpus_sha256",
        "model_config_sha256",
        "training_config_sha256",
        "evidence",
        "maximum_updates",
        "approved_device",
    }
    fields(receipt, required)
    if receipt["schema_version"] != "bullet-time.admission.v1" or receipt["scope"] != scope:
        raise ValueError("admission scope/version mismatch")
    if (
        receipt["corpus_sha256"] != corpus.manifest_sha256
        or receipt["model_config_sha256"] != identity(asdict(model))
        or receipt["training_config_sha256"] != identity(asdict(config))
    ):
        raise ValueError("admission does not bind current data/config")
    if receipt["approved_device"] != config.device:
        raise ValueError("resource device differs")
    integer(receipt["maximum_updates"], "maximum_updates", 1)
    if stop_after_updates is None or stop_after_updates > receipt["maximum_updates"]:
        raise ValueError("explicit stop exceeds admitted update cap")
    needed = {"H1", "H2", "resources"} | (
        {"H3", "early_stability"} if scope == "pilot_full" else set()
    )
    observed = set()
    for record in receipt["evidence"]:
        fields(record, {"gate", "path", "sha256"})
        if record["gate"] in observed:
            raise ValueError("duplicate evidence gate")
        sha256(record["sha256"])
        data = inside(path.parent, record["path"]).read_bytes()
        if digest(data) != record["sha256"]:
            raise ValueError("admission evidence changed")
        report = strict_json(data)
        if (
            report.get("gate") != record["gate"]
            or report.get("verdict") != "pass"
            or report.get("synthetic_only") is not False
        ):
            raise ValueError("gate report is not an accepted real-data assessment")
        if report.get("corpus_sha256") != corpus.manifest_sha256:
            raise ValueError("gate evidence does not bind the admitted corpus")
        observed.add(record["gate"])
    if not needed <= observed:
        raise ValueError("missing scientific/resource gate evidence")
    if (
        len(corpus.grids) != 1000
        or corpus.image_size != 224
        or config.total_passes != 20
        or config.grids_per_update != 8
    ):
        raise ValueError("not the frozen pilot corpus/update budget")
    if (
        model.patch_size != 16
        or model.encoder_width != 384
        or model.encoder_depth != 12
        or model.encoder_heads != 6
        or model.decoder_width != 192
        or model.decoder_depth != 4
        or model.decoder_heads != 3
    ):
        raise ValueError("not the declared pilot backbone/decoder")
    if any(grid.scene_family != "projectile_arena" for grid in corpus.grids):
        raise ValueError("pilot corpus must contain only the declared projectile arena family")
    if config.crop_fraction != 1 or config.color_jitter != 0:
        raise ValueError("initial pilot controlled grid transform is identity")
    if scope == "reference":
        image = (
            model.frames == 1
            and model.tubelet == 1
            and config.condition == "view"
            and config.recipe == "controlled"
            and config.mask_ratio == 0.75
            and config.seed in (17, 29, 43)
        )
        native = (
            model.frames == 16
            and model.tubelet == 2
            and config.recipe == "native"
            and config.condition in ("view", "time")
            and config.seed == 17
            and config.mask_ratio == 0.9
        )
        if not (image or native):
            raise ValueError("not a declared image/native reference slot")
    else:
        if (
            model.frames != 16
            or model.tubelet != 2
            or config.recipe != "controlled"
            or config.condition
            not in ("view", "time", "mix50", "joint", "shuffled_time", "regrouped")
            or config.seed not in (17, 29, 43)
        ):
            raise ValueError("not a declared controlled pilot slot")
        if config.mask_ratio != 0.9:
            raise ValueError("wrong controlled mask ratio")
    if scope == "pilot_early" and (
        config.condition not in ("view", "time", "mix50")
        or config.seed != 17
        or stop_after_updates > 500
    ):
        raise ValueError("early screen is seed-17 View/Time/Mix50 through four passes only")
    return {
        "scope": scope,
        "admission_sha256": digest(path.read_bytes()),
        "evidence_gates": sorted(observed),
        "scientific_gate_pass": "receipt binding checked; source evidence still requires scientific review",
    }
