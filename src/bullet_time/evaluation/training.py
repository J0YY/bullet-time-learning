"""Frozen-head/diagnostic fitting with explicit split access and target join."""

from dataclasses import dataclass, asdict
from pathlib import Path
import random
import torch
from torch.nn import functional as F
from bullet_time.provenance import strict_json, fields, integer, number, identity, digest, seed_for
from bullet_time.evaluation.inputs import point
from bullet_time.models.video import seeded_rng, model_identity


class Targets:
    """Labels never enter assembler/model features. All joins must have complete keys."""

    def __init__(self, path, inputs, *, allowed_splits=("train", "dev"), classes=174):
        self.path = Path(path)
        self.sha256 = digest(self.path.read_bytes())
        self.rows = {}
        examples = {(e.task_id, *e.key): e for e in inputs.examples if e.split in allowed_splits}
        required = {
            "schema_version",
            "task_id",
            "episode_id",
            "query_id",
            "horizon_or_frame",
            "split",
            "target",
        }
        for line in self.path.read_bytes().splitlines():
            row = strict_json(line)
            fields(row, required)
            if (
                row["schema_version"] != "bullet-time.labels.v1"
                or row["split"] not in allowed_splits
            ):
                raise ValueError("unsupported/inaccessible target")
            key = (row["task_id"], row["episode_id"], row["query_id"], str(row["horizon_or_frame"]))
            if key in self.rows or key not in examples:
                raise ValueError("duplicate or unmatched target")
            example = examples[key]
            if row["split"] != example.split:
                raise ValueError("input/target split mismatch")
            target = row["target"]
            if row["task_id"] in ("collision", "order"):
                fields(target, {"contact"})
                if type(target["contact"]) is not int or target["contact"] not in (0, 1):
                    raise ValueError("contact must be 0 or 1")
            elif row["task_id"] == "ssv2":
                fields(target, {"class_id"})
                integer(target["class_id"], "class_id")
                if target["class_id"] >= classes:
                    raise ValueError("class out of range")
            else:
                fields(target, {"x", "y", "visible", "bbox_diagonal_pixels", "prediction_role"})
                point([target["x"], target["y"]])
                number(target["bbox_diagonal_pixels"], "bbox_diagonal_pixels", 0)
                if type(target["visible"]) is not int or target["visible"] not in (0, 1):
                    raise ValueError("visibility must be binary")
                if target["prediction_role"] != example.prediction_role:
                    raise ValueError("prediction role mismatch")
                if example.prediction_role == "primary" and target["visible"] != 1:
                    raise ValueError("primary reacquisition frames must be visible")
            self.rows[key] = row
        if self.rows.keys() != examples.keys():
            raise ValueError("missing targets for declared examples")

    def get(self, example):
        return self.rows[(example.task_id, *example.key)]["target"]

    def reference_hash(self, example):
        return identity(self.rows[(example.task_id, *example.key)])


@dataclass(frozen=True)
class ReadoutConfig:
    task: str = "collision"
    seed: int = 101
    epochs: int = 20
    batch_size: int = 8
    learning_rate: float = 0.001
    weight_decay: float = 0.01
    image_size: int = 224
    mode: str = "sequence"
    device: str = "cpu"
    kind: str = "frozen"
    width: int = 256
    depth: int = 2
    heads: int = 4
    classes: int = 174
    label_budget: int | None = None
    horizon_seconds: float = 0.5

    def validate(self):
        if self.task not in ("collision", "order", "tracking", "ssv2"):
            raise ValueError("invalid task")
        if self.mode not in ("sequence", "final_frame", "bag", "current_frame"):
            raise ValueError("invalid mode")
        for key in ("epochs", "batch_size", "image_size", "width", "depth", "heads", "classes"):
            integer(getattr(self, key), key, 1)
        if self.label_budget is not None:
            integer(self.label_budget, "label_budget", 1)
        if self.horizon_seconds not in (0.25, 0.5, 1.0) or type(self.horizon_seconds) not in (
            float,
            int,
        ):
            raise ValueError("unsupported readout horizon")
        if self.kind not in ("frozen", "diagnostic") or self.width % self.heads:
            raise ValueError("invalid head configuration")
        if self.kind == "frozen" and self.mode != "sequence":
            raise ValueError("restricted controls are supervised diagnostics")
        integer(self.seed, "seed")
        number(self.learning_rate, "learning_rate", 1e-12)
        number(self.weight_decay, "weight_decay", 0)
        if torch.device(self.device).type not in ("cpu", "cuda"):
            raise ValueError("unsupported device")


def feature_batch(inputs, examples, config):
    rows = [inputs.assemble(e, size=config.image_size, mode=config.mode) for e in examples]
    return {
        key: None
        if rows[0][key] is None
        else torch.stack([row[key] for row in rows]).to(config.device)
        for key in rows[0]
    }


def loss_per_example(logits, examples, targets):
    task = examples[0].task_id
    rows = [targets.get(e) for e in examples]
    if task in ("collision", "order"):
        y = logits.new_tensor([r["contact"] for r in rows])
        return F.binary_cross_entropy_with_logits(logits[:, 0], y, reduction="none")
    if task == "ssv2":
        y = torch.tensor([r["class_id"] for r in rows], dtype=torch.long, device=logits.device)
        return F.cross_entropy(logits, y, reduction="none")
    xy = logits.new_tensor([[r["x"], r["y"]] for r in rows])
    visible = logits.new_tensor([r["visible"] for r in rows])
    # Do not train hidden-point coordinates as if they were visible evidence.
    position = (logits[:, :2].sigmoid() - xy).square().mean(1) * visible
    return position + F.binary_cross_entropy_with_logits(logits[:, 2], visible, reduction="none")


def fit(model, inputs, targets, config):
    """Fit only on train; select checkpoint only by dev loss. No assessment labels."""
    config.validate()
    from bullet_time.models.runtime import configure_runtime

    configure_runtime(config.device)
    selected = task_examples(inputs, config)
    if any(e.split not in ("train", "dev") for e in selected):
        raise ValueError("assessment/final input is inaccessible to fitting")
    train = [e for e in selected if e.split == "train"]
    dev = [e for e in selected if e.split == "dev"]
    if not train or not dev:
        raise ValueError("separate train and dev inputs required")
    if (
        config.label_budget is not None
        and len({e.episode_id for e in train}) != config.label_budget
    ):
        raise ValueError("actual training episode count differs from declared label budget")
    train_episodes = {e.episode_id for e in train}
    dev_episodes = {e.episode_id for e in dev}
    if train_episodes & dev_episodes:
        raise ValueError("episode leakage across train/dev")
    if config.task == "tracking":
        for split in (train, dev):
            if {targets.get(e)["visible"] for e in split} != {0, 1}:
                raise ValueError("visibility fitting needs visible and occluded auxiliary examples")
    if config.task == "ssv2":
        for examples in (train, dev):
            if {targets.get(e)["class_id"] for e in examples} != set(range(config.classes)):
                raise ValueError("SSv2 split lacks declared class coverage")
    model = model.to(config.device)
    frozen_module = (
        model.backbone
        if hasattr(model, "backbone")
        else model.encoder
        if config.kind == "frozen"
        else None
    )
    frozen_before = model_identity(frozen_module) if frozen_module is not None else None
    optimizer = torch.optim.AdamW(
        [p for p in model.parameters() if p.requires_grad],
        lr=config.learning_rate,
        weight_decay=config.weight_decay,
    )
    best = float("inf")
    best_state = None
    history = []
    # Each episode gets equal weight even with different numbers of tracking windows.
    weights = {}
    for split in (train, dev):
        counts = {
            e.episode_id: sum(other.episode_id == e.episode_id for other in split) for e in split
        }
        weights.update({(e.split, *e.key): 1 / counts[e.episode_id] for e in split})
    for epoch in range(config.epochs):
        ordered = train.copy()
        random.Random(seed_for(config.seed, "readout-order", epoch)).shuffle(ordered)
        model.train()
        train_loss = 0.0
        for offset in range(0, len(ordered), config.batch_size):
            examples = ordered[offset : offset + config.batch_size]
            features = feature_batch(inputs, examples, config)
            optimizer.zero_grad(set_to_none=True)
            with seeded_rng(seed_for(config.seed, "readout-dropout", epoch, offset), config.device):
                logits = model(**features)
                losses = loss_per_example(logits, examples, targets)
                w = losses.new_tensor([weights[(e.split, *e.key)] for e in examples])
                # Scale by the expected mean window weight; do not upweight short tail batches.
                denominator = config.batch_size * len(train_episodes) / len(train)
                loss = (losses * w).sum() / denominator
                if not torch.isfinite(loss):
                    raise ValueError("nonfinite readout loss")
                loss.backward()
            if not all(
                torch.isfinite(p.grad).all() for p in model.parameters() if p.grad is not None
            ):
                raise ValueError("nonfinite readout gradients")
            optimizer.step()
            train_loss += float((losses.detach() * w).sum().cpu())
        model.eval()
        dev_loss = 0.0
        with torch.no_grad():
            for offset in range(0, len(dev), config.batch_size):
                examples = dev[offset : offset + config.batch_size]
                losses = loss_per_example(
                    model(**feature_batch(inputs, examples, config)), examples, targets
                )
                w = losses.new_tensor([weights[(e.split, *e.key)] for e in examples])
                dev_loss += float((losses * w).sum().cpu())
        dev_loss /= len(dev_episodes)
        history.append(
            {"epoch": epoch, "train_loss": train_loss / len(train_episodes), "dev_loss": dev_loss}
        )
        if dev_loss < best:
            best = dev_loss
            best_state = {k: v.detach().cpu().clone() for k, v in model.state_dict().items()}
    if best_state is None:
        raise ValueError("no valid development checkpoint")
    model.load_state_dict(best_state)
    if frozen_before is not None and model_identity(frozen_module) != frozen_before:
        raise ValueError("frozen backbone changed during readout fit")
    return {
        "config": asdict(config),
        "history": history,
        "selected_dev_loss": best,
        "input_sha256": inputs.sha256,
        "image_manifest_sha256": inputs.store.manifest_sha256,
        "label_sha256": targets.sha256,
        "train_episodes": len(train_episodes),
        "dev_episodes": len(dev_episodes),
        "frozen_backbone_sha256": frozen_before,
        "model_sha256": model_identity(model),
        "training_episode_ids": sorted(train_episodes),
        "selection": getattr(inputs, "selection", None),
        "horizon_seconds": config.horizon_seconds
        if config.task in ("collision", "order")
        else None,
    }


def predict(model, inputs, config):
    config.validate()
    from bullet_time.models.runtime import configure_runtime

    configure_runtime(config.device)
    model.to(config.device).eval()
    output = []
    examples = task_examples(inputs, config)
    with torch.no_grad():
        for offset in range(0, len(examples), config.batch_size):
            group = examples[offset : offset + config.batch_size]
            logits = model(**feature_batch(inputs, group, config))
            if not torch.isfinite(logits).all():
                raise ValueError("nonfinite predictions")
            values = logits.sigmoid() if config.task != "ssv2" else logits.softmax(-1)
            for e, value in zip(group, values.cpu().tolist()):
                output.append((e, value))
    return output


def build_readout(backbone, config):
    from .heads import FrozenReadout, FrozenFrameReadout, DiagnosticModel, FrameEncoder

    config.validate()
    kwargs = dict(
        width=config.width, depth=config.depth, heads=config.heads, classes=config.classes
    )
    with seeded_rng(seed_for(config.seed, "readout-initialization")):
        if config.kind == "diagnostic":
            return DiagnosticModel(FrameEncoder(backbone), config.task, config.mode, **kwargs)
        if backbone.bt_config.frames == 1:
            return FrozenFrameReadout(FrameEncoder(backbone), config.task, **kwargs)
        return FrozenReadout(backbone, config.task, **kwargs)


def task_examples(inputs, config):
    # Separate heads per physical horizon: timing never becomes an undeclared feature,
    # and contradictory labels at different horizons never train one unconditioned head.
    return [
        e
        for e in inputs.examples
        if e.task_id == config.task
        and (
            config.task not in ("collision", "order") or e.horizon_seconds == config.horizon_seconds
        )
    ]
