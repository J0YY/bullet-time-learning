"""Immutable train/dev measurement drops and producer/consumer admission."""

from collections import Counter
from functools import lru_cache
from pathlib import Path
import math
import platform
import shutil
import subprocess

import numpy as np

from bullet_time.provenance import (
    atomic_json,
    canonical_bytes,
    digest,
    identity,
    inside,
    number,
    sha256,
    strict_json,
)
from .bundle import ROOT, read, rgb, sha, same_request, verify_engine, invoke
from .evaluation_motion import select_groups, select_collection
from .evaluation_selection import (
    counts_from_pilot,
    read_pilot,
    selection_sources,
    selection_runtime,
    check_collection,
    verify_selection,
)


def source_files():
    paths = [
        "game/project.godot",
        "game/arena_driver.gd",
        "game/evaluation_driver.gd",
        "game/LICENSE",
        "src/bullet_time/generation/arena.py",
        "src/bullet_time/generation/bundle.py",
        "src/bullet_time/generation/evaluation_motion.py",
        "src/bullet_time/generation/evaluation_bundle.py",
        "src/bullet_time/generation/evaluation_selection.py",
        "src/bullet_time/provenance.py",
        "scripts/data/build_evaluation.py",
        "configs/generation/evaluation-development.json",
        "configs/pilot-plan.json",
        "configs/rendering/godot-macos.json",
    ]
    return {p: sha(ROOT / p) for p in paths}


def check_plan(plan):
    expected = read(ROOT / "configs/generation/evaluation-development.json")
    if plan.get("schema_version") == "bullet-time.measurement-plan.v2":
        expected = progressive_plan(plan["selection_sha256"], plan["per_stratum"])
    if plan != expected:
        raise ValueError("this version accepts only the checked-in bounded development plan")


def progressive_plan(selection_sha256, per_stratum):
    """Fixed 1 → 8 → full prefixes of the already declared full selection."""
    sha256(selection_sha256)
    if type(per_stratum) is not int or per_stratum not in (1, 8, 600):
        raise ValueError("progressive per-stratum capture must be 1, 8 or 600 (full)")
    pilot = read_pilot()
    if (
        pilot["family"] != "projectile_arena"
        or pilot["physics_hz"] != 64
        or pilot["evaluation_hz"] != 16
        or pilot["observed_frames"] != 16
        or pilot["rgb_shape"] != [224, 224, 3]
        or pilot["forecast_horizon_seconds"] != [0.25, 0.5, 1.0]
    ):
        raise ValueError("pilot geometry/cadence differs from implemented measurement producer")
    counts = counts_from_pilot(pilot)
    if max(n for row in counts.values() for n in row.values()) > 600:
        raise ValueError("pilot counts exceed this bounded progressive implementation")
    plan = read(ROOT / "configs/generation/evaluation-development.json")
    plan.update(
        schema_version="bullet-time.measurement-plan.v2",
        seed=pilot["data_seed"],
        groups_per_task={
            task: {split: min(n, per_stratum) for split, n in row.items()}
            for task, row in counts.items()
        },
        selection_sha256=selection_sha256,
        per_stratum=per_stratum,
        scope="progressive full-selection train/dev capture; no assessment or H3 acceptance",
    )
    return plan


def plan_counts(plan):
    if plan["schema_version"] == "bullet-time.measurement-plan.v1":
        return {task: dict(plan["groups_per_task"]) for task in plan["tasks"]}
    return plan["groups_per_task"]


def select_for_capture(plan, *, full_requests=None, full_selection=None):
    if plan["schema_version"] == "bullet-time.measurement-plan.v1":
        requests, evidence = [], {}
        for task in plan["tasks"]:
            for split in ("train", "dev"):
                rows, stats = select_groups(
                    plan["seed"], split, plan["groups_per_task"][split], task
                )
                requests.extend(rows)
                evidence[f"{task}/{split}"] = stats
        return requests, evidence, None
    if full_requests is None:
        full_requests, full_selection = select_collection(
            plan["seed"], counts_from_pilot(read_pilot())
        )
    selected, counts = [], Counter()
    for request in full_requests:
        task, split = request["task"], request["split"]
        if counts[task, split] < plan["groups_per_task"][task][split]:
            selected.append(request)
            counts[task, split] += 1
    check_collection(selected, plan["groups_per_task"])
    return selected, full_selection, full_requests


def validate_selection_copy(root, plan, full_requests, selection):
    path = root / "selection.json"
    if sha(path) != plan["selection_sha256"]:
        raise ValueError("progressive selection receipt differs")
    report = read(path)
    expected_counts = counts_from_pilot(read_pilot())
    if (
        report["schema_version"] != "bullet-time.measurement-selection.v1"
        or report["scope"]
        != "prospective train/dev selection only; no rendering, assessment or learning"
        or report["source_sha256"] != selection_sources()
        or report["runtime"] != selection_runtime()
        or report["data_seed"] != plan["seed"]
        or report["groups_per_task"] != expected_counts
        or report["selection"] != selection
        or report["summary"] != check_collection(full_requests, expected_counts)
        or report["inventory"]
        != {
            "private/requests.jsonl": digest(
                b"".join(canonical_bytes(r) + b"\n" for r in full_requests)
            )
        }
    ):
        raise ValueError("progressive source selection does not reconstruct")


def image_catalog(input_root, request):
    """Catalog order is independent of request dictionary serialization."""
    rows = []
    gid = request["group_id"]
    for key in sorted(request["frames"]):
        path = input_root / "rgb" / gid / (key + ".png")
        rows.append(
            dict(
                image_id=f"{gid}/{key}",
                rgb_path=path.relative_to(input_root).as_posix(),
                file_sha256=sha(path),
                rgb_sha256=digest(rgb(path).tobytes()),
                height=224,
                width=224,
                channels=3,
            )
        )
    return rows


def foreground(mask, channel=0):
    return (mask[:, :, channel] > 200) & (mask[:, :, (channel + 1) % 3] < 20)


def point_visible(mask, point):
    x, y = np.rint(np.asarray(point) * 223).astype(int)
    return bool(0 <= x < 224 and 0 <= y < 224 and foreground(mask)[y, x])


def diagonal(mask):
    y, x = np.nonzero(foreground(mask))
    if not len(x):
        raise ValueError("empty isolated silhouette")
    # Inclusive pixel coverage gives the full raster bounding box, not visible fragment.
    return math.hypot(int(x.max() - x.min() + 1), int(y.max() - y.min() + 1))


def validate_capture(root, request, plan, pin, *, rgb_root=None):
    """Check raw render/geometry evidence before constructing label/input exports."""
    root = Path(root)
    rgb_root = Path(rgb_root) if rgb_root is not None else root / "rgb"
    report = read(root / "render.json")
    if not same_request(report["request"], request):
        raise ValueError("captured request mismatch")
    version = report["engine_version"]
    actual_version = f"{version['major']}.{version['minor']}.{version['patch']}.{version['status']}.{version['build']}.{version['hash'][:9]}"
    if (
        actual_version != pin["version"]
        or report["renderer"] != pin["renderer"]
        or report["display"] == "headless"
        or report["temporal_effects"] is not False
    ):
        raise ValueError("unadmitted renderer")
    records = {r["key"]: r for r in report["records"]}
    if len(records) != len(report["records"]) or records.keys() != request["frames"].keys():
        raise ValueError("incomplete/duplicate capture inventory")
    for record in records.values():
        if record["before_state_sha256"] != record["after_state_sha256"]:
            raise ValueError("capture advanced visual state")
        state = record["visual_state"]
        if state.keys() != {o["id"] for o in request["objects"]}:
            raise ValueError("captured object inventory differs")
        for obj in request["objects"]:
            position = request["frames"][record["key"]].get(obj["id"], obj["position"])
            expected_transform = [*np.eye(3).tolist(), position]
            if not np.allclose(state[obj["id"]], expected_transform, rtol=0, atol=2e-6):
                raise ValueError("captured visual transform differs from saved state")
    camera = request["camera"]
    z = np.subtract(camera["position"], camera["look_at"], dtype=float)
    z /= np.linalg.norm(z)
    x = np.cross(camera["up"], z)
    x /= np.linalg.norm(x)
    if not np.allclose(
        report["camera_transform"], [x, np.cross(z, x), z, camera["position"]], rtol=0, atol=2e-6
    ):
        raise ValueError("captured camera differs from declared camera")
    if len(report["repeats"]) != 2 or not all(r["identical"] is True for r in report["repeats"]):
        raise ValueError("missing/failed repeat captures")
    for folder in (rgb_root, root / "masks"):
        if {p.name for p in folder.iterdir()} != {k + ".png" for k in records}:
            raise ValueError("unplanned/missing frame file")
    pixels = {key: rgb(rgb_root / (key + ".png")) for key in records}
    for repeat in report["repeats"]:
        if not np.array_equal(
            rgb(root / "repeat" / (repeat["key"] + ".png")), pixels[repeat["key"]]
        ):
            raise ValueError("repeated capture bytes differ")
    masks = {key: rgb(root / "masks" / (key + ".png")) for key in records}
    evidence = dict(
        frame_count=len(records),
        repeated_frames=2,
        frozen_states=True,
        renderer={k: report[k] for k in ("renderer", "display", "video_adapter")},
    )
    if request["task"] in ("collision", "order"):
        if len(report["contact_probes"]) != 2:
            raise ValueError("missing independent contact probes")
        for probe, observed in zip(request["probes"], report["contact_probes"], strict=True):
            if probe["branch"] != observed["branch"]:
                raise ValueError("probe branch mismatch")
            hits = observed["hits"]
            expected = probe["expected_contact_tick"]
            if expected is None:
                if hits:
                    raise ValueError("Godot found an unexpected contact")
            elif len(hits) != 1 or abs(hits[0]["step"] - expected) > 1:
                raise ValueError("Godot and analytic contact times disagree")
            offset = probe.get("tick_offset", 0)
            for horizon in (16, 32, 64):
                actual = int(any(60 < h["step"] + offset <= 60 + horizon for h in hits))
                if actual != request["branches"][probe["branch"]]["labels"][str(horizon / 64)]:
                    raise ValueError("Godot and forecast labels disagree")
        finals = [b["observed"][-1] for b in request["branches"]]
        if not np.array_equal(pixels[finals[0]], pixels[finals[1]]):
            raise ValueError("counterfactual final RGB differs")
        final = records[finals[0]]["projected_centers"]
        for oid, channel in (("projectile", 0), ("target", 1)):
            if foreground(masks[finals[0]], channel).sum() < plan["minimum_final_object_pixels"]:
                raise ValueError("insufficient visible query object")
            if not all(0 <= v <= 1 for v in final[oid]):
                raise ValueError("final query point outside image")
        if request["task"] == "order":
            bags = [
                Counter(digest(pixels[k].tobytes()) for k in b["observed"])
                for b in request["branches"]
            ]
            if bags[0] != bags[1]:
                raise ValueError("same-bag diagnostic multisets differ")
        evidence.update(
            contact_probes=report["contact_probes"],
            final_rgb_identical=True,
            same_bag=request["task"] == "order",
        )
    else:
        if report["contact_probes"]:
            raise ValueError("unexpected tracking contact queries")
        if {p.name for p in (root / "full-masks").iterdir()} != {k + ".png" for k in records}:
            raise ValueError("incomplete full silhouette evidence")
        visible = {}
        for frame in range(28):
            key = f"frame-{frame:02d}"
            annotation = records[key]["tracking"]
            visible[frame] = annotation["facing_camera"] and point_visible(
                masks[key], annotation["surface_point"]
            )
        ref = request["tracking"]["reference_frame"]
        first = request["tracking"]["primary_frames"][0]
        if not visible[ref] or any(visible[t] for t in range(ref + 1, first)):
            raise ValueError("reference/occlusion visibility does not match rendered point")
        if not all(visible[t] for t in (first, first + 1, first + 2)):
            raise ValueError("first three reappearance frames not visible")
        if request["tracking"]["primary_frames"] != list(range(first, first + 3)):
            raise ValueError("primary tracking frames not consecutive")
        if not first + 2 - 15 <= ref < first or visible[request["tracking"]["auxiliary_frame"]]:
            raise ValueError("causal reference/auxiliary constraints failed")
        diagonals = {
            t: diagonal(rgb(root / "full-masks" / f"frame-{t:02d}.png")) for t in [17, 25, 26, 27]
        }
        if min(diagonals[t] for t in [25, 26, 27]) < plan["minimum_tracking_diagonal_pixels"]:
            raise ValueError("primary tracking object too small")
        evidence.update(
            reference_frame=ref,
            first_reappearance=first,
            visibility={str(k): v for k, v in visible.items()},
            full_diagonal_pixels={str(k): v for k, v in diagonals.items()},
            physical_clearance=request["tracking"]["minimum_physical_clearance"],
        )
    return records, evidence


def exports(request, records, evidence):
    gid, task, split = request["group_id"], request["task"], request["split"]
    inputs, labels, groups = [], [], []

    def image_id(key):
        return f"{gid}/{key}"

    if task in ("collision", "order"):
        for branch in request["branches"]:
            eid = f"{gid}-b{branch['branch']}"
            groups.append(dict(episode_id=eid, task_id=task, group_id=gid, split=split))
            point = records[branch["observed"][-1]]["projected_centers"]
            for horizon in (0.25, 0.5, 1.0):
                row = dict(
                    schema_version="bullet-time.evaluation.v2",
                    episode_id=eid,
                    query_id="forecast",
                    task_id=task,
                    split=split,
                    observed_image_ids=[image_id(k) for k in branch["observed"]],
                    observed_frame_indices=list(range(16)),
                    query_points=[point["projectile"], point["target"]],
                    horizon_seconds=horizon,
                )
                inputs.append(row)
                labels.append(
                    dict(
                        schema_version="bullet-time.labels.v1",
                        task_id=task,
                        episode_id=eid,
                        query_id="forecast",
                        horizon_or_frame=str(horizon),
                        split=split,
                        target={"contact": branch["labels"][str(horizon)]},
                    )
                )
    else:
        eid = gid
        groups.append(dict(episode_id=eid, task_id=task, group_id=gid, split=split))
        ref = request["tracking"]["reference_frame"]
        for frame in [
            request["tracking"]["auxiliary_frame"],
            *request["tracking"]["primary_frames"],
        ]:
            role = "auxiliary" if frame == request["tracking"]["auxiliary_frame"] else "primary"
            row = dict(
                schema_version="bullet-time.evaluation.v2",
                episode_id=eid,
                task_id=task,
                query_id="reacquire",
                split=split,
                observed_image_ids=[
                    image_id(f"frame-{t:02d}") for t in range(frame - 15, frame + 1)
                ],
                observed_frame_indices=list(range(frame - 15, frame + 1)),
                query_points=[],
                prediction_frame=frame,
                reference_image_id=image_id(f"frame-{ref:02d}"),
                reference_frame=ref,
                reference_point=records[f"frame-{ref:02d}"]["tracking"]["surface_point"],
                prediction_role=role,
            )
            inputs.append(row)
            point = records[f"frame-{frame:02d}"]["tracking"]["surface_point"]
            labels.append(
                dict(
                    schema_version="bullet-time.labels.v1",
                    task_id=task,
                    episode_id=eid,
                    query_id=row["query_id"],
                    horizon_or_frame=str(frame),
                    split=split,
                    target=dict(
                        x=point[0],
                        y=point[1],
                        visible=int(evidence["visibility"][str(frame)]),
                        bbox_diagonal_pixels=evidence["full_diagonal_pixels"][str(frame)],
                        prediction_role=role,
                    ),
                )
            )
    return inputs, labels, groups


def write_lines(path, rows):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"".join(canonical_bytes(r) + b"\n" for r in rows))


def reuse_capture_source(root, plan, pin, sources):
    """Admit raw captures only; old exports/admission status are never inherited."""
    root = Path(root).resolve(strict=True)
    old = read(root / "bundle.json")
    compatible_plan = old["plan"] == plan
    if (
        old["plan"].get("schema_version")
        == plan.get("schema_version")
        == "bullet-time.measurement-plan.v2"
        and old["plan"]["per_stratum"] <= plan["per_stratum"]
    ):
        check_plan(old["plan"])
        compatible_plan = all(
            old["plan"][key] == value
            for key, value in plan.items()
            if key not in {"per_stratum", "groups_per_task", "selection_sha256"}
        )
    if (
        old["schema_version"] != "bullet-time.measurement-bundle.v1"
        or old["development"]
        or not compatible_plan
        or old["engine_pin"] != pin
    ):
        raise ValueError("raw capture plan/runtime/development mismatch")

    def rendering_sources(records):
        return {
            key: value
            for key, value in records.items()
            if key.startswith(("game/", "configs/rendering/"))
        }

    if not rendering_sources(sources) or rendering_sources(
        old["producer_sources"]
    ) != rendering_sources(sources):
        raise ValueError("raw capture renderer/runtime source changed; cannot reuse")
    actual = {
        p.relative_to(root).as_posix()
        for p in root.rglob("*")
        if p.is_file() and p != root / "bundle.json"
    }
    if actual != old["inventory"].keys():
        raise ValueError("raw capture inventory differs")
    for name, checksum in old["inventory"].items():
        if sha(inside(root, name)) != checksum:
            raise ValueError("raw capture bytes changed")
    return root, dict(
        bundle_sha256=sha(root / "bundle.json"),
        producer_sources=old["producer_sources"],
        original_generation=read(root / "generation.json"),
    )


def reusable_request(root, request):
    path = root / "private" / request["group_id"] / "request.json"
    return path.is_file() and canonical_bytes(read(path)) == canonical_bytes(request)


def build_measurements(
    output, binary, *, development=False, reuse=None, full_selection=None, per_stratum=None
):
    output = Path(output).resolve()
    if output.exists():
        raise ValueError("refusing to overwrite an existing measurement drop")
    full_requests, full_stats = None, None
    if full_selection is None:
        if per_stratum is not None:
            raise ValueError("per-stratum capture requires a full selection")
        plan = read(ROOT / "configs/generation/evaluation-development.json")
    else:
        full_selection = Path(full_selection).resolve(strict=True)
        selected_report = verify_selection(full_selection)
        full_requests = [
            strict_json(line)
            for line in (full_selection / "private/requests.jsonl").read_bytes().splitlines()
        ]
        full_stats = selected_report["selection"]
        plan = progressive_plan(
            sha(full_selection / "selection.json"), 1 if per_stratum is None else per_stratum
        )
    check_plan(plan)
    pin = read(ROOT / "configs/rendering/godot-macos.json")
    binary = verify_engine(binary, pin)
    sources = source_files()
    dirty = bool(subprocess.check_output(["git", "status", "--porcelain"], cwd=ROOT))
    if dirty and not development:
        raise ValueError(
            "commit producer before accepted generation; development labels debugging only"
        )
    old = reuse_capture_source(reuse, plan, pin, sources) if reuse is not None else None
    output.mkdir(parents=True)
    if full_selection is not None:
        shutil.copy2(full_selection / "selection.json", output / "selection.json")
    requests, selection, all_selected = select_for_capture(
        plan, full_requests=full_requests, full_selection=full_stats
    )
    if all_selected is not None:
        validate_selection_copy(output, plan, all_selected, selection)
    check_lineage(requests, plan)
    all_inputs, all_labels, all_groups, images, summaries, commands = [], [], [], [], [], []
    for request in requests:
        gid = request["group_id"]
        private = output / "private" / gid
        if old and reusable_request(old[0], request):
            shutil.copytree(old[0] / "private" / gid, private)
            shutil.copytree(old[0] / "inputs/rgb" / gid, private / "rgb")
            if canonical_bytes(read(private / "request.json")) != canonical_bytes(request):
                raise ValueError("raw capture request differs from current selected request")
            commands.append(
                dict(reused_capture_group=gid, source_bundle_sha256=old[1]["bundle_sha256"])
            )
        else:
            for folder in ("rgb", "masks", "full-masks", "repeat"):
                (private / folder).mkdir(parents=True)
            atomic_json(private / "request.json", request)
            args = [
                str(binary),
                "--path",
                str(ROOT / "game"),
                "--rendering-method",
                "gl_compatibility",
                "--resolution",
                "224x224",
                "--position",
                "20,60",
                "--script",
                "res://evaluation_driver.gd",
                "--",
                str(private / "request.json"),
                str(private),
            ]
            commands.append(invoke(args, private / "render.log", 90))
        if "ERROR:" in (private / "render.log").read_text():
            raise ValueError("Godot logged an error; retain this rejected attempt")
        records, evidence = validate_capture(private, request, plan, pin)
        inp, lab, grp = exports(request, records, evidence)
        all_inputs.extend(inp)
        all_labels.extend(lab)
        all_groups.extend(grp)
        rgb_root = output / "inputs" / "rgb" / gid
        rgb_root.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(private / "rgb"), str(rgb_root))
        images.extend(image_catalog(output / "inputs", request))
        summaries.append(
            dict(
                group_id=gid,
                task=request["task"],
                split=request["split"],
                groups=request["groups"],
                **evidence,
            )
        )
        print(f"Validated {gid}: {len(records)} frames; {request['split']}", flush=True)
    write_lines(output / "inputs/images.jsonl", images)
    write_lines(output / "inputs/evaluation.jsonl", all_inputs)
    for split in ("train", "dev"):
        write_lines(
            output / f"inputs/{split}.jsonl", [r for r in all_inputs if r["split"] == split]
        )
        write_lines(
            output / f"private/{split}-labels.jsonl", [r for r in all_labels if r["split"] == split]
        )
    write_lines(output / "private/labels.jsonl", all_labels)
    atomic_json(
        output / "groups.json",
        dict(schema_version="bullet-time.evaluation-groups.v1", records=all_groups),
    )
    atomic_json(
        output / "validation.json",
        dict(
            summaries=summaries,
            selection=selection,
            capture_counts=plan_counts(plan),
            scientific_gate_pass=False,
        ),
    )
    atomic_json(
        output / "generation.json",
        dict(
            commands=commands,
            host=platform.platform(),
            development=development,
            reused_captures=None if old is None else old[1],
            source_commit=subprocess.check_output(
                ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
            ).strip(),
        ),
    )
    if source_files() != sources:
        raise ValueError("producer changed during generation")
    atomic_json(
        output / "bundle.json",
        dict(
            schema_version="bullet-time.measurement-bundle.v1",
            plan=plan,
            engine_pin=pin,
            producer_sources=sources,
            development=development,
            inventory={
                p.relative_to(output).as_posix(): sha(p)
                for p in sorted(output.rglob("*"))
                if p.is_file()
            },
            boundary="train/dev only; inputs contain RGB/permitted queries; private labels/state are siblings, not OS-isolated",
        ),
    )
    return verify_measurements(output)


def verify_measurements(root):
    from bullet_time.evaluation.inputs import ImageStore, EvaluationInputs
    from bullet_time.evaluation.training import Targets
    from bullet_time.evaluation.subsets import Groups, verify_pairs

    root = Path(root).resolve(strict=True)
    bundle = read(root / "bundle.json")
    if bundle["schema_version"] != "bullet-time.measurement-bundle.v1":
        raise ValueError("unknown measurement bundle")
    if bundle["producer_sources"] != source_files():
        raise ValueError("measurement producer changed; use its pinned source revision to reverify")
    check_plan(bundle["plan"])
    actual = {
        p.relative_to(root).as_posix()
        for p in root.rglob("*")
        if p.is_file() and p != root / "bundle.json"
    }
    if actual != bundle["inventory"].keys():
        raise ValueError("measurement inventory differs")
    for name, checksum in bundle["inventory"].items():
        if sha(inside(root, name)) != checksum:
            raise ValueError("measurement artifact hash mismatch")
    expected_inputs, expected_labels, expected_groups, requests, summaries = [], [], [], [], []
    expected_images = []
    selected, selection, all_selected = select_for_capture(bundle["plan"])
    if all_selected is not None:
        validate_selection_copy(root, bundle["plan"], all_selected, selection)
    for request in selected:
        task, split = request["task"], request["split"]
        gid = request["group_id"]
        if read(root / "private" / gid / "request.json") != request:
            raise ValueError("request differs from reproducible content selection")
        records, evidence = validate_capture(
            root / "private" / gid,
            request,
            bundle["plan"],
            bundle["engine_pin"],
            rgb_root=root / "inputs/rgb" / gid,
        )
        inp, lab, grp = exports(request, records, evidence)
        expected_inputs.extend(inp)
        expected_labels.extend(lab)
        expected_groups.extend(grp)
        requests.append(request)
        expected_images.extend(image_catalog(root / "inputs", request))
        summaries.append(
            dict(group_id=gid, task=task, split=split, groups=request["groups"], **evidence)
        )

    def line_bytes(rows):
        return b"".join(canonical_bytes(r) + b"\n" for r in rows)

    if (root / "inputs/images.jsonl").read_bytes() != line_bytes(expected_images):
        raise ValueError("image catalog differs from actual captured frames")

    if (root / "inputs/evaluation.jsonl").read_bytes() != line_bytes(expected_inputs) or (
        root / "private/labels.jsonl"
    ).read_bytes() != line_bytes(expected_labels):
        raise ValueError("measurement exports differ from admitted renderer evidence")
    for split in ("train", "dev"):
        if (root / f"inputs/{split}.jsonl").read_bytes() != line_bytes(
            [r for r in expected_inputs if r["split"] == split]
        ) or (root / f"private/{split}-labels.jsonl").read_bytes() != line_bytes(
            [r for r in expected_labels if r["split"] == split]
        ):
            raise ValueError("split export differs from admitted records")
    if (
        read(root / "groups.json")["records"] != expected_groups
        or read(root / "validation.json")["summaries"] != summaries
        or read(root / "validation.json")["selection"] != selection
        or read(root / "validation.json")["capture_counts"] != plan_counts(bundle["plan"])
    ):
        raise ValueError("group/summary report differs from actual validation")
    lineage = check_lineage(requests, bundle["plan"])
    duplicates = check_duplicates(root, requests, bundle["plan"])
    store = ImageStore(root / "inputs/images.jsonl")
    inputs = EvaluationInputs(root / "inputs/evaluation.jsonl", store)
    targets = Targets(root / "private/labels.jsonl", inputs)
    groups = Groups(root / "groups.json")
    pair_checks = {
        task: verify_pairs(inputs, targets, groups, task) for task in ("collision", "order")
    }
    groups.validate_inputs(inputs, "tracking")
    return dict(
        groups=len(read(root / "validation.json")["summaries"]),
        episodes=len({e.episode_id for e in inputs.examples}),
        images=len(store.images),
        examples=len(inputs.examples),
        pair_checks=pair_checks,
        bundle_sha256=sha(root / "bundle.json"),
        development=bundle["development"],
        scientific_gate_pass=False,
        scope=bundle["plan"]["scope"],
        lineage=lineage,
        duplicates=duplicates,
    )


def check_lineage(requests, plan):
    counts = Counter((r["task"], r["split"]) for r in requests)
    wanted = {(t, s): n for t, row in plan_counts(plan).items() for s, n in row.items()}
    if counts != wanted or len({r["group_id"] for r in requests}) != len(requests):
        raise ValueError("measurement task/split/group inventory mismatch")
    seen = {k: {} for k in ("trajectory", "asset", "configuration")}
    for request in requests:
        if set(request["assigned_pools"].values()) != {request["split"]}:
            raise ValueError("content prototype assigned to another split")
        for kind in seen:
            content = request["prototypes"][kind]
            group = identity([kind, content])
            if request["groups"][kind] != group:
                raise ValueError("lineage hash differs from content")
            if group in seen[kind]:
                raise ValueError(f"duplicate {kind} prototype across measurement groups")
            seen[kind][group] = request["split"]
    return {k: len(v) for k, v in seen.items()}


def check_duplicates(root, requests, plan):
    """Exact RGB check plus exhaustive cross-split mask/foreground near-duplicate check.

    Near duplicates require >=98% foreground-mask IoU and <=1/255 RGB mean absolute
    difference over their union. Empty foreground uses full RGB. This is a specific
    raster test, not a claim that semantic/perceptual redundancy is eliminated.
    """
    threshold = number(plan["near_duplicate_foreground_iou"], "foreground IoU", 1e-12, 1)
    max_difference = number(plan["near_duplicate_rgb_mae"], "RGB MAE", 0, 1)
    rows, hashes, unique = [], {}, set()
    image_counts = Counter()
    for request in requests:
        gid = request["group_id"]
        if request["split"] not in ("train", "dev"):
            raise ValueError("raster duplicate check is train/dev only")
        for key in request["frames"]:
            path = root / "inputs/rgb" / gid / (key + ".png")
            pixels = rgb(path)
            checksum = digest(pixels.tobytes())
            if checksum in hashes and hashes[checksum][0] != request["split"]:
                raise ValueError("exact duplicate RGB across train/dev")
            hashes[checksum] = (request["split"], gid)
            mask = rgb(root / "private" / gid / "masks" / (key + ".png"))
            fg = foreground(mask) | foreground(mask, 1) | foreground(mask, 2)
            packed = np.packbits(fg)
            image_counts[request["split"]] += 1
            signature = (request["split"], checksum, digest(packed.tobytes()))
            if signature in unique:
                continue
            unique.add(signature)
            yy, xx = np.nonzero(fg)
            bbox = (
                (int(xx.min()), int(yy.min()), int(xx.max()), int(yy.max()))
                if len(xx)
                else (0, 0, -1, -1)
            )
            rows.append(
                dict(
                    split=request["split"],
                    gid=gid,
                    key=key,
                    path=path,
                    checksum=checksum,
                    mask=packed,
                    area=len(xx),
                    bbox=bbox,
                    sums=pixels.sum(axis=(0, 1), dtype=np.int64),
                )
            )
    left = [r for r in rows if r["split"] == "train"]
    right = [r for r in rows if r["split"] == "dev"]
    areas = np.array([r["area"] for r in right], dtype=np.int64)
    boxes = np.array([r["bbox"] for r in right], dtype=np.int64).reshape(-1, 4)
    empty = np.flatnonzero(areas == 0)
    popcount = np.unpackbits(np.arange(256, dtype=np.uint8)[:, None], axis=1).sum(axis=1)

    @lru_cache(maxsize=64)
    def pixels_for(path, checksum):
        pixels = rgb(path)
        if digest(pixels.tobytes()) != checksum:
            raise ValueError("RGB changed during duplicate check")
        return pixels

    comparisons = mask_candidates = mean_bound_skips = 0
    for a in left:
        if not a["area"]:
            candidates = empty
        else:
            ax, ay, az, aw = a["bbox"]
            overlap = np.maximum(
                0, np.minimum(az, boxes[:, 2]) - np.maximum(ax, boxes[:, 0]) + 1
            ) * np.maximum(0, np.minimum(aw, boxes[:, 3]) - np.maximum(ay, boxes[:, 1]) + 1)
            cap = np.minimum(np.minimum(a["area"], areas), overlap)
            candidates = np.flatnonzero(cap / (a["area"] + areas - cap) >= threshold)
        mask_candidates += len(candidates)
        for index in candidates:
            b = right[index]
            if not a["area"]:
                # Triangle inequality: channel-mean distance lower-bounds full RGB MAE.
                lower_bound = np.abs(a["sums"] - b["sums"]).sum() / (224 * 224 * 3 * 255)
                if lower_bound > max_difference + 1e-12:
                    mean_bound_skips += 1
                    continue
                pa, pb = pixels_for(a["path"], a["checksum"]), pixels_for(b["path"], b["checksum"])
                difference = float(np.abs(pa.astype(float) - pb).mean() / 255)
            else:
                intersection = int(popcount[a["mask"] & b["mask"]].sum())
                if intersection / (a["area"] + b["area"] - intersection) < threshold:
                    continue
                indices = np.flatnonzero(np.unpackbits(a["mask"] | b["mask"]))
                pa, pb = pixels_for(a["path"], a["checksum"]), pixels_for(b["path"], b["checksum"])
                difference = float(
                    np.abs(
                        pa.reshape(-1, 3)[indices].astype(float) - pb.reshape(-1, 3)[indices]
                    ).mean()
                    / 255
                )
            comparisons += 1
            if difference <= max_difference:
                raise ValueError(
                    f"near duplicate RGB across splits: {(a['gid'], a['key'])} / {(b['gid'], b['key'])}"
                )
    return dict(
        images=sum(image_counts.values()),
        cross_split_image_pairs=image_counts["train"] * image_counts["dev"],
        unique_raster_mask_pairs=len(rows),
        unique_cross_split_comparisons=len(left) * len(right),
        mask_candidates=mask_candidates,
        mean_bound_skips=mean_bound_skips,
        candidate_rgb_comparisons=comparisons,
        rgb_cache_capacity=64,
        retained_mask_bytes=sum(r["mask"].nbytes for r in rows),
        exact_cross_split_duplicates=0,
        near_duplicates=0,
        foreground_iou=plan["near_duplicate_foreground_iou"],
        rgb_mae=plan["near_duplicate_rgb_mae"],
        scope="train/dev raster and prototype checks; old pretraining integration pool and future final test not admitted",
    )
