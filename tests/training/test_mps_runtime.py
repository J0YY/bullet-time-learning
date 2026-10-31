from dataclasses import replace
import platform

import pytest
import torch

from bullet_time.models.runtime import configure_runtime, runtime_provenance, validate_device
from bullet_time.models.video import seeded_rng, model_identity
from bullet_time.training.runner import Runner, TrainConfig
from bullet_time.evaluation.training import ReadoutConfig
from bullet_time.loading.manifest import Corpus
from fixtures.consumer.evaluation import TINY
from fixtures.consumer.factory import make_corpus

NATIVE_MPS = pytest.mark.skipif(
    not torch.backends.mps.is_available() or platform.machine() != "arm64",
    reason="native Apple Silicon MPS required",
)


def test_device_policy_fails_closed_on_unavailable_or_altered_mps(monkeypatch):
    for config in (TrainConfig(device="mps"), ReadoutConfig(device="mps:0")):
        config.validate()
    with pytest.raises(ValueError, match="device zero"):
        validate_device("mps:1")
    with pytest.raises(ValueError, match="CPU, CUDA or MPS"):
        validate_device("meta")
    monkeypatch.setattr(torch.backends.mps, "is_available", lambda: False)
    with pytest.raises(RuntimeError, match="unavailable"):
        configure_runtime("mps")
    monkeypatch.setattr(torch.backends.mps, "is_available", lambda: True)
    monkeypatch.setattr(platform, "machine", lambda: "x86_64")
    with pytest.raises(RuntimeError, match="Apple Silicon"):
        configure_runtime("mps")
    monkeypatch.setattr(platform, "system", lambda: "Darwin")
    monkeypatch.setattr(platform, "machine", lambda: "arm64")
    for name in ("PYTORCH_ENABLE_MPS_FALLBACK", "PYTORCH_MPS_FAST_MATH"):
        with monkeypatch.context() as change:
            change.setenv(name, "1")
            with pytest.raises(ValueError, match="disabled before process startup"):
                configure_runtime("mps")
    assert configure_runtime("cpu").type == "cpu"
    assert "mps_runtime" not in runtime_provenance("cpu")


@NATIVE_MPS
def test_mps_rng_repeats_and_restores_both_streams_even_after_exception():
    configure_runtime("mps")
    cpu, mps = torch.get_rng_state().clone(), torch.mps.get_rng_state().clone()
    samples = []
    for _ in range(2):
        with seeded_rng(1729, "mps"):
            samples.append((torch.rand(13), torch.rand(13, device="mps").cpu()))
        assert torch.equal(torch.get_rng_state(), cpu)
        assert torch.equal(torch.mps.get_rng_state(), mps)
    assert all(torch.equal(a, b) for a, b in zip(*samples, strict=True))
    with pytest.raises(RuntimeError, match="intentional"):
        with seeded_rng(30, "mps:0"):
            torch.rand(5, device="mps")
            torch.rand(5)
            raise RuntimeError("intentional failure")
    assert torch.equal(torch.get_rng_state(), cpu)
    assert torch.equal(torch.mps.get_rng_state(), mps)
    with seeded_rng(30):
        torch.rand(5)
    assert torch.equal(torch.mps.get_rng_state(), mps)
    provenance = runtime_provenance("mps")
    assert provenance["device_name"].startswith("MPS: Apple")
    assert provenance["mps_runtime"]["macos"]
    assert provenance["mps_runtime"]["fallback"] == "0"


@NATIVE_MPS
def test_mps_actual_grid_tail_and_stochastic_resume_are_exact(tmp_path):
    corpus = Corpus(make_corpus(tmp_path / "rgb", count=3), image_size=32)
    config = TrainConfig(
        device="mps", total_passes=4, warmup_passes=0, grids_per_update=2, microbatch_clips=16
    )
    model = replace(TINY, dropout=0.1, drop_path=0.1)
    original = Runner(corpus, model, config)
    before = model_identity(original.model)
    first = original.step(detailed_audit=True)
    assert model_identity(original.model) != before
    assert first["clips"] == 32 and first["images"] == 512
    original.save(tmp_path / "checkpoint.pt")
    resumed = Runner(corpus, model, config)
    resumed.resume(tmp_path / "checkpoint.pt")
    left, right = original.step(detailed_audit=True), resumed.step(detailed_audit=True)
    assert left["clips"] == right["clips"] == 16
    assert left["target_values"] * 2 == first["target_values"]
    assert left["loss"] == right["loss"]
    assert left["learning_rate"] == right["learning_rate"]
    assert left["detailed_exposure"] == right["detailed_exposure"]
    assert model_identity(original.model) == model_identity(resumed.model)
    with pytest.raises(ValueError, match="binding"):
        Runner(corpus, model, replace(config, device="cpu")).resume(tmp_path / "checkpoint.pt")
