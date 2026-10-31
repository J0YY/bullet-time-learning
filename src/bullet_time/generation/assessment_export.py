"""Prepare opaque assessment inputs without opening an assessment release.

Run only in the producer's private environment. No public seed reconstructs these
IDs or commitments. Physical/lineage admission and protocol locking are separate.
"""

from pathlib import Path
import re
import secrets

from PIL import Image
import PIL

from bullet_time.provenance import atomic_json, canonical_bytes, digest, inside, strict_json
from bullet_time.evaluation.inputs import EvaluationInputs, ImageStore
from bullet_time.evaluation.label_contract import seal_assessment_labels
from bullet_time.evaluation.subsets import Groups, verify_pairs
from bullet_time.evaluation.training import Targets


def read_lines(path):
    return [strict_json(line) for line in Path(path).read_bytes().splitlines()]


def write_lines(path, rows):
    path.write_bytes(b"".join(canonical_bytes(row) + b"\n" for row in rows))


def source_binding():
    here = Path(__file__).resolve().parents[1]
    paths = (
        [Path(__file__).resolve()]
        + [
            here / "evaluation" / name
            for name in (
                "inputs.py",
                "label_contract.py",
                "scoring.py",
                "subsets.py",
                "training.py",
            )
        ]
        + [here / "provenance.py", here / "loading/batch.py"]
    )
    return {
        "sources": {str(p.relative_to(here)): digest(p.read_bytes()) for p in paths},
        "pillow": PIL.__version__,
    }


def new_ids(keys):
    """Independent 256-bit names; never use a public seeded RNG or target value."""
    result, used = {}, set()
    for key in sorted(set(keys)):
        value = secrets.token_hex(32)
        if value in used:
            raise ValueError("opaque ID collision; retain failed preparation")
        used.add(value)
        result[key] = value
    return result


def row_order(row):
    return (
        row["episode_id"],
        row.get("query_id", ""),
        str(
            row.get("horizon_or_frame", row.get("prediction_frame", row.get("horizon_seconds", "")))
        ),
    )


def validate_export(root):
    """Consumer validation only; no metric calculation or release authority."""
    store = ImageStore(root / "public/images.jsonl")
    inputs = EvaluationInputs(
        root / "public/evaluation.jsonl", store, allowed_splits=("assessment",)
    )
    used_images = {i for e in inputs.examples for i in e.observed_image_ids}
    if used_images != set(store.images):
        raise ValueError("public catalog must contain exactly the permitted input images")
    targets = Targets(root / "private/labels.jsonl", inputs, allowed_splits=("assessment",))
    groups = Groups(root / "public/groups.json")
    episodes = {(e.task_id, e.episode_id) for e in inputs.examples}
    if set(groups.records) != episodes:
        raise ValueError("group inventory differs from assessment input episodes")
    identifiers = list(store.images)
    identifiers.extend(e.episode_id for e in inputs.examples)
    identifiers.extend(e.query_id for e in inputs.examples)
    identifiers.extend(r["group_id"] for r in groups.records.values())
    if any(not re.fullmatch(r"[0-9a-f]{64}", value) for value in identifiers):
        raise ValueError("public source identifiers must be opaque")
    for image_id, row in store.images.items():
        if row["rgb_path"] != f"rgb/{image_id}.png":
            raise ValueError("public RGB filename must be opaque")
        store.read(image_id)
    tasks = {e.task_id for e in inputs.examples}
    if not tasks <= {"collision", "order", "tracking"}:
        raise ValueError("assessment preparation is game-only")
    checks = {}
    for task in sorted(tasks):
        checks[task] = (
            {"episodes": len(groups.validate_inputs(inputs, task))}
            if task == "tracking"
            else verify_pairs(inputs, targets, groups, task)
        )
    commitments = strict_json((root / "public/target-commitments.json").read_bytes())
    expected = [
        {
            **{
                k: row[k]
                for k in ("task_id", "episode_id", "query_id", "horizon_or_frame", "split")
            },
            "target_reference_sha256": digest(canonical_bytes(row)),
        }
        for row in sorted(targets.rows.values(), key=row_order)
    ]
    if commitments != expected:
        raise ValueError("public commitments differ from private labels")
    return {
        "episodes": len(episodes),
        "examples": len(inputs.examples),
        "images": len(store.images),
        "groups": len({row["group_id"] for row in groups.records.values()}),
        "task_checks": checks,
        "scientific_gate_pass": False,
        "assessment_release_authorized": False,
    }


def verify_preparation(root):
    root = Path(root).resolve(strict=True)
    public, private = root / "public", root / "private"
    receipt = strict_json((public / "preparation.json").read_bytes())
    if receipt["schema_version"] != "bullet-time.opaque-assessment-preparation.v1":
        raise ValueError("unsupported assessment preparation")
    for folder, inventory, excluded in (
        (public, receipt["public_inventory"], "preparation.json"),
        (private, strict_json((private / "inventory.json").read_bytes()), "inventory.json"),
    ):
        actual = {
            str(p.relative_to(folder))
            for p in folder.rglob("*")
            if p.is_file() and p != folder / excluded
        }
        if actual != set(inventory):
            raise ValueError("preparation inventory differs")
        for name, expected in inventory.items():
            if digest(inside(folder, name).read_bytes()) != expected:
                raise ValueError("preparation artifact hash differs")
    result = validate_export(root)
    if receipt["result"] != result:
        raise ValueError("preparation result differs")
    return receipt


def prepare_assessment(source, output):
    """Convert a private assessment-only export; never relabel train/dev as assessment.

    Source layout: inputs/{images,evaluation}.jsonl, private/labels.jsonl and
    groups.json. Output separates opaque public inputs from labels/ID provenance.
    A complete receipt appears only after target, pair and actual-pixel checks.
    """
    source, output = Path(source).resolve(strict=True), Path(output).resolve()
    if output.exists() or output.is_relative_to(source) or source.is_relative_to(output):
        raise ValueError("new output outside the private source tree required")
    paths = {
        name: inside(source, name)
        for name in (
            "inputs/images.jsonl",
            "inputs/evaluation.jsonl",
            "private/labels.jsonl",
            "groups.json",
        )
    }
    before = {name: digest(path.read_bytes()) for name, path in paths.items()}
    code = source_binding()
    store = ImageStore(paths["inputs/images.jsonl"])
    inputs = EvaluationInputs(
        paths["inputs/evaluation.jsonl"], store, allowed_splits=("assessment",)
    )
    if any(e.task_id == "ssv2" for e in inputs.examples):
        raise ValueError("assessment preparation is game-only")
    groups = Groups(paths["groups.json"])
    if set(groups.records) != {(e.task_id, e.episode_id) for e in inputs.examples}:
        raise ValueError("group inventory differs from assessment input episodes")
    for task in {e.task_id for e in inputs.examples}:
        groups.validate_inputs(inputs, task)
    rows = read_lines(paths["inputs/evaluation.jsonl"])
    labels = read_lines(paths["private/labels.jsonl"])
    # The source labels must already be assessment; sealing validates every target.
    sealed, _ = seal_assessment_labels(labels)
    episode_ids = new_ids(e.episode_id for e in inputs.examples)
    query_ids = new_ids((e.task_id, e.query_id) for e in inputs.examples)
    group_ids = new_ids(r["group_id"] for r in groups.records.values())
    used_images = {i for e in inputs.examples for i in e.observed_image_ids}
    used_images.update(
        e.reference_image_id for e in inputs.examples if e.reference_image_id is not None
    )
    image_ids = new_ids(used_images)
    output.mkdir(mode=0o700, parents=True)
    for folder in ("public/rgb", "private"):
        (output / folder).mkdir(parents=True, mode=0o700)
    public, private = output / "public", output / "private"
    catalog = []
    for old, new in sorted(image_ids.items(), key=lambda item: item[1]):
        rgb = store.read(old)
        path = public / "rgb" / f"{new}.png"
        # Strip arbitrary PNG text/source metadata without changing decoded RGB.
        Image.fromarray(rgb).save(path, format="PNG")
        catalog.append(
            dict(
                store.images[old],
                image_id=new,
                rgb_path=f"rgb/{new}.png",
                file_sha256=digest(path.read_bytes()),
            )
        )
    write_lines(public / "images.jsonl", catalog)
    exported = []
    for row in rows:
        r = dict(
            row,
            episode_id=episode_ids[row["episode_id"]],
            query_id=query_ids[row["task_id"], row["query_id"]],
        )
        r["observed_image_ids"] = [image_ids[i] for i in row["observed_image_ids"]]
        if row["task_id"] == "tracking":
            r["reference_image_id"] = image_ids[row["reference_image_id"]]
        exported.append(r)
    write_lines(public / "evaluation.jsonl", sorted(exported, key=row_order))
    grouped = [
        dict(r, episode_id=episode_ids[r["episode_id"]], group_id=group_ids[r["group_id"]])
        for r in groups.records.values()
    ]
    atomic_json(
        public / "groups.json",
        {
            "schema_version": "bullet-time.evaluation-groups.v1",
            "records": sorted(grouped, key=row_order),
        },
    )
    renamed = []
    for row in sealed:
        # Missing/extraneous labels fail here or in the exact Targets join below.
        if (
            row["episode_id"] not in episode_ids
            or (row["task_id"], row["query_id"]) not in query_ids
        ):
            raise ValueError("unmatched assessment label")
        renamed.append(
            dict(
                row,
                episode_id=episode_ids[row["episode_id"]],
                query_id=query_ids[row["task_id"], row["query_id"]],
            )
        )
    renamed.sort(key=row_order)
    write_lines(private / "labels.jsonl", renamed)
    (private / "labels.jsonl").chmod(0o600)
    commitments = [
        {
            **{k: r[k] for k in ("task_id", "episode_id", "query_id", "horizon_or_frame", "split")},
            "target_reference_sha256": digest(canonical_bytes(r)),
        }
        for r in renamed
    ]
    atomic_json(public / "target-commitments.json", commitments)
    atomic_json(
        private / "provenance.json",
        {
            "source_files_sha256": before,
            "episode_ids": episode_ids,
            "query_ids": [
                {"task_id": k[0], "source": k[1], "opaque": v} for k, v in query_ids.items()
            ],
            "group_ids": group_ids,
            "image_ids": image_ids,
            "source_image_files_sha256": {
                old: store.images[old]["file_sha256"] for old in used_images
            },
        },
    )
    result = validate_export(output)
    if (
        before != {name: digest(path.read_bytes()) for name, path in paths.items()}
        or code != source_binding()
    ):
        raise ValueError("source/code changed during preparation; retain rejected output")
    receipt = {
        "schema_version": "bullet-time.opaque-assessment-preparation.v1",
        "scope": "input identity/target preparation only; not physical/lineage admission, protocol lock or release",
        "execution": code,
        "result": result,
        "public_inventory": {
            str(p.relative_to(public)): digest(p.read_bytes())
            for p in sorted(public.rglob("*"))
            if p.is_file()
        },
    }
    atomic_json(public / "preparation.json", receipt)
    atomic_json(
        private / "inventory.json",
        {p.name: digest(p.read_bytes()) for p in sorted(private.iterdir()) if p.is_file()},
    )
    return receipt
