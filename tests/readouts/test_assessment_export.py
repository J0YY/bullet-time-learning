import json
import re
import subprocess
import sys

import pytest
import torch
from PIL import Image, PngImagePlugin

from bullet_time.generation.assessment_export import prepare_assessment, verify_preparation
from bullet_time.evaluation.inputs import EvaluationInputs, ImageStore
from bullet_time.provenance import digest, atomic_json
from fixtures.consumer.evaluation import fixtures


def lines(path, rows):
    path.write_text("".join(json.dumps(r) + "\n" for r in rows))


def source_fixture(root):
    """Synthetic assessment example; no real development data is reclassified."""
    root.mkdir()
    path, store, base = fixtures(root / "inputs")
    # Preserve pixels but add an identifying text chunk that must not be copied.
    catalog = list(store.images.values())
    image_path = store.root / catalog[0]["rgb_path"]
    with Image.open(image_path) as image:
        pixels = image.copy()
    info = PngImagePlugin.PngInfo()
    info.add_text("source", "PRIVATE-RECONSTRUCTION-SEED")
    pixels.save(image_path, pnginfo=info)
    catalog[0]["file_sha256"] = digest(image_path.read_bytes())
    lines(store.path, catalog)
    rows, labels, groups = [], [], []
    for task in ("collision", "order"):
        for branch in (0, 1):
            eid = f"PRIVATE-{task}-branch-{branch}"
            images = base["observed_image_ids"]
            if branch == 1:
                images = images[:-1][::-1] + images[-1:]
            rows.append(
                dict(
                    base,
                    task_id=task,
                    episode_id=eid,
                    query_id="PRIVATE-query",
                    split="assessment",
                    observed_image_ids=images,
                )
            )
            labels.append(
                dict(
                    schema_version="bullet-time.labels.v1",
                    task_id=task,
                    episode_id=eid,
                    query_id="PRIVATE-query",
                    horizon_or_frame="0.5",
                    split="assessment",
                    target={"contact": branch},
                )
            )
            groups.append(
                dict(
                    task_id=task,
                    episode_id=eid,
                    group_id=f"PRIVATE-{task}-group",
                    split="assessment",
                )
            )
    for frame in (15, 16, 17):
        indices = list(range(frame - 15, frame + 1))
        rows.append(
            dict(
                schema_version="bullet-time.evaluation.v2",
                task_id="tracking",
                episode_id="PRIVATE-tracking",
                query_id="PRIVATE-query",
                split="assessment",
                observed_image_ids=[f"0/{i % 16}/0" for i in indices],
                observed_frame_indices=indices,
                query_points=[],
                prediction_frame=frame,
                reference_frame=2,
                reference_image_id="0/2/0",
                reference_point=[0.3, 0.4],
                prediction_role="primary",
            )
        )
        labels.append(
            dict(
                schema_version="bullet-time.labels.v1",
                task_id="tracking",
                episode_id="PRIVATE-tracking",
                query_id="PRIVATE-query",
                horizon_or_frame=str(frame),
                split="assessment",
                target={
                    "x": 0.4,
                    "y": 0.5,
                    "visible": 1,
                    "bbox_diagonal_pixels": 30.0,
                    "prediction_role": "primary",
                },
            )
        )
    groups.append(
        dict(
            task_id="tracking",
            episode_id="PRIVATE-tracking",
            group_id="PRIVATE-track-group",
            split="assessment",
        )
    )
    lines(root / "inputs/evaluation.jsonl", rows)
    (root / "private").mkdir()
    lines(root / "private/labels.jsonl", labels)
    atomic_json(
        root / "groups.json",
        {"schema_version": "bullet-time.evaluation-groups.v1", "records": groups},
    )
    return rows, labels, groups


def test_opaque_export_preserves_all_model_inputs_and_pairs_without_source_metadata(tmp_path):
    source, output = tmp_path / "source", tmp_path / "prepared"
    source_fixture(source)
    report = prepare_assessment(source, output)
    assert verify_preparation(output) == report
    result = report["result"]
    assert [result[k] for k in ("episodes", "examples", "images", "groups")] == [5, 7, 16, 3]
    assert not result["assessment_release_authorized"] and not result["scientific_gate_pass"]
    for task in ("collision", "order"):
        assert result["task_checks"][task]["pairs"] == 1
    before = EvaluationInputs(
        source / "inputs/evaluation.jsonl",
        ImageStore(source / "inputs/images.jsonl"),
        allowed_splits=("assessment",),
    )
    after = EvaluationInputs(
        output / "public/evaluation.jsonl",
        ImageStore(output / "public/images.jsonl"),
        allowed_splits=("assessment",),
    )
    private = json.loads((output / "private/provenance.json").read_text())
    queries = {(r["task_id"], r["source"]): r["opaque"] for r in private["query_ids"]}
    exported = {(e.task_id, *e.key): e for e in after.examples}
    for e in before.examples:
        key = (
            e.task_id,
            private["episode_ids"][e.episode_id],
            queries[e.task_id, e.query_id],
            e.key[-1],
        )
        counterpart = exported[key]
        for mode in (
            ("sequence", "current_frame")
            if e.task_id == "tracking"
            else ("sequence", "final_frame", "bag")
        ):
            left, right = (
                before.assemble(e, size=32, mode=mode),
                after.assemble(counterpart, size=32, mode=mode),
            )
            for field in left:
                assert (
                    right[field] is None
                    if left[field] is None
                    else torch.equal(left[field], right[field])
                )
    for path in (output / "public").rglob("*"):
        if path.is_file():
            assert b"PRIVATE-" not in path.read_bytes()
    for row in after.store.images.values():
        assert re.fullmatch(r"[0-9a-f]{64}", row["image_id"])
        assert Image.open(output / "public" / row["rgb_path"]).info == {}
    labels = [json.loads(l) for l in (output / "private/labels.jsonl").read_text().splitlines()]
    public_text = b"".join(p.read_bytes() for p in (output / "public").glob("*.json*"))
    assert all(r["commitment_nonce"].encode() not in public_text for r in labels)
    assert (output / "private/labels.jsonl").stat().st_mode & 0o777 == 0o600
    with pytest.raises(ValueError, match="new output"):
        prepare_assessment(source, output)


def test_export_randomization_and_order_do_not_retain_branch_correspondence(tmp_path):
    source = tmp_path / "source"
    source_fixture(source)
    prepare_assessment(source, tmp_path / "one")
    prepare_assessment(source, tmp_path / "two")
    first = json.loads((tmp_path / "one/private/provenance.json").read_text())
    second = json.loads((tmp_path / "two/private/provenance.json").read_text())
    for namespace in ("episode_ids", "image_ids", "group_ids"):
        assert not set(first[namespace].values()) & set(second[namespace].values())
    rows = [
        json.loads(l) for l in (tmp_path / "one/public/evaluation.jsonl").read_text().splitlines()
    ]
    assert [r["episode_id"] for r in rows] == sorted(r["episode_id"] for r in rows)


@pytest.mark.parametrize(
    "mutation",
    [
        "train",
        "missing_label",
        "extra_label",
        "unpaired",
        "extra_group",
        "bad_pixels",
        "side_information",
    ],
)
def test_bad_private_inputs_never_receive_a_complete_receipt(tmp_path, mutation):
    source, output = tmp_path / "source", tmp_path / "prepared"
    rows, labels, groups = source_fixture(source)
    if mutation == "train":
        rows[0]["split"] = "train"
    elif mutation == "missing_label":
        labels.pop()
    elif mutation == "extra_label":
        labels.append(dict(labels[0], episode_id="PRIVATE-other"))
    elif mutation == "unpaired":
        groups[0]["group_id"] = "PRIVATE-wrong-group"
    elif mutation == "extra_group":
        groups.append(dict(groups[0], episode_id="PRIVATE-other"))
    elif mutation == "side_information":
        rows[0]["query_points"] = [[0.2, 0.4], [0.5, 0.6]]
    else:
        store = ImageStore(source / "inputs/images.jsonl")
        (store.root / store.images["0/0/0"]["rgb_path"]).write_bytes(b"not the image")
    lines(source / "inputs/evaluation.jsonl", rows)
    lines(source / "private/labels.jsonl", labels)
    atomic_json(
        source / "groups.json",
        {"schema_version": "bullet-time.evaluation-groups.v1", "records": groups},
    )
    with pytest.raises(ValueError):
        prepare_assessment(source, output)
    assert not (output / "public/preparation.json").exists()


def test_cli_verification_detects_public_and_private_mutation(tmp_path):
    source, output = tmp_path / "source", tmp_path / "prepared"
    source_fixture(source)
    subprocess.run(
        [
            sys.executable,
            "scripts/data/prepare_assessment.py",
            "--private-source",
            str(source),
            "--output",
            str(output),
        ],
        check=True,
        capture_output=True,
    )
    subprocess.run(
        [
            sys.executable,
            "scripts/data/prepare_assessment.py",
            "--verify-only",
            "--output",
            str(output),
        ],
        check=True,
        capture_output=True,
    )
    for name in ("public/evaluation.jsonl", "private/provenance.json"):
        path = output / name
        before = path.read_bytes()
        path.write_bytes(before + b"\n")
        with pytest.raises(ValueError, match="hash differs"):
            verify_preparation(output)
        path.write_bytes(before)
    (output / "public/unexpected-state.json").write_text("{}")
    with pytest.raises(ValueError, match="inventory differs"):
        verify_preparation(output)
