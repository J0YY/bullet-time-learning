"""Actual small-model pass/replay checks; fixtures are not native pilot evidence."""

from dataclasses import replace
import json
import pytest
import torch

from bullet_time.loading.manifest import Corpus
from bullet_time.training.runner import TrainConfig
from bullet_time.training import tail_audit as a
from fixtures.consumer.factory import make_corpus
from test_runner import TINY


@pytest.fixture
def corpus(tmp_path):
    return Corpus(make_corpus(tmp_path / "rgb", count=3), image_size=32)


CONFIG = TrainConfig(total_passes=4, warmup_passes=1, grids_per_update=2, microbatch_clips=8)


def test_actual_complete_pass_and_stochastic_tail_replay_in_every_arm(tmp_path, corpus):
    root = tmp_path / "audit"
    result = a.audit_tail_pass(corpus, replace(TINY, dropout=0.1, drop_path=0.1), CONFIG, root)
    assert result["all_conditions_pass"] and len(result["conditions"]) == 8
    assert not result["pilot_100_grid_layout"] and not result["scientific_gate_pass"]
    assert result["actual_updates_per_condition"] == 2 and result["tail_grids"] == 1
    assert len({tuple(r["tail_grid_ids"]) for r in result["conditions"].values()}) == 1
    for condition, row in result["conditions"].items():
        assert row["tail_replay_exact"]
        events = [
            json.loads(line)
            for line in (root / condition / "updates.jsonl").read_text().splitlines()
        ]
        assert [e["images"] for e in events] == [512, 256]
        assert events[0]["target_values"] == 2 * events[1]["target_values"]
        assert len({g for e in events for g in e["grid_ids"]}) == 3
        assert all("detailed_exposure" not in e for e in events)
        assert (
            json.loads((root / condition / "before-tail.pt.json").read_text())["global_step"] == 1
        )
    assert json.loads((root / "run.json").read_text())["status"] == "completed"
    with pytest.raises(FileExistsError):
        a.audit_tail_pass(corpus, TINY, CONFIG, root)


@pytest.mark.parametrize("fault", ["denominator", "duplicate", "replay"])
def test_incorrect_tail_or_replay_fails_without_success_receipt(
    tmp_path, corpus, monkeypatch, fault
):
    original = a.Runner.step

    def corrupt(self, **kwargs):
        event = original(self, **kwargs)
        if fault == "denominator" and event["step"] == 1:
            event["target_values"] *= 2
        if fault == "duplicate" and event["step"] == 1:
            event["grid_ids"] = [self.first_grid]
        if event["step"] == 0:
            self.first_grid = event["grid_ids"][0]
        return event

    monkeypatch.setattr(a.Runner, "step", corrupt)
    if fault == "replay":
        resume = a.Runner.resume

        def altered(self, path):
            resume(self, path)
            next(iter(self.optimizer.state.values()))["exp_avg"].add_(0.1)

        monkeypatch.setattr(a.Runner, "resume", altered)
    root = tmp_path / "failed"
    with pytest.raises(ValueError, match="normalization|omitted|replay differs"):
        a.audit_tail_pass(corpus, TINY, CONFIG, root)
    assert not (root / "report.json").exists()
    assert json.loads((root / "run.json").read_text())["status"] == "failed"


def test_reject_invalid_audit_shapes_before_output(tmp_path, corpus):
    for cfg, model in (
        (replace(CONFIG, grids_per_update=3), TINY),
        (replace(CONFIG, grids_per_update=4), TINY),
        (replace(CONFIG, recipe="native"), TINY),
        (CONFIG, replace(TINY, frames=1, tubelet=1)),
    ):
        with pytest.raises(ValueError, match="tail audit"):
            a.audit_tail_pass(corpus, model, cfg, tmp_path / "never")
    assert not (tmp_path / "never").exists()


def test_optimizer_hash_binds_values_and_scalar_hyperparameters():
    state = {0: {"exp_avg": torch.ones(3), "step": torch.tensor(12.0)}, "lr": 0.001}
    before = a.state_identity(state)
    assert before == a.state_identity(dict(reversed(list(state.items()))))
    state[0]["exp_avg"][0] += 1
    assert before != a.state_identity(state)
    assert before != a.state_identity(
        {0: {"exp_avg": torch.ones(3), "step": torch.tensor(13.0)}, "lr": 0.001}
    )
