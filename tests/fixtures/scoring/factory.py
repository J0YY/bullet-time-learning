"""Known-answer scoring wires, deliberately synthetic and independent of generator."""

from pathlib import Path
import json
from bullet_time.provenance import identity, atomic_json
from bullet_time.evaluation.export import KEY, write_predictions


def make_run(root, task="collision", families=("projectile_arena",), episodes_per_family=None):
    root = Path(root)
    root.mkdir(parents=True)
    expected = []
    observed = []
    labels = []
    groups = []
    for fi, family in enumerate(families):
        count = (episodes_per_family or [2] * len(families))[fi]
        for e in range(count):
            eid = f"{family}-ep-{e}"
            gid = f"{family}-group-{e // 2 if task in ('collision', 'order') else e}"
            groups.append(dict(episode_id=eid, task_id=task, group_id=gid, split="dev"))
            for frame in [17, 18, 19, 15] if task == "tracking" else [0]:
                horizon = str(frame) if task == "tracking" else "clip" if task == "ssv2" else "0.5"
                role = "auxiliary" if task == "tracking" and frame == 15 else "primary"
                target = (
                    {"contact": e % 2}
                    if task in ("collision", "order")
                    else {"class_id": e % 2}
                    if task == "ssv2"
                    else dict(
                        x=0.5,
                        y=0.5,
                        visible=int(role == "primary"),
                        bbox_diagonal_pixels=32,
                        prediction_role=role,
                    )
                )
                label = dict(
                    schema_version="bullet-time.labels.v1",
                    task_id=task,
                    episode_id=eid,
                    query_id=f"q{frame}",
                    horizon_or_frame=horizon,
                    split="dev",
                    target=target,
                )
                labels.append(label)
                row = dict(
                    run_id="1" * 64,
                    checkpoint_id="2" * 64,
                    task_id=task,
                    label_budget=300,
                    readout_seed=101,
                    episode_or_video_id=eid,
                    query_id=f"q{frame}",
                    horizon_or_frame=horizon,
                    split="dev",
                    scene_family=family,
                    pair_group_id=gid,
                    target_reference_sha256=identity(label),
                    prediction_role=role,
                )
                expected.append(row)
                pred = {k: row[k] for k in KEY}
                pred.update(status="ok", error="")
                if task in ("collision", "order"):
                    pred["contact_probability"] = 0.5
                elif task == "ssv2":
                    pred["class_id"] = e % 2
                else:
                    pred.update(x=0.5, y=0.5, visibility_probability=target["visible"])
                observed.append(pred)
    expected_path = root / "expected.json"
    atomic_json(expected_path, expected)
    labels_path = root / "labels.jsonl"
    labels_path.write_text("".join(json.dumps(r) + "\n" for r in labels))
    groups_path = root / "groups.json"
    atomic_json(
        groups_path, dict(schema_version="bullet-time.evaluation-groups.v1", records=groups)
    )
    directory = root / "predictions"
    write_predictions(directory, expected, observed, {"scope": "synthetic known answer"})
    return directory, expected_path, labels_path, groups_path, list(families)


def make_plan(root):
    from copy import deepcopy
    from bullet_time.provenance import digest

    root = Path(root)
    base = make_run(root / "base")
    expected = json.loads(base[1].read_text())
    slots = []
    facets = dict(
        objective="videomae_raw_rgb",
        task_id="collision",
        horizon="0.5",
        label_budget=300,
        checkpoint_pass=20,
        model_kind="controlled",
        corpus_sha256="c" * 64,
        readout_recipe_sha256="a" * 64,
    )
    for condition in ["view", "time"]:
        for seed in [17, 29, 43]:
            for readout in [101, 102, 103]:
                sid = f"{condition}-{seed}-{readout}"
                folder = root / sid
                folder.mkdir()
                rows = deepcopy(expected)
                for row in rows:
                    row.update(
                        run_id=identity([condition, seed]),
                        checkpoint_id=identity([condition, seed, "checkpoint"]),
                        readout_seed=readout,
                    )
                pred = []
                for row in rows:
                    p = {k: row[k] for k in KEY}
                    p.update(status="ok", error="", contact_probability=0.5)
                    if condition == "time" and seed == 29:
                        p["contact_probability"] = float(row["episode_or_video_id"].endswith("-1"))
                    pred.append(p)
                atomic_json(folder / "expected.json", rows)
                write_predictions(
                    folder / "predictions", rows, pred, {"scope": "synthetic known answer"}
                )
                slots.append(
                    {
                        **facets,
                        "slot_id": sid,
                        "condition": condition,
                        "pretraining_seed": seed,
                        "readout_seed": readout,
                        "expected": {
                            "path": f"{sid}/expected.json",
                            "sha256": digest((folder / "expected.json").read_bytes()),
                        },
                        "predictions": f"{sid}/predictions",
                    }
                )
    plan = dict(
        schema_version="bullet-time.scoring-plan.v1",
        scope="synthetic",
        split="dev",
        families=base[-1],
        classes=174,
        labels={"path": "base/labels.jsonl", "sha256": digest(base[2].read_bytes())},
        groups={"path": "base/groups.json", "sha256": digest(base[3].read_bytes())},
        pretraining_seeds=[17, 29, 43],
        readout_seeds=[101, 102, 103],
        slots=slots,
        contrasts=[
            {
                **facets,
                "contrast_id": "time-view",
                "condition": "time",
                "reference": "view",
                "margin": 0.02,
            }
        ],
        bootstrap={"replicates": 100, "seed": 99},
    )
    path = root / "plan.json"
    atomic_json(path, plan)
    return path
