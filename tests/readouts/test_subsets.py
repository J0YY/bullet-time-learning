import json
import pytest
from bullet_time.evaluation.inputs import EvaluationInputs
from bullet_time.evaluation.subsets import Groups, select_game_labels, verify_pairs
from bullet_time.evaluation.training import Targets, ReadoutConfig, task_examples
from fixtures.consumer.evaluation import fixtures


def test_grouped_budget_pair_integrity_and_horizon_selection(tmp_path):
    path, store, base = fixtures(tmp_path / "data")
    rows = []
    labels = []
    group_rows = []
    for i in range(8):
        split = "train" if i < 6 else "dev"
        group_rows.append(
            dict(episode_id=str(i), task_id="collision", group_id=f"pair-{i // 2}", split=split)
        )
        for horizon in (0.5, 1.0):
            row = dict(base, episode_id=str(i), split=split, horizon_seconds=horizon)
            rows.append(row)
            labels.append(
                dict(
                    schema_version="bullet-time.labels.v1",
                    task_id="collision",
                    episode_id=str(i),
                    query_id="query",
                    horizon_or_frame=str(horizon),
                    split=split,
                    target={"contact": i % 2 if horizon == 0.5 else 1},
                )
            )
    path.write_text("".join(json.dumps(r) + "\n" for r in rows))
    inputs = EvaluationInputs(path, store)
    labels_path = tmp_path / "labels.jsonl"
    labels_path.write_text("".join(json.dumps(r) + "\n" for r in labels))
    targets = Targets(labels_path, inputs)
    groups_path = tmp_path / "groups.json"
    groups_path.write_text(
        json.dumps({"schema_version": "bullet-time.evaluation-groups.v1", "records": group_rows})
    )
    groups = Groups(groups_path)
    assert verify_pairs(inputs, targets, groups, "collision")["pairs"] == 4
    small = select_game_labels(inputs, groups, "collision", 2)
    large = select_game_labels(inputs, groups, "collision", 4)
    assert set(small.selection["episode_ids"]) < set(large.selection["episode_ids"])
    assert len({e.episode_id for e in small.examples if e.split == "train"}) == 2
    assert {e.horizon_seconds for e in task_examples(small, ReadoutConfig())} == {0.5}
    assert {
        e.horizon_seconds for e in task_examples(small, ReadoutConfig(horizon_seconds=1.0))
    } == {1.0}
    with pytest.raises(ValueError, match="pair"):
        select_game_labels(inputs, groups, "collision", 3)
    rows[0]["query_points"] = [[0.1, 0.2], [0.3, 0.4]]
    path.write_text("".join(json.dumps(r) + "\n" for r in rows))
    with pytest.raises(ValueError, match="side information"):
        verify_pairs(EvaluationInputs(path, store), targets, groups, "collision")
    group_rows[-1]["split"] = "train"
    groups_path.write_text(
        json.dumps({"schema_version": "bullet-time.evaluation-groups.v1", "records": group_rows})
    )
    with pytest.raises(ValueError, match="crosses splits"):
        Groups(groups_path)
