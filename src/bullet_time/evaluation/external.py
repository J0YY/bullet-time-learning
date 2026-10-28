"""SSv2 consumer-side deterministic development/label split and RGB adapter."""

from collections import defaultdict
import math
from bullet_time.provenance import digest, fields, integer, identity
from bullet_time.evaluation.inputs import uniform_frame_indices, letterbox, normalize
import torch


def ssv2_partitions(rows):
    by_class = defaultdict(list)
    seen = set()
    for row in rows:
        fields(row, {"video_id", "class_id", "official_split"})
        if row["official_split"] != "train":
            raise ValueError("only official training may enter pilot development")
        identifier = row["video_id"]
        if (
            not isinstance(identifier, str)
            or not identifier.isascii()
            or not identifier.isdecimal()
            or str(int(identifier)) != identifier
        ):
            raise ValueError("video ID must be canonical decimal string")
        integer(row["class_id"], "class_id")
        if row["class_id"] >= 174 or identifier in seen:
            raise ValueError("class out of range or duplicate video")
        seen.add(identifier)
        by_class[row["class_id"]].append(identifier)
    if not by_class:
        raise ValueError("empty SSv2 metadata")
    train = []
    dev = []
    labels = []

    def order(namespace, ids):
        return sorted(
            ids,
            key=lambda identifier: (
                digest(f"{namespace}:20261028:{identifier}".encode()),
                int(identifier),
            ),
        )

    for class_id, ids in sorted(by_class.items()):
        if len(ids) < 2:
            raise ValueError("each class needs train and dev examples")
        ordered = order("bt-ssv2-dev-v1", ids)
        n = max(1, math.floor(0.1 * len(ids)))
        development = ordered[:n]
        training = ordered[n:]
        selected = order("bt-ssv2-label-v1", training)[: max(1, math.floor(0.1 * len(training)))]
        dev.extend(development)
        train.extend(training)
        labels.extend(selected)
    result = {
        "schema_version": "bullet-time.ssv2-partitions.v1",
        "source": "official_train_only",
        "train": sorted(train, key=int),
        "dev": sorted(dev, key=int),
        "train_10pct": sorted(labels, key=int),
        "group_audit": "pending; not a final split freeze",
    }
    result["partition_sha256"] = identity(result)
    return result


def validate_external_groups(partitions, group_by_video):
    fields(
        partitions,
        {
            "schema_version",
            "source",
            "train",
            "dev",
            "train_10pct",
            "group_audit",
            "partition_sha256",
        },
    )
    if (
        partitions["schema_version"] != "bullet-time.ssv2-partitions.v1"
        or partitions["source"] != "official_train_only"
        or identity({k: v for k, v in partitions.items() if k != "partition_sha256"})
        != partitions["partition_sha256"]
    ):
        raise ValueError("invalid partition provenance")
    for name in ("train", "dev", "train_10pct"):
        if len(partitions[name]) != len(set(partitions[name])):
            raise ValueError("duplicate partition ID")
    if set(partitions["train"]) & set(partitions["dev"]) or not set(
        partitions["train_10pct"]
    ) <= set(partitions["train"]):
        raise ValueError("invalid partition separation/subset")
    if any(not isinstance(g, str) or not g for g in group_by_video.values()):
        raise ValueError("invalid external group ID")
    if set(group_by_video) != set(partitions["train"]) | set(partitions["dev"]):
        raise ValueError("group audit must cover every video")
    roles = {}
    for role, ids in [("dev", partitions["dev"]), ("train", partitions["train"])]:
        for identifier in ids:
            group = group_by_video[identifier]
            if group in roles and roles[group] != role:
                raise ValueError("related videos cross train/dev; S split revision needed")
            roles[group] = role
    labels = set(partitions["train_10pct"])
    members = defaultdict(set)
    for identifier in partitions["train"]:
        members[group_by_video[identifier]].add(identifier)
    if any(group & labels and not group <= labels for group in members.values()):
        raise ValueError("low-label subset splits a related group; S split revision needed")
    return {
        "group_sha256": identity(group_by_video),
        "partition_sha256": partitions["partition_sha256"],
        "passed": True,
    }


def assemble_action_clip(frames, size=224):
    if not frames:
        raise ValueError("empty decoded video")
    indices = uniform_frame_indices(len(frames))
    return normalize(torch.stack([letterbox(frames[i], size)[0] for i in indices], 1)), indices
