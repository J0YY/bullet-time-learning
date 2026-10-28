"""Consumer checks for grouped labels and paired diagnostic inputs; no split creation."""

from collections import Counter, defaultdict
from pathlib import Path
import copy
from bullet_time.provenance import strict_json, fields, text_id, digest, identity, integer


class Groups:
    def __init__(self, path):
        self.path = Path(path)
        self.sha256 = digest(self.path.read_bytes())
        data = strict_json(self.path.read_bytes())
        fields(data, {"schema_version", "records"})
        if data["schema_version"] != "bullet-time.evaluation-groups.v1":
            raise ValueError("unsupported grouping format")
        self.records = {}
        splits = {}
        episode_splits = {}
        for row in data["records"]:
            fields(row, {"episode_id", "task_id", "group_id", "split"})
            for name in ("episode_id", "group_id"):
                text_id(row[name], name)
            if row["task_id"] not in ("collision", "order", "tracking") or row["split"] not in (
                "train",
                "dev",
                "assessment",
            ):
                raise ValueError("invalid game task/split")
            key = (row["task_id"], row["episode_id"])
            if key in self.records:
                raise ValueError("duplicate grouped episode")
            if row["group_id"] in splits and splits[row["group_id"]] != row["split"]:
                raise ValueError("related group crosses splits")
            if (
                row["episode_id"] in episode_splits
                and episode_splits[row["episode_id"]] != row["split"]
            ):
                raise ValueError("episode crosses splits")
            splits[row["group_id"]] = row["split"]
            episode_splits[row["episode_id"]] = row["split"]
            self.records[key] = row
        if not self.records:
            raise ValueError("empty grouping inventory")

    def validate_inputs(self, inputs, task):
        examples = [e for e in inputs.examples if e.task_id == task]
        included_splits = {e.split for e in examples}
        expected = {
            key[1]
            for key, row in self.records.items()
            if key[0] == task and row["split"] in included_splits
        }
        if expected != {e.episode_id for e in examples}:
            raise ValueError("input does not cover the declared grouped episodes")
        grouped = defaultdict(set)
        for e in examples:
            row = self.records[(task, e.episode_id)]
            if row["split"] != e.split:
                raise ValueError("input/group split mismatch")
            grouped[row["group_id"]].add(e.episode_id)
        expected_size = 1 if task == "tracking" else 2
        if any(len(ids) != expected_size for ids in grouped.values()):
            raise ValueError(
                "group size differs from pilot episode/pair units; version or regenerate"
            )
        return grouped


def select_game_labels(inputs, groups, task, budget):
    integer(budget, "label_budget", 1)
    groups.validate_inputs(inputs, task)
    unit = 1 if task == "tracking" else 2
    if budget % unit:
        raise ValueError("budget splits a counterpart pair")
    train_groups = defaultdict(set)
    for e in inputs.examples:
        if e.task_id == task and e.split == "train":
            train_groups[groups.records[(task, e.episode_id)]["group_id"]].add(e.episode_id)
    ordered = sorted(
        train_groups,
        key=lambda group: (digest(f"bt-game-label-v1:20261028:{group}".encode()), group),
    )
    if budget > sum(map(len, train_groups.values())):
        raise ValueError("label budget exceeds available episodes")
    selected = set().union(*(train_groups[g] for g in ordered[: budget // unit]))
    view = copy.copy(inputs)
    view.examples = [
        e
        for e in inputs.examples
        if e.task_id == task and (e.split != "train" or e.episode_id in selected)
    ]
    view.selection = {
        "label_budget": budget,
        "episode_ids": sorted(selected),
        "group_sha256": groups.sha256,
        "selection_sha256": identity(sorted(selected)),
        "source_inputs_sha256": inputs.sha256,
    }
    return view


def verify_pairs(inputs, targets, groups, task):
    if task not in ("collision", "order"):
        raise ValueError("paired test is collision/order only")
    grouped = groups.validate_inputs(inputs, task)
    examples = defaultdict(dict)
    image_fingerprints = {}

    def fingerprint(image_id):
        if image_id not in image_fingerprints:
            inputs.store.read(image_id)  # checks actual immutable file and decoded pixels
            row = inputs.store.images[image_id]
            image_fingerprints[image_id] = (row["rgb_sha256"], row["height"], row["width"])
        return image_fingerprints[image_id]

    for e in inputs.examples:
        if e.task_id == task:
            examples[e.episode_id][(e.query_id, e.horizon_seconds)] = e
    comparisons = 0
    for pair in grouped.values():
        a, b = sorted(pair)
        if examples[a].keys() != examples[b].keys():
            raise ValueError("counterparts have different query/horizon inventories")
        if not any(horizon == 0.5 for _, horizon in examples[a]):
            raise ValueError("missing primary half-second pair")
        for key, left in examples[a].items():
            right = examples[b][key]
            if left.query_points != right.query_points or fingerprint(
                left.observed_image_ids[-1]
            ) != fingerprint(right.observed_image_ids[-1]):
                raise ValueError("pair leaks branch through final RGB or query side information")
            if left.horizon_seconds == 0.5 and {
                targets.get(left)["contact"],
                targets.get(right)["contact"],
            } != {0, 1}:
                raise ValueError("primary pair must have opposite contact labels")
            if task == "order" and Counter(map(fingerprint, left.observed_image_ids)) != Counter(
                map(fingerprint, right.observed_image_ids)
            ):
                raise ValueError("order diagnostic image multisets differ")
            comparisons += 1
    return {
        "pairs": len(grouped),
        "query_horizon_comparisons": comparisons,
        "group_sha256": groups.sha256,
        "scope": "pixel/query/label checks only; forward dynamics and visual solvability require S3 and models",
    }
