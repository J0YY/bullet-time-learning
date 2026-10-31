"""Physics/lineage and raster-boundary checks; native capture is separate evidence."""

from collections import Counter
from copy import deepcopy

import numpy as np
import pytest
from PIL import Image

from bullet_time.generation.evaluation_motion import (
    forecast_candidate,
    tracking_candidate,
    reflect_steps,
    select_groups,
)
from bullet_time.generation.evaluation_bundle import (
    check_lineage,
    check_duplicates,
    diagonal,
    point_visible,
    ROOT,
    read,
)


def test_forward_collision_pairs_share_final_state_with_opposite_velocity():
    for index in range(24):
        request = forecast_candidate(71, index, "collision")
        histories = [np.array(b["history_positions"]) for b in request["branches"]]
        assert np.allclose(histories[0][-1], histories[1][-1], rtol=0, atol=1e-12)
        assert np.allclose(np.diff(histories[0], axis=0)[-1], -np.diff(histories[1], axis=0)[-1])
        assert [b["labels"]["0.5"] for b in request["branches"]] == [1, 0]
        target = np.array(next(o for o in request["objects"] if o["id"] == "target")["position"])
        radius = sum(o["radius"] for o in request["objects"] if o["kind"] == "sphere")
        for branch, probe in zip(request["branches"], request["probes"], strict=True):
            positions = np.array(probe["positions"])
            distances = np.linalg.norm(positions - target, axis=1)
            assert distances.min() == pytest.approx(radius, abs=1e-10)
            assert np.argmin(distances) == probe["expected_contact_tick"]
            assert branch["contacts"][0] == pytest.approx(probe["expected_contact_tick"] / 64)
            assert all(
                events == pytest.approx(branch["contacts"])
                for events in branch["refinement_contacts"]
            )


def test_order_uses_forward_circle_and_identical_image_bag():
    for index in range(16):
        request = forecast_candidate(23, index, "order")
        a, b = request["branches"]
        assert Counter(a["observed"]) == Counter(b["observed"])
        assert len(set(a["observed"])) == 16 and a["observed"][-1] == b["observed"][-1]
        assert [a["labels"]["0.5"], b["labels"]["0.5"]] == [1, 0]
        for branch, sign in [(a, 1), (b, -1)]:
            points = np.array(branch["history_positions"])[:, [0, 2]]
            angular = np.unwrap(np.arctan2(points[:, 1], points[:, 0]))
            assert np.diff(angular) == pytest.approx(np.full(60, sign * 2 * np.pi / 64))
            for i, key in enumerate(branch["observed"]):
                assert branch["history_positions"][i * 4] == request["frames"][key]["projectile"]


def test_collision_contact_refinement_and_post_contact_remainder():
    points, _, contacts = reflect_steps(-0.7, 2.3, 0.43, seconds=1)
    expected = (0.43 + 0.7) / 2.3
    assert contacts == pytest.approx([expected])
    assert points[-1] == pytest.approx(0.43 - 2.3 * (1 - expected))
    for hz in [128, 256]:
        fine, _, events = reflect_steps(-0.7, 2.3, 0.43, hz=hz, seconds=1)
        assert fine[:: hz // 64] == pytest.approx(points)
        assert events == pytest.approx(contacts)


def test_tracking_constant_motion_and_physical_clearance():
    for index in range(32):
        request = tracking_candidate(71, index)
        positions = np.array([r["projectile"] for r in request["frames"].values()])
        other = np.array([r["distractor"] for r in request["frames"].values()])
        assert np.diff(positions, n=2, axis=0) == pytest.approx(np.zeros((26, 3)))
        assert np.min(np.linalg.norm(positions - other, axis=1)) > 0.7
        assert request["tracking"]["minimum_physical_clearance"] > 0
        ref = request["tracking"]["reference_frame"]
        for current in request["tracking"]["primary_frames"]:
            assert current - 15 <= ref < current


def test_content_pools_and_prototypes_are_split_disjoint():
    plan = read(ROOT / "configs/generation/evaluation-development.json")
    requests = []
    for task in plan["tasks"]:
        for split, count in plan["groups_per_task"].items():
            rows, _ = select_groups(plan["seed"], split, count, task)
            requests.extend(rows)
    assert check_lineage(requests, plan) == dict(trajectory=72, asset=72, configuration=72)
    bad = deepcopy(requests)
    bad[0]["assigned_pools"]["asset"] = "dev"
    with pytest.raises(ValueError, match="another split"):
        check_lineage(bad, plan)
    bad = deepcopy(requests)
    bad[1]["prototypes"]["trajectory"] = bad[0]["prototypes"]["trajectory"]
    bad[1]["groups"]["trajectory"] = bad[0]["groups"]["trajectory"]
    with pytest.raises(ValueError, match="duplicate trajectory"):
        check_lineage(bad, plan)
    with pytest.raises(ValueError, match="train/dev"):
        select_groups(plan["seed"], "assessment", 1, "collision")


def test_raster_surface_visibility_and_full_box_diagonal():
    mask = np.zeros((224, 224, 3), dtype=np.uint8)
    mask[20:30, 40:50, 0] = 255
    assert point_visible(mask, [45 / 223, 25 / 223])
    assert not point_visible(mask, [40 / 223, 30 / 223])
    assert not point_visible(mask, [-1, 0.5])
    assert diagonal(mask) == pytest.approx(np.sqrt(200))
    with pytest.raises(ValueError, match="empty"):
        diagonal(np.zeros_like(mask))


@pytest.mark.parametrize(
    "difference,match", [(0, "exact duplicate"), (1, "near duplicate"), (50, None)]
)
def test_cross_split_raster_duplicate_admission(tmp_path, difference, match):
    plan = read(ROOT / "configs/generation/evaluation-development.json")
    requests = []
    for index, split in enumerate(["train", "dev"]):
        gid = f"group-{index}"
        requests.append(dict(group_id=gid, split=split, frames={"frame": {}}))
        pixels = np.full((224, 224, 3), 100, dtype=np.uint8)
        pixels[20:40, 20:40] = [180 + (difference if index else 0), 20, 20]
        mask = np.zeros_like(pixels)
        mask[20:40, 20:40, 0] = 255
        for path, array in [
            (tmp_path / "inputs/rgb" / gid / "frame.png", pixels),
            (tmp_path / "private" / gid / "masks/frame.png", mask),
        ]:
            path.parent.mkdir(parents=True)
            Image.fromarray(array).save(path)
    if match:
        with pytest.raises(ValueError, match=match):
            check_duplicates(tmp_path, requests, plan)
    else:
        assert check_duplicates(tmp_path, requests, plan)["near_duplicates"] == 0


@pytest.mark.parametrize("task", ["collision", "order", "tracking"])
def test_producer_exports_are_accepted_by_actual_consumer(tmp_path, task):
    """Synthetic pixels isolate the wire contract; native evidence is separate."""
    from bullet_time.generation.evaluation_bundle import exports, write_lines
    from bullet_time.evaluation.inputs import ImageStore, EvaluationInputs
    from bullet_time.evaluation.training import Targets
    from bullet_time.evaluation.subsets import Groups, verify_pairs
    from bullet_time.provenance import atomic_json, digest

    request = tracking_candidate(71, 0) if task == "tracking" else forecast_candidate(71, 0, task)
    request.update(group_id="synthetic-group", split="train")
    records = {
        k: dict(
            projected_centers=dict(projectile=[0.4, 0.5], target=[0.6, 0.5]),
            tracking=dict(surface_point=[0.5, 0.5]),
        )
        for k in request["frames"]
    }
    evidence = dict(
        visibility={str(t): t != 17 for t in [17, 25, 26, 27]},
        full_diagonal_pixels={str(t): 32 for t in [17, 25, 26, 27]},
    )
    inputs, labels, groups = exports(request, records, evidence)
    pixels = np.zeros((224, 224, 3), dtype=np.uint8)
    path = tmp_path / "fixture.png"
    Image.fromarray(pixels).save(path)
    images = [
        dict(
            image_id=f"synthetic-group/{key}",
            rgb_path="fixture.png",
            file_sha256=digest(path.read_bytes()),
            rgb_sha256=digest(pixels.tobytes()),
            height=224,
            width=224,
            channels=3,
        )
        for key in request["frames"]
    ]
    write_lines(tmp_path / "images.jsonl", images)
    write_lines(tmp_path / "inputs.jsonl", inputs)
    write_lines(tmp_path / "labels.jsonl", labels)
    atomic_json(
        tmp_path / "groups.json",
        dict(schema_version="bullet-time.evaluation-groups.v1", records=groups),
    )
    consumer = EvaluationInputs(tmp_path / "inputs.jsonl", ImageStore(tmp_path / "images.jsonl"))
    targets = Targets(tmp_path / "labels.jsonl", consumer)
    group_store = Groups(tmp_path / "groups.json")
    assert len(group_store.validate_inputs(consumer, task)) == 1
    if task != "tracking":
        assert verify_pairs(consumer, targets, group_store, task)["pairs"] == 1
    else:
        assert len({e.query_id for e in consumer.examples}) == 1
        assert len([e for e in consumer.examples if e.prediction_role == "primary"]) == 3


def test_raw_capture_reuse_preserves_bytes_and_rejects_changed_renderer(tmp_path):
    from bullet_time.generation.evaluation_bundle import reuse_capture_source
    from bullet_time.provenance import atomic_json, digest

    data = tmp_path / "raw.bin"
    data.write_bytes(b"synthetic capture bytes")
    atomic_json(tmp_path / "generation.json", {"source_commit": "synthetic fixture"})
    sources = {
        "game/evaluation_driver.gd": "a" * 64,
        "src/bullet_time/generation/evaluation_bundle.py": "b" * 64,
    }
    plan = {"scope": "synthetic"}
    pin = {"version": "synthetic"}
    old = dict(
        schema_version="bullet-time.measurement-bundle.v1",
        plan=plan,
        engine_pin=pin,
        development=False,
        producer_sources=sources,
        inventory={p.name: digest(p.read_bytes()) for p in tmp_path.iterdir()},
    )
    atomic_json(tmp_path / "bundle.json", old)
    current = {**sources, "src/bullet_time/generation/evaluation_bundle.py": "c" * 64}
    _, receipt = reuse_capture_source(tmp_path, plan, pin, current)
    assert receipt["producer_sources"] == sources
    with pytest.raises(ValueError, match="renderer/runtime"):
        reuse_capture_source(
            tmp_path, plan, pin, {**current, "game/evaluation_driver.gd": "d" * 64}
        )
    data.write_bytes(b"changed bytes")
    with pytest.raises(ValueError, match="bytes changed"):
        reuse_capture_source(tmp_path, plan, pin, current)
