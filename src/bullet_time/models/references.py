"""Untrained/external reference checkpoints with the same downstream source binding."""

from dataclasses import asdict
from pathlib import Path
import torch
from bullet_time.provenance import atomic_json, digest, identity
from .video import build_model, model_identity


def save_reference(model, path, *, seed=17, cache=None):
    from .external import lock

    path = Path(path)
    if path.exists() or Path(str(path) + ".json").exists():
        raise ValueError("reference output already exists")
    kind = getattr(model, "bt_kind", "videomae")
    binding = {
        "model": asdict(model.bt_config),
        "training": {"seed": seed},
        "reference_kind": kind,
        "reference_status": "external_pretrained" if kind == "dinov2" else "untrained",
    }
    if kind == "dinov2":
        binding["external_lock"] = lock()
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema_version": "bullet-time.reference.v1",
        "binding": binding,
        "global_step": 0,
        "model": model.state_dict(),
    }
    with path.open("xb") as file:
        torch.save(payload, file)
    atomic_json(
        str(path) + ".json",
        {
            "sha256": digest(path.read_bytes()),
            "model_sha256": model_identity(model),
            "binding_sha256": identity(binding),
        },
    )
    return {
        "checkpoint": str(path.resolve()),
        "binding_sha256": identity(binding),
        "reference_kind": kind,
    }


def rebuild_backbone(config, seed, *, kind="videomae", cache=None):
    if kind == "dinov2":
        from .external import build_dino, ImageConfig

        if config != asdict(ImageConfig()):
            raise ValueError("external model geometry mismatch")
        if cache is None:
            raise ValueError("DINOv2 requires --external-cache with its verified source archive")
        return build_dino(cache)
    if kind != "videomae":
        raise ValueError("unknown backbone kind")
    from .video import ModelConfig

    return build_model(ModelConfig(**config), seed)
