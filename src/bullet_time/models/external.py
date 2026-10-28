"""Official DINOv2 code/weights with fixed hashes and an explicit setup command."""

from dataclasses import dataclass
import importlib
import os
from pathlib import Path
import sys
import urllib.request
import zipfile
import torch
from torch import nn
from bullet_time.provenance import digest, strict_json
from .video import seeded_rng


@dataclass(frozen=True)
class ImageConfig:
    image_size: int = 224
    patch_size: int = 14
    encoder_width: int = 384
    frames: int = 1
    tubelet: int = 1


def lock():
    return strict_json((Path(__file__).parent / "pins/dinov2.json").read_bytes())


def fetch_verified(url, path, expected):
    if not path.exists():
        # Never execute newly downloaded code before checking the committed checksum.
        temporary = path.with_suffix(path.suffix + ".download")
        try:
            urllib.request.urlretrieve(url, temporary)
            if digest(temporary.read_bytes()) != expected:
                raise ValueError("download checksum mismatch")
            temporary.replace(path)
        finally:
            temporary.unlink(missing_ok=True)
    if digest(path.read_bytes()) != expected:
        raise ValueError("cached external artifact checksum mismatch")


def source_root(cache, *, download=False):
    cache = Path(cache).resolve()
    spec = lock()
    archive = cache / "source.zip"
    if download:
        cache.mkdir(parents=True, exist_ok=True)
        fetch_verified(spec["archive_url"], archive, spec["archive_sha256"])
    if not archive.exists() or digest(archive.read_bytes()) != spec["archive_sha256"]:
        raise ValueError("verified DINOv2 source archive missing; run prepare-dinov2")
    root = cache / ("dinov2-" + spec["revision"])
    # Verify extracted contents on every use, including an existing cache. Extract
    # only absent files; refuse changed files instead of silently replacing them.
    with zipfile.ZipFile(archive) as bundle:
        for member in bundle.infolist():
            if member.is_dir():
                continue
            destination = (cache / member.filename).resolve()
            if not destination.is_relative_to(root):
                raise ValueError("unsafe source archive member")
            contents = bundle.read(member)
            if destination.exists():
                if destination.read_bytes() != contents:
                    raise ValueError("extracted external source changed")
            else:
                destination.parent.mkdir(parents=True, exist_ok=True)
                destination.write_bytes(contents)
    return root


class PatchEncoder(nn.Module):
    def __init__(self, model):
        super().__init__()
        self.model = model

    def forward(self, video, mask):
        if bool(mask.any()):
            raise ValueError("external reference only supports all-visible features")
        return self.model.forward_features(video[:, :, 0])["x_norm_patchtokens"]


class DinoAdapter(nn.Module):
    def __init__(self, model):
        super().__init__()
        self.encoder = PatchEncoder(model)
        self.bt_config = ImageConfig()
        self.bt_kind = "dinov2"


def build_dino(cache, *, pretrained=False, download=False):
    root = source_root(cache, download=download)
    for name, module in list(sys.modules.items()):
        if name == "dinov2" or name.startswith("dinov2."):
            origin = getattr(module, "__file__", None)
            if origin and not Path(origin).resolve().is_relative_to(root):
                raise ValueError("another DINOv2 source is already loaded; use a fresh process")
    # Keep CPU/CUDA on the same torch attention implementation, independent of an
    # optional xformers installation. Must be set before importing upstream code.
    os.environ["XFORMERS_DISABLED"] = "1"
    sys.path.insert(0, str(root))
    try:
        module = importlib.import_module("dinov2.hub.backbones")
        with seeded_rng(0):
            model = module.dinov2_vits14(pretrained=False)
    finally:
        sys.path.remove(str(root))
    if pretrained:
        spec = lock()
        weights = Path(cache) / "weights.pth"
        if download:
            fetch_verified(spec["weights_url"], weights, spec["weights_sha256"])
        if not weights.exists() or digest(weights.read_bytes()) != spec["weights_sha256"]:
            raise ValueError("verified DINOv2 weights missing; run prepare-dinov2")
        model.load_state_dict(
            torch.load(weights, map_location="cpu", weights_only=True), strict=True
        )
    return DinoAdapter(model)
