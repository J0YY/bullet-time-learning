import csv
import json
import platform
import pytest
import torch
from bullet_time.evaluation.inputs import EvaluationInputs
from bullet_time.evaluation.training import Targets, ReadoutConfig, build_readout, fit, predict
from bullet_time.evaluation.export import write_predictions, KEY
from bullet_time.models.video import build_model, model_identity
from fixtures.consumer.evaluation import fixtures, TINY


DEVICES = [
    "cpu",
    pytest.param(
        "mps",
        marks=pytest.mark.skipif(
            not torch.backends.mps.is_available() or platform.machine() != "arm64",
            reason="native Apple Silicon MPS required",
        ),
    ),
]


@pytest.mark.parametrize("device", DEVICES)
def test_fit_frozen_head_predict_and_complete_failure_export(tmp_path, device):
    inputs_path, store, base = fixtures(tmp_path / "data")
    rows = []
    labels = []
    for index, split in enumerate(("train", "train", "dev", "dev")):
        row = dict(base, episode_id=f"episode-{index}", split=split)
        rows.append(row)
        labels.append(
            dict(
                schema_version="bullet-time.labels.v1",
                task_id="collision",
                episode_id=row["episode_id"],
                query_id="query",
                horizon_or_frame="0.5",
                split=split,
                target={"contact": index % 2},
            )
        )
    inputs_path.write_text("".join(json.dumps(r) + "\n" for r in rows))
    labels_path = tmp_path / "labels.jsonl"
    labels_path.write_text("".join(json.dumps(r) + "\n" for r in labels))
    inputs = EvaluationInputs(inputs_path, store)
    targets = Targets(labels_path, inputs)
    cfg = ReadoutConfig(epochs=2, batch_size=3, image_size=32, width=24, heads=3, device=device)
    backbone = build_model(TINY, 17)
    initial = model_identity(backbone)
    model = build_readout(backbone, cfg)
    twin = build_readout(build_model(TINY, 17), cfg)
    assert model_identity(model.head) == model_identity(twin.head)
    report = fit(model, inputs, targets, cfg)
    from bullet_time.training.runner import code_identity

    assert report["execution"]["source_sha256"] == code_identity()
    assert report["execution"]["deterministic_algorithms"]
    assert model_identity(backbone) == initial and len(report["history"]) == 2
    predictions = predict(model, inputs, cfg)
    expected = []
    observed = []
    for example, value in predictions:
        row = dict(
            run_id="synthetic-run",
            checkpoint_id="initial",
            task_id=example.task_id,
            label_budget=2,
            readout_seed=101,
            episode_or_video_id=example.episode_id,
            query_id=example.query_id,
            horizon_or_frame=example.key[-1],
            split=example.split,
            scene_family="fixture",
            pair_group_id=example.episode_id,
            target_reference_sha256=targets.reference_hash(example),
            prediction_role=example.prediction_role,
        )
        expected.append(row)
        observed.append(
            {
                **{k: row[k] for k in KEY},
                "status": "ok",
                "error": "",
                "contact_probability": value[0],
            }
        )
    coverage = write_predictions(
        tmp_path / "complete", expected, observed, {"synthetic_only": True}
    )
    assert coverage["complete"] and coverage["ok"] == 4
    coverage = write_predictions(
        tmp_path / "missing", expected, observed[:-1], {"synthetic_only": True}
    )
    assert not coverage["complete"] and coverage["missing"] == 1
    with (tmp_path / "missing" / "predictions.csv").open() as file:
        exported = list(csv.DictReader(file))
    assert exported[-1]["status"] == "missing" and exported[-1]["contact_probability"] == ""
    with pytest.raises(ValueError):
        write_predictions(tmp_path / "duplicate", expected, observed + observed[:1], {})
    rows[-1]["split"] = "assessment"
    inputs_path.write_text("".join(json.dumps(r) + "\n" for r in rows))
    assessment = EvaluationInputs(inputs_path, store, allowed_splits=("train", "dev", "assessment"))
    with pytest.raises(ValueError, match="inaccessible"):
        fit(model, assessment, targets, cfg)


@pytest.mark.parametrize("device", DEVICES)
def test_tracking_window_and_visibility_training_guard(tmp_path, device):
    inputs_path, store, base = fixtures(tmp_path / "data")
    rows = []
    labels = []

    def image_id(i):
        return f"0/{i % 16}/{i // 16}"

    for episode, split in [("train-episode", "train"), ("dev-episode", "dev")]:
        for t in (15, 17, 18, 19):
            role = "auxiliary" if t == 15 else "primary"
            row = dict(
                schema_version="bullet-time.evaluation.v2",
                task_id="tracking",
                episode_id=episode,
                query_id="point",
                split=split,
                observed_image_ids=[image_id(i) for i in range(t - 15, t + 1)],
                observed_frame_indices=list(range(t - 15, t + 1)),
                query_points=[],
                reference_frame=14,
                reference_image_id=image_id(14),
                reference_point=[0.4, 0.5],
                prediction_frame=t,
                prediction_role=role,
            )
            rows.append(row)
            labels.append(
                dict(
                    schema_version="bullet-time.labels.v1",
                    task_id="tracking",
                    episode_id=episode,
                    query_id="point",
                    horizon_or_frame=str(t),
                    split=split,
                    target=dict(
                        x=0.4,
                        y=0.5,
                        visible=int(t != 15),
                        bbox_diagonal_pixels=32,
                        prediction_role=role,
                    ),
                )
            )
    inputs_path.write_text("".join(json.dumps(r) + "\n" for r in rows))
    data = EvaluationInputs(inputs_path, store)
    labels_path = tmp_path / "labels.jsonl"
    labels_path.write_text("".join(json.dumps(r) + "\n" for r in labels))
    targets = Targets(labels_path, data)
    cfg = ReadoutConfig(
        task="tracking", epochs=1, image_size=32, width=24, heads=3, batch_size=4, device=device
    )
    model = build_readout(build_model(TINY, 17), cfg)
    report = fit(model, data, targets, cfg)
    assert report["train_episodes"] == 1 and len(predict(model, data, cfg)) == 8
    bad = dict(rows[1], reference_frame=18)
    inputs_path.write_text(json.dumps(bad) + "\n")
    with pytest.raises(ValueError, match="causal"):
        EvaluationInputs(inputs_path, store)
