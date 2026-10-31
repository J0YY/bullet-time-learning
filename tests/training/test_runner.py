from dataclasses import replace
import torch
import pytest
from bullet_time.models.video import ModelConfig, build_model, encode_video, model_identity
from bullet_time.training.runner import Runner, TrainConfig, learning_rate
from bullet_time.loading.manifest import Corpus
from fixtures.consumer.factory import make_corpus

TINY = ModelConfig(
    image_size=32,
    patch_size=8,
    encoder_width=24,
    encoder_depth=1,
    encoder_heads=3,
    decoder_width=24,
    decoder_depth=1,
    decoder_heads=3,
)


def test_full_grid_tail_and_microbatch_gradient_invariance(tmp_path):
    corpus = Corpus(make_corpus(tmp_path / "rgb", count=3), image_size=32)
    cfg = TrainConfig(total_passes=4, warmup_passes=0, grids_per_update=2, microbatch_clips=3)
    a = Runner(corpus, TINY, cfg)
    b = Runner(corpus, TINY, replace(cfg, microbatch_clips=16))
    assert a.initialization_sha256 == b.initialization_sha256
    before = model_identity(a.model)
    record = a.step(detailed_audit=True)
    b.step()
    assert record["clips"] == 32 and record["images"] == 512
    assert before != model_identity(a.model)
    for p, q in zip(a.model.parameters(), b.model.parameters()):
        torch.testing.assert_close(p, q, atol=3e-7, rtol=1e-4)
    tail = a.step()
    assert tail["clips"] == 16 and tail["optimizer_steps"] == 2
    assert tail["target_values"] * 2 == record["target_values"]


def test_resume_exact_and_reject_changed_budget_or_bytes(tmp_path):
    corpus = Corpus(make_corpus(tmp_path / "rgb", count=2), image_size=32)
    cfg = TrainConfig(total_passes=4, warmup_passes=1, grids_per_update=1, microbatch_clips=4)
    mc = replace(TINY, dropout=0.1, drop_path=0.1)
    a = Runner(corpus, mc, cfg)
    a.step()
    a.save(tmp_path / "state.pt")
    b = Runner(corpus, mc, cfg)
    b.resume(tmp_path / "state.pt")
    left = a.step()
    right = b.step()
    assert left["loss"] == right["loss"] and left["learning_rate"] == right["learning_rate"]
    assert model_identity(a.model) == model_identity(b.model)
    with pytest.raises(ValueError, match="binding"):
        Runner(corpus, mc, replace(cfg, total_passes=8)).resume(tmp_path / "state.pt")
    image = corpus.root / corpus.grids[0].cells[0].rgb_path
    image.write_bytes(b"changed")
    with pytest.raises(ValueError, match="hash mismatch"):
        b.resume(tmp_path / "state.pt")


def test_clip_isolation_and_frozen_features():
    model = build_model(TINY, 17).eval()
    x = torch.randn(2, 3, 16, 32, 32)
    with torch.no_grad():
        both = encode_video(model, x)
        single = encode_video(model, x[:1])
        x[1] *= 100
        altered = encode_video(model, x)
    torch.testing.assert_close(both[:1], single, atol=1e-6, rtol=1e-5)
    torch.testing.assert_close(both[:1], altered[:1], atol=0, rtol=0)
    assert not any(isinstance(m, torch.nn.modules.batchnorm._BatchNorm) for m in model.modules())


def test_source_model_shape_and_framewise_variant():
    model = build_model(ModelConfig(), 17).eval()
    assert len(model.encoder.blocks) == 12 and model.encoder.embed_dim == 384
    with torch.no_grad():
        x = torch.zeros(1, 3, 16, 224, 224)
        spatial = torch.arange(196) >= 20
        mask = spatial.repeat(8)[None]
        assert model(x, mask).shape == (1, 1408, 1536)
    image = build_model(replace(TINY, frames=1, tubelet=1), 17)
    assert encode_video(image, torch.zeros(2, 3, 1, 32, 32)).shape == (2, 16, 24)


def test_scheduler_uses_fixed_total_not_interruption():
    cfg = TrainConfig(total_passes=20, warmup_passes=2)
    assert learning_rate(cfg, 2499, 125) == cfg.minimum_learning_rate
    assert learning_rate(cfg, 0, 125) == cfg.warmup_learning_rate
    assert learning_rate(cfg, 499, 125) > cfg.minimum_learning_rate


def test_framewise_reference_consumes_every_frame_and_advances_once(tmp_path):
    corpus = Corpus(make_corpus(tmp_path / "rgb", count=1), image_size=32)
    cfg = TrainConfig(
        total_passes=4, warmup_passes=0, grids_per_update=8, microbatch_clips=16, mask_ratio=0.75
    )
    runner = Runner(corpus, replace(TINY, frames=1, tubelet=1), cfg)
    record = runner.step(detailed_audit=True)
    assert record["images"] == 256 and record["sequences"] == 256 and record["clips"] == 0
    assert record["optimizer_steps"] == 1
    assert len(record["detailed_exposure"][corpus.grids[0].grid_id]) == 256


def test_consumer_hash_tracks_used_code_and_pins_without_blocking_producer_work(tmp_path):
    from bullet_time.training.runner import code_identity

    (tmp_path / "loading").mkdir()
    (tmp_path / "loading/consumer.py").write_text("version = 1")
    original = code_identity(tmp_path)
    (tmp_path / "schema.py").write_text("producer version = 1")
    (tmp_path / "generation").mkdir()
    (tmp_path / "generation/generator.py").write_text("producer version = 2")
    (tmp_path / "evaluation").mkdir()
    (tmp_path / "evaluation/metrics.py").write_text("independent analysis version = 3")
    for name in (
        "scoring.py",
        "statistics.py",
        "score_plan.py",
        "assessment_policy.py",
        "assessment_state.py",
        "assessment_contract.py",
        "assessment_inputs.py",
        "job_evidence.py",
    ):
        (tmp_path / "evaluation" / name).write_text("unimported operational scoring")
    assert code_identity(tmp_path) == original
    (tmp_path / "evaluation/export.py").write_text("shared consumer export code")
    assert code_identity(tmp_path) != original
    (tmp_path / "evaluation/export.py").unlink()
    (tmp_path / "loading/consumer.py").write_text("version = 2")
    changed = code_identity(tmp_path)
    assert changed != original
    (tmp_path / "models/pins").mkdir(parents=True)
    (tmp_path / "models/pins/source.json").write_text('{"source":"changed"}')
    assert code_identity(tmp_path) != changed
