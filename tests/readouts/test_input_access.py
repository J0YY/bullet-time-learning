import json
from dataclasses import replace
import numpy as np
import pytest
import torch
from bullet_time.evaluation.inputs import (
    EvaluationInputs,
    letterbox,
    uniform_frame_indices,
)
from bullet_time.evaluation.heads import DiagnosticModel, FrameEncoder, FrozenReadout
from bullet_time.models.video import build_model, model_identity

from fixtures.consumer.evaluation import fixtures, TINY


def test_forecast_access_and_reject_labels_future_or_heldout(tmp_path):
    path, store, row = fixtures(tmp_path)
    data = EvaluationInputs(path, store)
    seq = data.assemble(data.examples[0], size=32)
    assert set(seq) == {"video", "query_points", "reference", "reference_point"}
    final = data.assemble(data.examples[0], size=32, mode="final_frame")
    assert torch.equal(final["video"][:, 0], seq["video"][:, -1])
    assert torch.equal(final["video"][:, 0], final["video"][:, 10])
    for key, value in [
        ("velocity", 1),
        ("split", "official_validation"),
        ("observed_frame_indices", list(range(15)) + [20]),
    ]:
        bad = dict(row)
        bad[key] = value
        path.write_text(json.dumps(bad) + "\n")
        with pytest.raises(ValueError):
            EvaluationInputs(path, store)


def test_coordinate_letterbox_and_uniform_sampling():
    rgb = np.zeros((20, 40, 3), dtype=np.uint8)
    result, mapping = letterbox(rgb, 224)
    assert result.shape == (3, 224, 224)
    assert mapping((0, 0)) == (0, 56 / 223)
    assert mapping((1, 1)) == (1, 167 / 223)
    assert uniform_frame_indices(1) == (0,) * 16
    assert uniform_frame_indices(16) == tuple(range(16))
    for n in (2, 3, 5, 17, 100):
        indices = uniform_frame_indices(n)
        assert indices[0] == 0 and indices[-1] == n - 1 and tuple(sorted(indices)) == indices


def test_diagnostic_controls_enforce_invariance_and_frozen_backbone():
    image = build_model(replace(TINY, frames=1, tubelet=1), 17)
    x = torch.randn(2, 3, 16, 32, 32)
    points = torch.rand(2, 2, 2)
    bag = DiagnosticModel(FrameEncoder(image), "order", "bag", width=24, depth=2, heads=3).eval()
    original = bag(x, points)
    permuted = bag(x[:, :, torch.randperm(16)], points)
    torch.testing.assert_close(original, permuted, atol=1e-6, rtol=1e-6)
    final = DiagnosticModel(
        FrameEncoder(image), "collision", "final_frame", width=24, heads=3
    ).eval()
    a = final(x, points)
    x[:, :, :15] = torch.randn_like(x[:, :, :15]) * 100
    assert torch.equal(a, final(x, points))
    backbone = build_model(TINY, 17)
    frozen = FrozenReadout(backbone, "collision", width=24, heads=3)
    before = model_identity(backbone)
    frozen.train()
    assert not backbone.training
    frozen(x, points).sum().backward()
    assert all(p.grad is None for p in backbone.parameters())
    assert any(p.grad is not None for p in frozen.head.parameters())
    assert model_identity(backbone) == before


@pytest.mark.parametrize(
    "task,mode",
    [
        ("collision", "sequence"),
        ("order", "sequence"),
        ("tracking", "sequence"),
        ("collision", "final_frame"),
        ("order", "final_frame"),
        ("order", "bag"),
        ("tracking", "current_frame"),
    ],
)
def test_all_seven_supervised_modes_backpropagate_through_image_encoder(task, mode):
    from bullet_time.evaluation.training import ReadoutConfig, build_readout

    backbone = build_model(replace(TINY, frames=1, tubelet=1), 17)
    config = ReadoutConfig(
        task=task, mode=mode, kind="diagnostic", image_size=32, width=24, heads=3
    )
    model = build_readout(backbone, config)
    video = torch.randn(1, 3, 16, 32, 32, requires_grad=True)
    kwargs = (
        {"reference": video.detach().clone(), "reference_point": torch.rand(1, 2)}
        if task == "tracking"
        else {"query_points": torch.rand(1, 2, 2)}
    )
    output = model(video, **kwargs)
    assert output.shape == (1, 3 if task == "tracking" else 1) and torch.isfinite(output).all()
    output.square().sum().backward()
    assert any(p.grad is not None and p.grad.abs().sum() > 0 for p in backbone.encoder.parameters())
    if mode in ("final_frame", "current_frame"):
        assert torch.count_nonzero(video.grad[:, :, :15]) == 0
