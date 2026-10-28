from dataclasses import asdict
from types import SimpleNamespace
import json
import pytest
from bullet_time.training.admission import admit
from bullet_time.training.runner import TrainConfig
from bullet_time.models.video import ModelConfig
from bullet_time.provenance import identity, digest
from bullet_time.training.audit import audit_update
from bullet_time.loading.manifest import Corpus
from fixtures.consumer.factory import make_corpus
from test_runner import TINY


def test_all_eight_actual_updates_have_equal_pixels_targets_masks_and_budgets(tmp_path):
    corpus = Corpus(make_corpus(tmp_path / "data", count=8), image_size=32)
    report = audit_update(
        corpus, TINY, TrainConfig(total_passes=4, warmup_passes=1, microbatch_clips=8)
    )
    assert report["all_conditions_pass"] and len(report["events"]) == 8
    assert {e["images"] for e in report["events"].values()} == {2048}


def test_admission_rejects_wrong_scope_hash_corpus_and_caps(tmp_path):
    corpus = SimpleNamespace(
        manifest_sha256="a" * 64,
        grids=[SimpleNamespace(scene_family="projectile_arena") for _ in range(1000)],
        image_size=224,
    )
    model = ModelConfig()
    config = TrainConfig()
    evidence = []
    for gate in ("H1", "H2", "resources"):
        path = tmp_path / f"{gate}.json"
        path.write_text(
            json.dumps(
                dict(
                    gate=gate,
                    verdict="pass",
                    synthetic_only=False,
                    corpus_sha256=corpus.manifest_sha256,
                )
            )
        )
        evidence.append(dict(gate=gate, path=path.name, sha256=digest(path.read_bytes())))
    receipt = dict(
        schema_version="bullet-time.admission.v1",
        scope="pilot_early",
        corpus_sha256=corpus.manifest_sha256,
        model_config_sha256=identity(asdict(model)),
        training_config_sha256=identity(asdict(config)),
        evidence=evidence,
        maximum_updates=500,
        approved_device="cpu",
    )
    path = tmp_path / "receipt.json"

    def check(value=receipt, **kwargs):
        path.write_text(json.dumps(value))
        return admit(
            corpus,
            model,
            config,
            "pilot_early",
            receipt_path=path,
            stop_after_updates=kwargs.get("stop", 500),
        )

    assert check()["scope"] == "pilot_early"
    for bad in (
        dict(receipt, scope="pilot_full"),
        dict(receipt, model_config_sha256="b" * 64),
        dict(receipt, approved_device="cuda"),
        dict(receipt, evidence=evidence[:2]),
    ):
        with pytest.raises(ValueError):
            check(bad)
    with pytest.raises(ValueError):
        check(stop=501)
    changed = tmp_path / "H1.json"
    changed.write_text("{}")
    with pytest.raises(ValueError, match="evidence changed"):
        check()
    changed.write_text(
        json.dumps(dict(gate="H1", verdict="pass", synthetic_only=False, corpus_sha256="b" * 64))
    )
    evidence[0]["sha256"] = digest(changed.read_bytes())
    with pytest.raises(ValueError, match="admitted corpus"):
        check()
