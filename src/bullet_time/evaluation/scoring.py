"""Hash-bound expected/observed/label joins and fail-explicit scoring."""

import csv
from pathlib import Path
import re
from collections import defaultdict

from bullet_time.provenance import (
    strict_json,
    fields,
    identity,
    digest,
    integer,
    number,
    sha256,
    text_id,
)
from .export import COLUMNS, KEY, OUTPUTS, key_of
from .metrics import summarize

EXPECTED = set(COLUMNS) - set(OUTPUTS) - {"status", "error"}
LABEL_FIELDS = {
    "schema_version",
    "task_id",
    "episode_id",
    "query_id",
    "horizon_or_frame",
    "split",
    "target",
}


def file_json(path):
    return strict_json(Path(path).read_bytes())


def label_key(row):
    return (
        row["task_id"],
        row.get("episode_id", row.get("episode_or_video_id")),
        row["query_id"],
        str(row["horizon_or_frame"]),
    )


def validate_target(row, classes=174):
    fields(row, LABEL_FIELDS)
    if row["schema_version"] != "bullet-time.labels.v1" or row["split"] not in (
        "train",
        "dev",
        "assessment",
    ):
        raise ValueError("unsupported label schema/split")
    for key in ("episode_id", "query_id", "horizon_or_frame"):
        text_id(row[key], key)
    t = row["target"]
    task = row["task_id"]
    if task in ("collision", "order"):
        fields(t, {"contact"})
        if type(t["contact"]) is not int or t["contact"] not in (0, 1):
            raise ValueError("nonbinary contact")
        if row["horizon_or_frame"] not in ("0.25", "0.5", "1.0"):
            raise ValueError("unsupported horizon")
    elif task == "tracking":
        fields(t, {"x", "y", "visible", "bbox_diagonal_pixels", "prediction_role"})
        for k in ("x", "y"):
            number(t[k], k, 0, 1)
        number(t["bbox_diagonal_pixels"], "bbox diagonal", 1e-12)
        if type(t["visible"]) is not int or t["visible"] not in (0, 1):
            raise ValueError("nonbinary visibility")
        if t["prediction_role"] not in ("primary", "auxiliary"):
            raise ValueError("unknown tracking role")
        if not re.fullmatch(r"0|[1-9][0-9]*", row["horizon_or_frame"]):
            raise ValueError("invalid frame")
    elif task == "ssv2":
        fields(t, {"class_id"})
        integer(t["class_id"], "class_id")
        if t["class_id"] >= classes or row["horizon_or_frame"] != "clip":
            raise ValueError("invalid action target")
    else:
        raise ValueError("unknown label task")


def load_expected(path, split):
    rows = file_json(path)
    seen = {}
    if not isinstance(rows, list) or not rows:
        raise ValueError("empty expected inventory")
    for row in rows:
        fields(row, EXPECTED)
        for k in ("run_id", "checkpoint_id", "target_reference_sha256"):
            sha256(row[k])
        integer(row["label_budget"], "label_budget", 1)
        integer(row["readout_seed"], "readout_seed")
        for k in (
            "episode_or_video_id",
            "query_id",
            "scene_family",
            "pair_group_id",
            "horizon_or_frame",
        ):
            text_id(row[k], k)
        if row["split"] != split or row["prediction_role"] not in ("primary", "auxiliary"):
            raise ValueError("expected split/role mismatch")
        if row["task_id"] not in ("collision", "order", "tracking", "ssv2"):
            raise ValueError("unknown expected task")
        if row["task_id"] != "tracking" and row["prediction_role"] != "primary":
            raise ValueError("auxiliary classification query")
        key = key_of(row)
        if key in seen:
            raise ValueError("duplicate expected prediction key")
        seen[key] = row
    predictors = {tuple(str(r[k]) for k in KEY[:5]) for r in rows}
    if len(predictors) != 1:
        raise ValueError("one predictor/task per scoring slot required")
    return seen


def join_labels(expected, labels, groups, split, classes):
    targets = {}
    for line in Path(labels).read_bytes().splitlines():
        row = strict_json(line)
        validate_target(row, classes)
        if row["split"] != split:
            raise ValueError("label split is inaccessible to this scoring job")
        k = label_key(row)
        if k in targets:
            raise ValueError("duplicate label key")
        targets[k] = row
    group_data = file_json(groups)
    # External group exports are the existing full video-ID -> related-group map.
    # Unselected related members still participate in the whole-group check below.
    if {e["task_id"] for e in expected.values()} == {"ssv2"} and "schema_version" not in group_data:
        if not isinstance(group_data, dict) or not group_data:
            raise ValueError("invalid external group map")
        group_data = {
            "schema_version": "bullet-time.evaluation-groups.v1",
            "records": [
                {
                    "episode_id": text_id(eid, "video ID"),
                    "task_id": "ssv2",
                    "group_id": text_id(gid, "related group"),
                    "split": split,
                }
                for eid, gid in group_data.items()
            ],
        }
    fields(group_data, {"schema_version", "records"})
    if group_data["schema_version"] != "bullet-time.evaluation-groups.v1":
        raise ValueError("unknown group schema")
    group_map = {}
    group_splits = {}
    episode_splits = {}
    members = defaultdict(set)
    for row in group_data["records"]:
        fields(row, {"episode_id", "task_id", "group_id", "split"})
        for name in row:
            text_id(row[name], name)
        if row["split"] not in ("train", "dev", "assessment"):
            raise ValueError("invalid group split")
        key = (row["task_id"], row["episode_id"])
        if key in group_map:
            raise ValueError("duplicate group episode")
        group_map[key] = row
        for mapping, identifier in [
            (group_splits, row["group_id"]),
            (episode_splits, row["episode_id"]),
        ]:
            if identifier in mapping and mapping[identifier] != row["split"]:
                raise ValueError("group/episode leaks across splits")
            mapping[identifier] = row["split"]
        members[(row["task_id"], row["group_id"])].add(row["episode_id"])
    joined = {}
    selected_groups = defaultdict(set)
    for key, e in expected.items():
        k = label_key(e)
        if k not in targets:
            raise ValueError("missing label for expected prediction")
        y = targets[k]
        if identity(y) != e["target_reference_sha256"]:
            raise ValueError("target reference hash mismatch")
        group = group_map.get((e["task_id"], e["episode_or_video_id"]))
        if group is None or group["group_id"] != e["pair_group_id"] or group["split"] != split:
            raise ValueError("prediction/group mismatch")
        if e["task_id"] == "tracking" and e["prediction_role"] != y["target"]["prediction_role"]:
            raise ValueError("target/prediction role mismatch")
        selected_groups[(e["task_id"], e["pair_group_id"])].add(e["episode_or_video_id"])
        joined[key] = {
            "task_id": e["task_id"],
            "episode_id": e["episode_or_video_id"],
            "query_id": e["query_id"],
            "horizon_or_frame": e["horizon_or_frame"],
            "family": e["scene_family"],
            "group_id": e["pair_group_id"],
            "target": y["target"],
        }
    for (task, gid), selected in selected_groups.items():
        if selected != members[(task, gid)]:
            raise ValueError("selected partial related group")
        if task in ("collision", "order") and len(selected) != 2:
            raise ValueError("classification group must be a pair")
        if task == "tracking" and len(selected) != 1:
            raise ValueError("tracking group must contain one episode")
    primary_pairs = defaultdict(list)
    for row in joined.values():
        if row["task_id"] in ("collision", "order") and row["horizon_or_frame"] == "0.5":
            primary_pairs[row["group_id"]].append(row)
    if any(
        len(rows) != 2 or {r["target"]["contact"] for r in rows} != {0, 1}
        for rows in primary_pairs.values()
    ):
        raise ValueError("primary paired outcomes must be opposite")
    # A group cannot mix families; preserve a pair as one resampling unit.
    family_groups = defaultdict(set)
    for r in joined.values():
        family_groups[r["group_id"]].add(r["family"])
    if any(len(v) != 1 for v in family_groups.values()):
        raise ValueError("group spans scene families")
    return joined


def read_predictions(directory, expected, classes):
    directory = Path(directory)
    if not directory.exists():
        return {
            k: {"status": "missing", "error": "planned run not delivered", "prediction": {}}
            for k in expected
        }, {"state": "missing_run"}
    if not (directory / "run.json").is_file():
        failure = directory / "failure.json"
        reason = "run has no completed prediction export"
        provenance = {"state": "incomplete_export"}
        status = "missing"
        if failure.exists():
            record = file_json(failure)
            if record.get("status") != "failed" or not record.get("error"):
                raise ValueError("malformed failure receipt")
            reason = str(record["error"])
            status = "failed"
            provenance = {"state": "failed_run", "failure_sha256": digest(failure.read_bytes())}
        return {
            k: {"status": status, "error": reason, "prediction": {}} for k in expected
        }, provenance
    meta = file_json(directory / "run.json")
    coverage = file_json(directory / "coverage.json")
    if (
        meta.get("schema_version") != "bullet-time.run.v1"
        or meta.get("prediction_schema_version") != "bullet-time.prediction.v1"
    ):
        raise ValueError("unknown prediction export")
    for file, field in [("predictions.csv", "csv_sha256"), ("coverage.json", "coverage_sha256")]:
        if digest((directory / file).read_bytes()) != meta.get(field):
            raise ValueError("prediction artifact hash mismatch")
    if coverage.get("csv_sha256") != meta["csv_sha256"]:
        raise ValueError("coverage CSV binding mismatch")
    inventory = coverage.get("expected_keys", [])
    if len(inventory) != len(expected) or {tuple(k) for k in inventory} != set(expected):
        raise ValueError("coverage inventory differs from independent expected keys")
    result = {}
    with (directory / "predictions.csv").open(newline="") as f:
        reader = csv.DictReader(f)
        if reader.fieldnames != list(COLUMNS):
            raise ValueError("unexpected CSV columns")
        for r in reader:
            if None in r or None in r.values():
                raise ValueError("malformed CSV row")
            key = key_of(r)
            if key in result or key not in expected:
                raise ValueError("duplicate/unplanned CSV key")
            e = expected[key]
            if any(r[k] != str(e[k]) for k in EXPECTED):
                raise ValueError("CSV identity/metadata differs from expected")
            status = r["status"]
            error = r["error"]
            needed = (
                {"contact_probability"}
                if r["task_id"] in ("collision", "order")
                else {"class_id"}
                if r["task_id"] == "ssv2"
                else {"x", "y", "visibility_probability"}
            )
            present = {k for k in OUTPUTS if r[k] != ""}
            prediction = {}
            if status == "ok":
                if error or present != needed:
                    raise ValueError("invalid successful output")
                for k in needed:
                    if k == "class_id":
                        if not re.fullmatch(r"0|[1-9][0-9]*", r[k]) or int(r[k]) >= classes:
                            raise ValueError("invalid predicted class")
                        prediction[k] = int(r[k])
                    else:
                        prediction[k] = number(float(r[k]), k, 0, 1)
            elif status not in ("missing", "failed") or not error or present:
                raise ValueError("invalid failure status/output")
            result[key] = {"status": status, "error": error, "prediction": prediction}
    if result.keys() != expected.keys():
        raise ValueError("CSV omits expected rows; export explicit missing rows")
    counts = {
        status: sum(r["status"] == status for r in result.values())
        for status in ("ok", "failed", "missing")
    }
    if (
        any(coverage.get(k) != v for k, v in counts.items())
        or coverage.get("expected") != len(expected)
        or coverage.get("complete") != (counts["ok"] == len(expected))
    ):
        raise ValueError("coverage counters disagree with actual rows")
    return result, {
        "state": "delivered",
        "run_sha256": digest((directory / "run.json").read_bytes()),
        "csv_sha256": meta["csv_sha256"],
        "coverage_sha256": meta["coverage_sha256"],
    }


def score_directory(
    directory, expected_path, labels_path, groups_path, *, split, families, classes=174
):
    if split not in ("train", "dev"):
        raise ValueError(
            "direct scoring is train/dev only; assessment requires a locked release job"
        )
    expected = load_expected(expected_path, split)
    joined = join_labels(expected, labels_path, groups_path, split, classes)
    observed, provenance = read_predictions(directory, expected, classes)
    rows = [{**joined[k], **observed[k]} for k in expected]
    task = rows[0]["task_id"]
    # Each horizon is a different fitted head; tracking frames are one endpoint.
    horizons = {r["horizon_or_frame"] for r in rows}
    if task != "tracking" and len(horizons) != 1:
        raise ValueError("score one classification horizon per slot")
    report = summarize(rows, families)
    report.update(
        schema_version="bullet-time.score.v1",
        split=split,
        provenance={
            **provenance,
            "expected_sha256": digest(Path(expected_path).read_bytes()),
            "labels_sha256": digest(Path(labels_path).read_bytes()),
            "groups_sha256": digest(Path(groups_path).read_bytes()),
        },
        predictor={k: next(iter(expected.values()))[k] for k in KEY[:5]},
        horizon="tracking" if task == "tracking" else next(iter(horizons)),
        rows=rows,
        scientific_gate_pass=False,
    )
    return report
