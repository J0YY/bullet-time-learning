"""Compile primary game-assessment inventories using public opaque metadata only."""

from collections import Counter
from pathlib import Path
import re

from bullet_time.provenance import digest, fields, identity, inside, sha256, strict_json
from .assessment_contract import expected_input_identity, verifier_binding
from .assessment_policy import TASKS, stage_inventory
from .inputs import EvaluationInputs, ImageStore
from .subsets import Groups

METADATA = {"evaluation.jsonl", "images.jsonl", "groups.json", "target-commitments.json"}


def _public_bytes(public):
    if public.is_symlink() or any(p.is_symlink() for p in public.rglob("*")):
        raise ValueError("public assessment cannot contain symlinks")
    receipt_path = public / "preparation.json"
    receipt = strict_json(receipt_path.read_bytes())
    if receipt["schema_version"] != "bullet-time.opaque-assessment-preparation.v1":
        raise ValueError("unsupported opaque preparation")
    inventory = receipt["public_inventory"]
    if not METADATA <= inventory.keys() or any(
        name not in METADATA and not re.fullmatch(r"rgb/[0-9a-f]{64}\.png", name)
        for name in inventory
    ):
        raise ValueError("public inventory contains unexpected/private filenames")
    actual = {p.relative_to(public).as_posix() for p in public.rglob("*") if p.is_file()}
    if actual != set(inventory) | {"preparation.json"}:
        raise ValueError("public file inventory differs")
    hashes = {name: digest(inside(public, name).read_bytes()) for name in inventory}
    if hashes != inventory:
        raise ValueError("public artifact bytes changed")
    return {**hashes, "preparation.json": digest(receipt_path.read_bytes())}


def _execution():
    return {
        "compiler_sha256": digest(Path(__file__).read_bytes()),
        "verifier": verifier_binding(),
        "policy_inventory_sha256": stage_inventory()["inventory_sha256"],
    }


def compile_inputs(public, *, allow_partial=False):
    """No label/private/source-map reads; counts alone never establish admission.

    Primary half-second classification heads use all episodes, while tracking
    retains every declared primary/auxiliary query. Public commitments must join
    every source example, including non-primary classification horizons.
    """
    public = Path(public)
    if public.is_symlink():
        raise ValueError("public root cannot be a symlink")
    public = public.resolve(strict=True)
    execution = _execution()
    before = _public_bytes(public)
    store = ImageStore(public / "images.jsonl")
    inputs = EvaluationInputs(public / "evaluation.jsonl", store, allowed_splits=("assessment",))
    if {e.task_id for e in inputs.examples} != set(TASKS):
        raise ValueError("all three game tasks required")
    groups = Groups(public / "groups.json")
    if set(groups.records) != {(e.task_id, e.episode_id) for e in inputs.examples}:
        raise ValueError("group inventory differs from complete assessment input")
    ids = [e.episode_id for e in inputs.examples] + [e.query_id for e in inputs.examples]
    ids += [r["group_id"] for r in groups.records.values()] + list(store.images)
    if any(not re.fullmatch(r"[0-9a-f]{64}", name) for name in ids):
        raise ValueError("assessment identifiers must be opaque")
    used = {image for e in inputs.examples for image in e.observed_image_ids}
    used.update(e.reference_image_id for e in inputs.examples if e.reference_image_id is not None)
    if used != set(store.images):
        raise ValueError("RGB catalog must contain exactly permitted inputs")
    for image, record in store.images.items():
        if record["rgb_path"] != f"rgb/{image}.png":
            raise ValueError("RGB filename must be opaque")
        store.read(image)  # verifies encoded and decoded RGB hashes, never labels
    if {f"rgb/{image}.png" for image in store.images} != set(before) - METADATA - {
        "preparation.json"
    }:
        raise ValueError("public PNG inventory differs from RGB catalog")
    commitments = {}
    rows = strict_json((public / "target-commitments.json").read_bytes())
    for row in rows:
        fields(
            row,
            {
                "task_id",
                "episode_id",
                "query_id",
                "horizon_or_frame",
                "split",
                "target_reference_sha256",
            },
        )
        key = row["task_id"], row["episode_id"], row["query_id"], row["horizon_or_frame"]
        if key in commitments or row["split"] != "assessment":
            raise ValueError("duplicate/inaccessible target commitment")
        commitments[key] = sha256(row["target_reference_sha256"])
    if set(commitments) != {(e.task_id, *e.key) for e in inputs.examples}:
        raise ValueError("target commitments differ from all declared inputs")
    templates, counts = {}, {}
    for task in TASKS:
        grouped = groups.validate_inputs(inputs, task)
        selected = [
            e
            for e in inputs.examples
            if e.task_id == task and (task == "tracking" or e.horizon_seconds == 0.5)
        ]
        expected_episodes = {
            r["episode_id"] for r in groups.records.values() if r["task_id"] == task
        }
        if {e.episode_id for e in selected} != expected_episodes:
            raise ValueError("primary task inventory omits a declared episode")
        if task != "tracking" and len(selected) != len(expected_episodes):
            raise ValueError("one primary classification query per episode required")
        if task == "tracking":
            frames = {
                eid: sorted(
                    e.prediction_frame
                    for e in selected
                    if e.episode_id == eid and e.prediction_role == "primary"
                )
                for eid in expected_episodes
            }
            if any(len(f) != 3 or f != list(range(f[0], f[0] + 3)) for f in frames.values()):
                raise ValueError("tracking requires three consecutive primary queries per episode")
        templates[task] = [
            {
                "task_id": task,
                "episode_or_video_id": e.episode_id,
                "query_id": e.query_id,
                "horizon_or_frame": e.key[2],
                "split": "assessment",
                "scene_family": "projectile_arena",
                "pair_group_id": groups.records[task, e.episode_id]["group_id"],
                "target_reference_sha256": commitments[task, *e.key],
                "prediction_role": e.prediction_role,
            }
            for e in sorted(selected, key=lambda e: e.key)
        ]
        counts[task] = {
            "episodes": len(expected_episodes),
            "groups": len(grouped),
            "queries": len(selected),
            "roles": dict(Counter(e.prediction_role for e in selected)),
        }
    pilot_counts = all(
        counts[t]["episodes"] == 400 and counts[t]["groups"] == (400 if t == "tracking" else 200)
        for t in TASKS
    )
    if not pilot_counts and not allow_partial:
        raise ValueError(
            "complete pilot needs 400 episodes per task; partial inventories are diagnostics only"
        )
    if before != _public_bytes(public) or execution != _execution():
        raise ValueError("public inputs or compiler changed during inventory compilation")
    return {
        "schema_version": "bullet-time.assessment-input-inventory.v1",
        "execution": execution,
        "public_files": before,
        "public_inventory_sha256": identity(before),
        "templates": templates,
        "counts": counts,
        "pilot_counts_complete": pilot_counts,
        "expected_inputs_sha256": {
            task: expected_input_identity(rows) for task, rows in templates.items()
        },
        "assessment_authorized": False,
        "scientific_gate_pass": False,
        "limits": [
            "Public prepared identity is not proof of a fresh underlying source pool",
            "Projectile-arena family is the pilot declaration; source admission must verify it",
            "No physical/lineage/label correctness, model execution, isolation or release admission",
        ],
    }
