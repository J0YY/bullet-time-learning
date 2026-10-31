"""Operational ledger for predeclared scoring slots and paired contrasts."""

from pathlib import Path
import importlib.metadata
import platform

from bullet_time.provenance import (
    fields,
    integer,
    number,
    text_id,
    sha256,
    digest,
    identity,
    inside,
    atomic_json,
)
from .scoring import file_json, score_directory, load_expected
from .statistics import paired_reports, paired_group_bootstrap, holm

FACETS = (
    "objective",
    "task_id",
    "horizon",
    "label_budget",
    "checkpoint_pass",
    "model_kind",
    "corpus_sha256",
    "readout_recipe_sha256",
)
SLOT_FIELDS = set(FACETS) | {
    "slot_id",
    "condition",
    "pretraining_seed",
    "readout_seed",
    "expected",
    "predictions",
}


def source_binding():
    here = Path(__file__).resolve().parent
    files = [
        here / n
        for n in ["metrics.py", "scoring.py", "statistics.py", "score_plan.py", "export.py"]
    ] + [here.parent / "provenance.py"]
    return {
        "sources": {p.relative_to(here.parent).as_posix(): digest(p.read_bytes()) for p in files},
        "python": platform.python_version(),
        "numpy": importlib.metadata.version("numpy"),
        "scipy": importlib.metadata.version("scipy"),
    }


def bound_file(root, record):
    fields(record, {"path", "sha256"})
    sha256(record["sha256"])
    path = inside(root, record["path"])
    if digest(path.read_bytes()) != record["sha256"]:
        raise ValueError("planned input artifact hash mismatch")
    return path


def destination(root, relative):
    """Absent planned outputs are allowed; escaping paths and symlinks are not."""
    text_id(relative, "prediction path")
    path = Path(relative)
    if path.is_absolute() or ".." in path.parts or "\\" in relative:
        raise ValueError("prediction path escape")
    resolved = (root / path).resolve()
    if not resolved.is_relative_to(root.resolve()):
        raise ValueError("prediction path escape")
    return resolved


def validate_fit(slot, expected, fit, metadata, fit_sha256):
    """Match paired-seed/recipe claims to the actual consumer's fit and run records."""
    config = fit["config"]
    source = fit["backbone_source"]
    binding = source["binding"]
    if (
        metadata.get("fit_sha256") != fit_sha256
        or metadata.get("backbone_source") != source
        or metadata.get("readout_config") != config
        or metadata.get("fit_execution") != fit["execution"]
    ):
        raise ValueError("prediction does not bind the actual fit/source/config")
    if identity(binding) != source["run_id"]:
        raise ValueError("backbone run ID differs from its binding")
    if source["binding"]["training"]["seed"] != slot["pretraining_seed"]:
        raise ValueError("declared paired seed differs from actual backbone seed")
    if (
        config["seed"] != slot["readout_seed"]
        or config["task"] != slot["task_id"]
        or fit["train_episodes"] != slot["label_budget"]
    ):
        raise ValueError("declared readout task/seed/budget differs from actual fit")
    recipe = {k: v for k, v in config.items() if k != "seed"}
    if identity(recipe) != slot["readout_recipe_sha256"]:
        raise ValueError("declared readout recipe differs from actual fit")
    ids = {k: expected[k] for k in ["run_id", "checkpoint_id"]}
    if metadata.get("prediction_identity") != ids:
        raise ValueError("prediction identity differs from its fit")
    if config["kind"] == "diagnostic":
        actual = {
            "run_id": identity({"backbone_run_id": source["run_id"], "diagnostic_config": config}),
            "checkpoint_id": metadata["readout_sha256"],
        }
        kind, condition, objective, checkpoint_pass, corpus = (
            "diagnostic",
            config["mode"],
            "supervised",
            0,
            "0" * 64,
        )
    else:
        actual = {"run_id": source["run_id"], "checkpoint_id": source["checkpoint_sha256"]}
        if "reference_status" in binding:
            kind = (
                "external" if binding["reference_status"] == "external_pretrained" else "untrained"
            )
            condition, objective, checkpoint_pass, corpus = kind, kind, 0, "0" * 64
        else:
            training = binding["training"]
            steps = (binding["corpus_grids"] + training["grids_per_update"] - 1) // training[
                "grids_per_update"
            ]
            if source["global_step"] % steps:
                raise ValueError("analysis checkpoint is not at a completed pass")
            checkpoint_pass = source["global_step"] // steps
            kind = (
                "native"
                if training["recipe"] == "native"
                else "image_mae"
                if binding["model"]["frames"] == 1
                else "controlled"
            )
            objective = (
                "videomae_native"
                if kind == "native"
                else "image_mae_raw_rgb"
                if kind == "image_mae"
                else "videomae_raw_rgb"
            )
            condition, corpus = training["condition"], binding["corpus_sha256"]
    if actual != ids or any(
        slot[k] != v
        for k, v in {
            "model_kind": kind,
            "condition": condition,
            "objective": objective,
            "checkpoint_pass": checkpoint_pass,
            "corpus_sha256": corpus,
        }.items()
    ):
        raise ValueError("declared experimental slot differs from the fitted predictor")


def run_plan(plan_path, output):
    plan_path = Path(plan_path).resolve()
    root = plan_path.parent
    plan = file_json(plan_path)
    fields(
        plan,
        {
            "schema_version",
            "scope",
            "split",
            "families",
            "classes",
            "labels",
            "groups",
            "pretraining_seeds",
            "readout_seeds",
            "slots",
            "contrasts",
            "bootstrap",
        },
    )
    if (
        plan["schema_version"] != "bullet-time.scoring-plan.v1"
        or plan["scope"] not in ("synthetic", "development")
        or plan["split"] not in ("train", "dev")
    ):
        raise ValueError("unsupported scope: assessment requires the release workflow")
    for name in ["pretraining_seeds", "readout_seeds"]:
        seeds = plan[name]
        if not isinstance(seeds, list) or len(set(seeds)) != len(seeds):
            raise ValueError("duplicate/invalid seed inventory")
        for seed in seeds:
            integer(seed, name)
    if len(plan["readout_seeds"]) != 3 or len(plan["pretraining_seeds"]) < 2:
        raise ValueError(
            "paired plan requires three readout seeds and at least two pretraining seeds"
        )
    if (
        not isinstance(plan["families"], list)
        or not plan["families"]
        or len(set(plan["families"])) != len(plan["families"])
    ):
        raise ValueError("invalid expected family inventory")
    for family in plan["families"]:
        text_id(family, "family")
    integer(plan["classes"], "classes", 2)
    labels = bound_file(root, plan["labels"])
    groups = bound_file(root, plan["groups"])
    fields(plan["bootstrap"], {"replicates", "seed"})
    integer(plan["bootstrap"]["replicates"], "replicates", 100)
    integer(plan["bootstrap"]["seed"], "seed")
    if not plan["slots"]:
        raise ValueError("empty slot inventory")
    reports = {}
    slots = {}
    identities = set()
    designs = set()
    before = source_binding()
    for slot in plan["slots"]:
        fields(slot, SLOT_FIELDS, {"fit"})
        sid = text_id(slot["slot_id"], "slot_id")
        if sid in slots:
            raise ValueError("duplicate slot ID")
        for name in ["condition", "objective", "task_id", "horizon", "model_kind"]:
            text_id(slot[name], name)
        for name in ["label_budget", "checkpoint_pass", "pretraining_seed", "readout_seed"]:
            integer(slot[name], name)
        if slot["label_budget"] < 1:
            raise ValueError("positive label budget required")
        for name in ["corpus_sha256", "readout_recipe_sha256"]:
            sha256(slot[name])
        if (
            slot["pretraining_seed"] not in plan["pretraining_seeds"]
            and slot["model_kind"] not in ("external", "diagnostic")
        ) or slot["readout_seed"] not in plan["readout_seeds"]:
            raise ValueError("unplanned seed slot")
        design = tuple(
            str(slot[k]) for k in FACETS + ("condition", "pretraining_seed", "readout_seed")
        )
        if design in designs:
            raise ValueError("duplicate experimental cell")
        designs.add(design)
        if slot["expected"] is None:
            pending = destination(root, slot["predictions"])
            if (pending / "run.json").exists():
                raise ValueError("delivered predictions lack their declared expected inventory")
            reports[sid] = {
                "complete": False,
                "primary": None,
                "slot": slot,
                "reason": "fit/predictor inventory not delivered",
                "rows": [],
                "task_id": slot["task_id"],
                "horizon": slot["horizon"],
                "split": plan["split"],
                "expected_families": plan["families"],
            }
            slots[sid] = slot
            continue
        expected_path = bound_file(root, slot["expected"])
        expected = load_expected(expected_path, plan["split"])
        first = next(iter(expected.values()))
        if any(first[k] != slot[k] for k in ["task_id", "label_budget", "readout_seed"]):
            raise ValueError("slot does not match predictor identity")
        actual_horizons = {r["horizon_or_frame"] for r in expected.values()}
        if (
            slot["horizon"]
            != ("tracking" if slot["task_id"] == "tracking" else next(iter(actual_horizons)))
            or slot["task_id"] != "tracking"
            and len(actual_horizons) != 1
        ):
            raise ValueError("slot horizon mismatch")
        predictor = tuple(
            str(first[k])
            for k in ["run_id", "checkpoint_id", "task_id", "label_budget", "readout_seed"]
        )
        if predictor in identities:
            raise ValueError("same predictor counted as multiple slots")
        identities.add(predictor)
        report = score_directory(
            destination(root, slot["predictions"]),
            expected_path,
            labels,
            groups,
            split=plan["split"],
            families=plan["families"],
            classes=plan["classes"],
        )
        if plan["scope"] == "development" and report["provenance"]["state"] == "delivered":
            if "fit" not in slot:
                raise ValueError("real scoring slot requires the bound fit report")
            fit_path = bound_file(root, slot["fit"])
            metadata = file_json(destination(root, slot["predictions"]) / "run.json")
            validate_fit(slot, first, file_json(fit_path), metadata, digest(fit_path.read_bytes()))
        report["slot"] = slot
        reports[sid] = report
        slots[sid] = slot
    contrasts = {}
    for contrast in plan["contrasts"]:
        fields(contrast, set(FACETS) | {"contrast_id", "condition", "reference", "margin"})
        cid = text_id(contrast["contrast_id"], "contrast_id")
        if cid in contrasts or contrast["condition"] == contrast["reference"]:
            raise ValueError("duplicate/invalid contrast")
        number(contrast["margin"], "margin", 1e-12, 1)
        sides = []
        for condition in ["condition", "reference"]:
            selected = {}
            for sid, slot in slots.items():
                if slot["condition"] == contrast[condition] and all(
                    slot[k] == contrast[k] for k in FACETS
                ):
                    selected[slot["pretraining_seed"], slot["readout_seed"]] = reports[sid]
            sides.append(selected)
        result = paired_reports(
            *sides, plan["pretraining_seeds"], plan["readout_seeds"], contrast["margin"]
        )
        if result["complete"]:
            result["episode_group_sensitivity"] = paired_group_bootstrap(
                *sides, plan["pretraining_seeds"], plan["readout_seeds"], **plan["bootstrap"]
            )
            result["crossed_sensitivity"] = paired_group_bootstrap(
                *sides,
                plan["pretraining_seeds"],
                plan["readout_seeds"],
                crossed=True,
                **plan["bootstrap"],
            )
        contrasts[cid] = {**result, "design": contrast}
    complete = all(r["complete"] for r in reports.values()) and all(
        r["complete"] for r in contrasts.values()
    )
    available = {
        k: r["inference"]
        for k, r in contrasts.items()
        if r["complete"] and r["inference"]["inference_available"]
    }
    # No multiplicity decision on a selected subset of a declared contrast family.
    corrections = None
    if available and len(available) == len(contrasts):
        corrections = {
            "individual_equivalence_holm": holm({k: v["p_tost"] for k, v in available.items()}),
            "two_sided_superiority_holm": holm(
                {k: v["p_superiority_two_sided"] for k, v in available.items()}
            ),
        }
    after = source_binding()
    if before != after:
        raise ValueError("analysis source/runtime changed during scoring")
    report = {
        "schema_version": "bullet-time.analysis.v1",
        "scope": plan["scope"],
        "plan_sha256": digest(plan_path.read_bytes()),
        "execution": before,
        "complete": complete,
        "planned_slots": len(slots),
        "complete_slots": sum(r["complete"] for r in reports.values()),
        "slots": reports,
        "contrasts": contrasts,
        "multiple_individual_claims": corrections,
        "scientific_claim_pass": False,
        "interpretation": "operational development/synthetic report; no final freeze, global-null or H1-H4 claim",
    }
    output = Path(output)
    if output.exists():
        raise ValueError("analysis output already exists")
    atomic_json(output, report)
    return report
