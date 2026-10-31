"""Complete-grid VideoMAE optimizer, resumable only at completed update boundaries."""

from dataclasses import dataclass, asdict
from pathlib import Path
import math
import os
import platform
import importlib.metadata
import tempfile
import time
import torch
from bullet_time.provenance import (
    atomic_json,
    digest,
    identity,
    integer,
    number,
    strict_json,
    seed_for,
)
from bullet_time.loading.schedule import CONDITIONS, construct, family_ranks, updates
from bullet_time.loading.batch import (
    sample_transform,
    transform_grid,
    collate,
    collate_images,
    audit_batch,
)
from bullet_time.models.video import build_model, model_identity, seeded_rng
from bullet_time.models.runtime import validate_device, device_name, mps_runtime


@dataclass(frozen=True)
class TrainConfig:
    condition: str = "view"
    seed: int = 17
    recipe: str = "controlled"
    total_passes: int = 20
    grids_per_update: int = 8
    microbatch_clips: int = 2
    mask_ratio: float = 0.9
    learning_rate: float = 0.000075
    warmup_learning_rate: float = 0.0000005
    minimum_learning_rate: float = 0.000005
    warmup_passes: int = 2
    weight_decay: float = 0.05
    beta1: float = 0.9
    beta2: float = 0.95
    epsilon: float = 1e-8
    grad_clip: float = 0.0
    crop_fraction: float = 1.0
    color_jitter: float = 0.0
    device: str = "cpu"

    def validate(self):
        if self.condition not in CONDITIONS or self.recipe not in ("controlled", "native"):
            raise ValueError("invalid condition/recipe")
        for key in ("seed", "warmup_passes"):
            integer(getattr(self, key), key)
        for key in ("total_passes", "grids_per_update", "microbatch_clips"):
            integer(getattr(self, key), key, 1)
        if self.microbatch_clips > 16 or self.warmup_passes >= self.total_passes:
            raise ValueError("invalid microbatch or warmup")
        for key in ("learning_rate", "warmup_learning_rate", "minimum_learning_rate", "epsilon"):
            number(getattr(self, key), key, 1e-12)
        for key in ("beta1", "beta2", "mask_ratio"):
            number(getattr(self, key), key, 1e-6, 1 - 1e-6)
        number(self.weight_decay, "weight_decay", 0)
        number(self.grad_clip, "grad_clip", 0)
        number(self.crop_fraction, "crop_fraction", 0.25, 1)
        number(self.color_jitter, "color_jitter", 0, 0.5)
        validate_device(self.device)


def code_identity(root=None):
    root = Path(root) if root is not None else Path(__file__).resolve().parents[1]
    # Producer/independent-analysis code is not imported by this consumer. Its
    # parallel development must not invalidate Joy's in-flight runs or checkpoints.
    independent_roots = {"generation", "rendering", "splits", "analysis"}
    independent_files = {
        "schema.py",
        "evaluation/metrics.py",
        "evaluation/scoring.py",
        "evaluation/statistics.py",
        "evaluation/score_plan.py",
        "evaluation/assessment_policy.py",
        "evaluation/assessment_state.py",
        "evaluation/assessment_contract.py",
        "evaluation/assessment_inputs.py",
        "evaluation/job_evidence.py",
    }
    records = {}
    for path in sorted(root.rglob("*")):
        relative = path.relative_to(root)
        if relative.parts[0] in independent_roots or relative.as_posix() in independent_files:
            continue
        if path.suffix == ".py" or path.suffix == ".json" and relative.parts[0] == "models":
            records[relative.as_posix()] = digest(path.read_bytes())
    return identity(records)


def learning_rate(config, step, steps_per_pass):
    warmup = config.warmup_passes * steps_per_pass
    total = config.total_passes * steps_per_pass
    if not 0 <= step < total:
        raise ValueError("scheduler step outside fixed budget")
    if step < warmup:
        return config.warmup_learning_rate + (
            config.learning_rate - config.warmup_learning_rate
        ) * step / max(1, warmup - 1)
    progress = (step - warmup) / max(1, total - warmup - 1)
    return (
        config.minimum_learning_rate
        + (config.learning_rate - config.minimum_learning_rate)
        * (1 + math.cos(math.pi * progress))
        / 2
    )


class Runner:
    def __init__(self, corpus, model_config, train_config, *, verify_bytes=True):
        train_config.validate()
        model_config.validate()
        if model_config.image_size != corpus.image_size:
            raise ValueError("model/corpus image geometry differs")
        if model_config.frames == 1 and (
            train_config.condition != "view" or train_config.recipe != "controlled"
        ):
            raise ValueError("framewise reference has no regrouping condition/native video recipe")
        if train_config.recipe == "native" and (
            train_config.crop_fraction != 1 or train_config.color_jitter != 0
        ):
            raise ValueError(
                "native reference uses its released per-clip crop, without extra grid transforms"
            )
        if verify_bytes:
            corpus.verify()
        self.corpus = corpus
        self.model_config = model_config
        self.config = train_config
        from bullet_time.models.runtime import configure_runtime

        self.device = configure_runtime(train_config.device)
        self.model = build_model(model_config, train_config.seed).to(self.device)
        self.initialization_sha256 = model_identity(self.model)
        decay = []
        no_decay = []
        for name, param in self.model.named_parameters():
            (
                no_decay
                if param.ndim <= 1 or name.endswith(".bias") or name == "mask_token"
                else decay
            ).append(param)
        self.optimizer = torch.optim.AdamW(
            [
                {"params": decay, "weight_decay": train_config.weight_decay},
                {"params": no_decay, "weight_decay": 0.0},
            ],
            lr=train_config.learning_rate,
            betas=(train_config.beta1, train_config.beta2),
            eps=train_config.epsilon,
        )
        self.steps_per_pass = math.ceil(len(corpus.grids) / train_config.grids_per_update)
        self.total_steps = self.steps_per_pass * train_config.total_passes
        self.global_step = 0
        self.binding = {
            "model": asdict(model_config),
            "training": asdict(train_config),
            "corpus_sha256": corpus.manifest_sha256,
            "corpus_grids": len(corpus.grids),
            "source_sha256": code_identity(),
            "torch_version": str(torch.__version__),
            "numpy_version": __import__("numpy").__version__,
            "python_version": platform.python_version(),
            "initialization_sha256": self.initialization_sha256,
            "pillow_version": importlib.metadata.version("Pillow"),
            "timm_version": importlib.metadata.version("timm"),
            "machine": platform.machine(),
            "system": platform.system(),
            "threads": torch.get_num_threads(),
            "device_name": device_name(self.device),
            **({"mps_runtime": mps_runtime()} if self.device.type == "mps" else {}),
            "deterministic_algorithms": torch.are_deterministic_algorithms_enabled(),
            "precision": "float32",
        }
        self.binding_sha256 = identity(self.binding)

    def step(self, *, detailed_audit=False):
        if self.global_step >= self.total_steps:
            raise ValueError("fixed run budget exhausted")
        if (
            code_identity() != self.binding["source_sha256"]
            or digest(self.corpus.manifest.read_bytes()) != self.corpus.manifest_sha256
        ):
            raise ValueError("code or manifest changed during the run")
        cfg = self.config
        mc = self.model_config
        step = self.global_step
        pass_index, update_index = divmod(step, self.steps_per_pass)
        group = updates(self.corpus.grids, cfg.seed, pass_index, cfg.grids_per_update)[update_index]
        ranks = family_ranks(self.corpus.grids, cfg.seed, pass_index)
        spatial = (mc.image_size // mc.patch_size) ** 2
        sequences_per_grid = 256 if mc.frames == 1 else 16
        target_values = (
            len(group)
            * sequences_per_grid
            * (mc.frames // mc.tubelet)
            * int(cfg.mask_ratio * spatial)
            * (3 * mc.tubelet * mc.patch_size**2)
        )
        if not target_values:
            raise ValueError("empty target set")
        lr = learning_rate(cfg, step, self.steps_per_pass)
        for params in self.optimizer.param_groups:
            params["lr"] = lr
        self.model.train()
        self.optimizer.zero_grad(set_to_none=True)
        start = time.perf_counter()
        loss_sum = 0.0
        seen_values = 0
        audits = {}
        summaries = {}
        microbatch_index = 0
        try:
            for grid in group:
                schedule = construct(grid, cfg.condition, pass_index, cfg.seed, ranks[grid.grid_id])
                tr = sample_transform(
                    mc.image_size,
                    cfg.seed,
                    grid.grid_id,
                    pass_index,
                    cfg.crop_fraction,
                    cfg.color_jitter,
                )
                pixels = transform_grid(self.corpus.read_grid(grid), tr)
                records = {}
                native_crops = {}
                for begin in range(0, sequences_per_grid, cfg.microbatch_clips):
                    indices = list(
                        range(begin, min(begin + cfg.microbatch_clips, sequences_per_grid))
                    )
                    if mc.frames == 1:
                        batch = collate_images(
                            grid,
                            pixels,
                            indices,
                            patch_size=mc.patch_size,
                            mask_ratio=cfg.mask_ratio,
                            seed=cfg.seed,
                            pass_index=pass_index,
                        )
                    else:
                        batch = collate(
                            grid,
                            pixels,
                            schedule,
                            indices,
                            patch_size=mc.patch_size,
                            mask_ratio=cfg.mask_ratio,
                            seed=cfg.seed,
                            recipe=cfg.recipe,
                            tubelet=mc.tubelet,
                        )
                    native_crops.update(batch.native_crops or {})
                    actual = audit_batch(batch)
                    if records.keys() & actual.keys():
                        raise ValueError("duplicate actual exposure")
                    records.update(actual)
                    labels = batch.labels.to(self.device)
                    inputs = batch.inputs.to(self.device)
                    mask = batch.mask.to(self.device)
                    with seeded_rng(
                        seed_for(cfg.seed, "dropout", step, microbatch_index), self.device
                    ):
                        output = self.model(inputs, mask)
                        if output.shape != labels.shape:
                            raise ValueError("decoder/target shape mismatch")
                        numerator = (output - labels).square().sum()
                        if not torch.isfinite(numerator):
                            raise ValueError("nonfinite loss")
                        (numerator / target_values).backward()
                    loss_sum += float(numerator.detach().cpu())
                    seen_values += labels.numel()
                    microbatch_index += 1
                if set(records) != {cell.image_id for cell in grid.cells}:
                    raise ValueError("actual loader exposure is not a complete grid")
                summaries[grid.grid_id] = {
                    "exposure_sha256": identity(records),
                    "images": len(records),
                    "orientation": schedule.orientation,
                    "direction": schedule.direction,
                    "phase": schedule.phase,
                    "transform": asdict(tr),
                    "native_clip_crops": native_crops,
                }
                if detailed_audit:
                    audits[grid.grid_id] = records
            if seen_values != target_values:
                raise ValueError("gradient denominator mismatch")
            parameters = [p for p in self.model.parameters() if p.grad is not None]
            if not parameters or not all(torch.isfinite(p.grad).all() for p in parameters):
                raise ValueError("missing or nonfinite gradients")
            grad_norm = torch.nn.utils.clip_grad_norm_(
                parameters, cfg.grad_clip if cfg.grad_clip else float("inf")
            )
            self.optimizer.step()
            if not all(torch.isfinite(p).all() for p in self.model.parameters()):
                raise ValueError("nonfinite parameters after update; reload last valid checkpoint")
            self.global_step += 1
        except BaseException:
            self.optimizer.zero_grad(set_to_none=True)
            raise
        return {
            "schema_version": "bullet-time.exposure.v1",
            "step": step,
            "pass_index": pass_index,
            "update_index": update_index,
            "grid_ids": [g.grid_id for g in group],
            "grids": summaries,
            "detailed_exposure": audits if detailed_audit else None,
            "clips": 16 * len(group) if mc.frames == 16 else 0,
            "sequences": sequences_per_grid * len(group),
            "frames_per_sequence": mc.frames,
            "images": 256 * len(group),
            "target_values": seen_values,
            "loss": loss_sum / seen_values,
            "learning_rate": lr,
            "gradient_norm": float(grad_norm),
            "seconds": time.perf_counter() - start,
            "optimizer_steps": self.global_step,
            "scheduler_steps": self.global_step,
            "teacher_steps": 0,
            "binding_sha256": self.binding_sha256,
        }

    def save(self, path):
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        if path.exists() or Path(str(path) + ".json").exists():
            raise ValueError("checkpoint path already exists")
        payload = {
            "schema_version": "bullet-time.checkpoint.v1",
            "binding": self.binding,
            "binding_sha256": self.binding_sha256,
            "global_step": self.global_step,
            "model": self.model.state_dict(),
            "optimizer": self.optimizer.state_dict(),
        }
        fd, tmp = tempfile.mkstemp(prefix=".checkpoint-", dir=path.parent)
        os.close(fd)
        try:
            with open(tmp, "wb") as file:
                torch.save(payload, file)
                file.flush()
                os.fsync(file.fileno())
            os.replace(tmp, path)
        finally:
            if os.path.exists(tmp):
                os.unlink(tmp)
        atomic_json(
            str(path) + ".json",
            {
                "sha256": digest(path.read_bytes()),
                "binding_sha256": self.binding_sha256,
                "global_step": self.global_step,
                "model_sha256": model_identity(self.model),
            },
        )

    def resume(self, path):
        path = Path(path)
        meta = strict_json(Path(str(path) + ".json").read_bytes())
        if digest(path.read_bytes()) != meta["sha256"]:
            raise ValueError("checkpoint byte hash mismatch")
        state = torch.load(path, map_location=self.device, weights_only=True)
        if (
            state["schema_version"] != "bullet-time.checkpoint.v1"
            or state["binding"] != self.binding
            or (
                state["binding_sha256"] != self.binding_sha256
                or meta["binding_sha256"] != self.binding_sha256
            )
        ):
            raise ValueError("resume binding differs: code/config/data/runtime/initialization")
        integer(state["global_step"], "global_step")
        if state["global_step"] > self.total_steps or state["global_step"] != meta["global_step"]:
            raise ValueError("checkpoint progress invalid")
        self.corpus.verify()
        self.model.load_state_dict(state["model"], strict=True)
        if model_identity(self.model) != meta["model_sha256"]:
            raise ValueError("model hash mismatch")
        self.optimizer.load_state_dict(state["optimizer"])
        self.global_step = state["global_step"]
