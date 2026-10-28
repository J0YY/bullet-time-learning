import argparse
from dataclasses import asdict
import json
import pytest
import torch
from bullet_time.cli import command_predict, load_backbone
from bullet_time.evaluation.access import prediction_access, prediction_ids
from bullet_time.evaluation.training import ReadoutConfig
from bullet_time.provenance import digest
from bullet_time.training.plan import pilot_slots
from bullet_time.training.runner import Runner, TrainConfig
from bullet_time.loading.manifest import Corpus
from fixtures.consumer.factory import make_corpus
from fixtures.consumer.evaluation import TINY


def test_diagnostic_identities_are_distinct_and_bind_fitted_weights():
    source = {
        "run_id": "same-initial-run",
        "checkpoint_sha256": "same-initial-weights",
        "assessment_eligible": True,
    }
    configs = [ReadoutConfig(**slot["readout"]) for slot in pilot_slots()["supervised_diagnostics"]]
    ids = [prediction_ids(config, source, "fitted-model") for config in configs]
    assert len({row["run_id"] for row in ids}) == 7
    assert all(row["checkpoint_id"] == "fitted-model" for row in ids)
    assert prediction_access(ReadoutConfig(task="ssv2"), source) == ["dev"]
    assert prediction_access(ReadoutConfig(), source) == ["dev", "assessment"]
    assert prediction_access(ReadoutConfig(), dict(source, assessment_eligible=False)) == ["dev"]


@pytest.mark.parametrize("task,complete", [("collision", False), ("ssv2", True)])
def test_ineligible_assessment_rejected_before_input_or_model_access(tmp_path, task, complete):
    checkpoint = tmp_path / "head.pt"
    # A deliberately minimal checkpoint proves the access rejection happens before
    # any backbone or nonexistent assessment input can be loaded.
    torch.save(
        {
            "schema_version": "bullet-time.readout.v1",
            "readout_config": asdict(ReadoutConfig(task=task)),
            "backbone_source": {"assessment_eligible": complete},
            "allowed_prediction_splits": ["dev"],
        },
        checkpoint,
    )
    (tmp_path / "head.pt.json").write_text(json.dumps({"sha256": digest(checkpoint.read_bytes())}))
    args = argparse.Namespace(
        checkpoint=checkpoint, split="assessment", device="cpu", images=tmp_path / "forbidden-input"
    )
    with pytest.raises(ValueError, match="not eligible"):
        command_predict(args)


def test_actual_backbone_progress_defines_early_and_full_eligibility(tmp_path):
    corpus = Corpus(make_corpus(tmp_path / "data", count=1), image_size=32)
    runner = Runner(corpus, TINY, TrainConfig())
    runner.global_step = 4
    runner.save(tmp_path / "early.pt")
    runner.global_step = 20
    runner.save(tmp_path / "full.pt")
    assert not load_backbone(tmp_path / "early.pt")[1]["assessment_eligible"]
    assert load_backbone(tmp_path / "full.pt")[1]["assessment_eligible"]
