"""Validated wrapper around the pinned released VideoMAE computation."""

from contextlib import contextmanager
from dataclasses import dataclass, asdict
from functools import partial
from pathlib import Path
import torch
from torch import nn
from bullet_time.provenance import digest, integer, number, seed_for, strict_json, identity
from .videomae_upstream.modeling_pretrain import PretrainVisionTransformer
from .videomae_upstream.modeling_finetune import get_sinusoid_encoding_table


@dataclass(frozen=True)
class ModelConfig:
    image_size: int = 224
    patch_size: int = 16
    encoder_width: int = 384
    encoder_depth: int = 12
    encoder_heads: int = 6
    decoder_width: int = 192
    decoder_depth: int = 4
    decoder_heads: int = 3
    tubelet: int = 2
    frames: int = 16
    dropout: float = 0.0
    drop_path: float = 0.0

    def validate(self):
        for key, value in asdict(self).items():
            if key not in ("dropout", "drop_path"):
                integer(value, key, 1)
        for key in ("dropout", "drop_path"):
            number(getattr(self, key), key, 0, 0.5)
        if (
            self.image_size % self.patch_size
            or self.frames % self.tubelet
            or (self.encoder_width % self.encoder_heads or self.decoder_width % self.decoder_heads)
        ):
            raise ValueError("invalid transformer geometry")
        if self.frames not in (1, 16) or self.frames == 1 and self.tubelet != 1:
            raise ValueError("supported inputs are 16-frame video or framewise image-MAE")


@contextmanager
def seeded_rng(seed, device="cpu"):
    from .runtime import validate_device

    device = validate_device(device)
    if device.type == "mps":
        state = torch.mps.get_rng_state().clone()
        with torch.random.fork_rng(devices=[]):
            try:
                torch.random.default_generator.manual_seed(seed)
                torch.mps.manual_seed(seed)
                yield
            finally:
                torch.mps.set_rng_state(state)
        return
    devices = (
        []
        if device.type == "cpu"
        else [device.index if device.index is not None else torch.cuda.current_device()]
    )
    with torch.random.fork_rng(devices=devices):
        torch.random.default_generator.manual_seed(seed)
        if devices:
            with torch.cuda.device(devices[0]):
                torch.cuda.manual_seed(seed)
        yield


def verify_upstream():
    root = Path(__file__).parent / "videomae_upstream"
    record = strict_json((root / "upstream.json").read_bytes())
    for name, hashes in record["files"].items():
        if digest((root / name).read_bytes()) != hashes["vendored_sha256"]:
            raise ValueError("vendored model changed without provenance update")
    return record["revision"]


def build_model(config: ModelConfig, seed: int):
    config.validate()
    verify_upstream()
    with seeded_rng(seed_for(seed, "initialization")):
        model = PretrainVisionTransformer(
            img_size=config.image_size,
            patch_size=config.patch_size,
            encoder_embed_dim=config.encoder_width,
            encoder_depth=config.encoder_depth,
            encoder_num_heads=config.encoder_heads,
            decoder_embed_dim=config.decoder_width,
            decoder_depth=config.decoder_depth,
            decoder_num_heads=config.decoder_heads,
            decoder_num_classes=3 * config.tubelet * config.patch_size**2,
            tubelet_size=config.tubelet,
            qkv_bias=True,
            norm_layer=partial(nn.LayerNorm, eps=1e-6),
            drop_rate=config.dropout,
            attn_drop_rate=config.dropout,
            drop_path_rate=config.drop_path,
        )
        if config.frames == 1:
            # Framewise reference reuses transformer blocks; no cross-frame computation.
            n = (config.image_size // config.patch_size) ** 2
            model.encoder.patch_embed.num_patches = n
            model.encoder.pos_embed = get_sinusoid_encoding_table(n, config.encoder_width)
            model.pos_embed = get_sinusoid_encoding_table(n, config.decoder_width)
        model.bt_config = config
    return model


def model_identity(model):
    return identity(
        {
            name: digest(value.detach().cpu().contiguous().numpy().tobytes())
            for name, value in model.state_dict().items()
        }
    )


def encode_video(model, inputs):
    config = model.bt_config
    if tuple(inputs.shape[1:]) != (3, config.frames, config.image_size, config.image_size):
        raise ValueError("encoder input shape disagrees with model configuration")
    n = config.frames // config.tubelet * (config.image_size // config.patch_size) ** 2
    return model.encoder(
        inputs, torch.zeros((inputs.shape[0], n), device=inputs.device, dtype=torch.bool)
    )
