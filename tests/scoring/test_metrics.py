from copy import deepcopy
import json
import csv
import pytest
from bullet_time.evaluation.scoring import score_directory
from bullet_time.evaluation.metrics import summarize
from bullet_time.provenance import atomic_json, digest
from fixtures.scoring.factory import make_run


def score(bundle):
    directory, expected, labels, groups, families = bundle
    return score_directory(directory, expected, labels, groups, split="dev", families=families)


def rewrite_csv(bundle, change):
    directory = bundle[0]
    p = directory / "predictions.csv"
    with p.open(newline="") as f:
        r = csv.DictReader(f)
        columns = r.fieldnames
        rows = list(r)
    change(rows)
    with p.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=columns)
        w.writeheader()
        w.writerows(rows)
    coverage = json.loads((directory / "coverage.json").read_text())
    coverage["csv_sha256"] = digest(p.read_bytes())
    for k in ["ok", "missing", "failed"]:
        coverage[k] = sum(r["status"] == k for r in rows)
    coverage["complete"] = coverage["ok"] == coverage["expected"]
    atomic_json(directory / "coverage.json", coverage)
    meta = json.loads((directory / "run.json").read_text())
    meta.update(
        csv_sha256=coverage["csv_sha256"],
        coverage_sha256=digest((directory / "coverage.json").read_bytes()),
    )
    atomic_json(directory / "run.json", meta)


def test_balanced_chance_and_brier(tmp_path):
    r = score(make_run(tmp_path / "r"))
    assert r["complete"] and r["primary"] == 0.5
    assert r["families"]["projectile_arena"]["brier"] == 0.25


def test_readout_seed_zero_is_valid(tmp_path):
    from bullet_time.evaluation.export import KEY, write_predictions

    b = make_run(tmp_path / "r")
    rows = json.loads(b[1].read_text())
    for row in rows:
        row["readout_seed"] = 0
    atomic_json(b[1], rows)
    observed = [
        {**{k: r[k] for k in KEY}, "status": "ok", "error": "", "contact_probability": 0.5}
        for r in rows
    ]
    directory = tmp_path / "seed-zero"
    write_predictions(directory, rows, observed, {"scope": "synthetic"})
    result = score((directory, *b[1:]))
    assert result["complete"] and result["predictor"]["readout_seed"] == 0


def test_missing_run_and_failed_prediction_never_score_success_subset(tmp_path):
    bundle = make_run(tmp_path / "r")
    d, *rest = bundle
    assert score((d.parent / "missing-run", *rest))["primary"] is None

    def fail(rows):
        rows[0].update(status="failed", error="intentional failure", contact_probability="")

    rewrite_csv(bundle, fail)
    r = score(bundle)
    assert not r["complete"] and r["primary"] is None
    assert r["families"]["projectile_arena"]["coverage"]["failed"] == 1


def test_family_macro_and_readout_task_top1(tmp_path):
    b = make_run(tmp_path / "r", task="ssv2", families=("a", "b"), episodes_per_family=[2, 6])

    def incorrect(rows):
        for r in rows:
            if r["scene_family"] == "a":
                r["class_id"] = str(1 - int(r["class_id"]))

    rewrite_csv(b, incorrect)
    r = score(b)
    assert r["primary"] == 0.5  # micro average would be .75
    with pytest.raises(ValueError, match="family inventory"):
        score_directory(*b[:4], split="dev", families=["a", "b", "c"])


def test_tracking_all_three_visibility_boundary_and_size_stratum(tmp_path):
    b = make_run(tmp_path / "r", task="tracking")
    r = score(b)
    assert (
        r["primary"] == 1
        and r["families"]["projectile_arena"]["auxiliary_visibility_accuracy"] == 1
    )
    rows = deepcopy(r["rows"])
    row = rows[0]
    row["prediction"]["x"] = row["target"]["x"] + 4 / 223
    row["prediction"]["visibility_probability"] = 0.5
    assert summarize(rows, b[-1])["primary"] == 1
    row["prediction"]["x"] += 1e-6
    assert summarize(rows, b[-1])["primary"] == 0.5
    row["prediction"]["x"] = 0.5
    row["prediction"]["visibility_probability"] = 0.49999
    assert summarize(rows, b[-1])["primary"] == 0.5
    row["target"]["bbox_diagonal_pixels"] = 15.99
    s = summarize(rows, b[-1])
    assert s["primary"] == 1 and s["families"]["projectile_arena"]["small_object_episodes"] == 1
    bad = [
        r
        for r in rows
        if not (r["episode_id"] == row["episode_id"] and r["horizon_or_frame"] == "19")
    ]
    with pytest.raises(ValueError, match="three consecutive"):
        summarize(bad, b[-1])


@pytest.mark.parametrize(
    "kind,match",
    [
        ("label", "target reference"),
        ("group", "prediction/group"),
        ("csv_hash", "artifact hash"),
        ("duplicate", "duplicate/unplanned"),
        ("unplanned", "duplicate/unplanned"),
        ("nan", "finite"),
        ("metadata", "identity/metadata"),
        ("omit", "omits expected"),
        ("partial_pair", "partial related group"),
        ("split", "inaccessible"),
    ],
)
def test_reject_inconsistent_wire_records(tmp_path, kind, match):
    b = make_run(tmp_path / "r")
    d, e, labels_path, g, _ = b
    if kind == "label":
        rows = [json.loads(x) for x in labels_path.read_text().splitlines()]
        rows[0]["target"]["contact"] = 1
        labels_path.write_text("".join(json.dumps(x) + "\n" for x in rows))
    elif kind == "group":
        data = json.loads(g.read_text())
        data["records"][0]["group_id"] = "wrong"
        atomic_json(g, data)
    elif kind == "csv_hash":
        (d / "predictions.csv").write_text("broken")
    elif kind == "duplicate":
        rewrite_csv(b, lambda rows: rows.append(rows[0]))
    elif kind == "unplanned":
        rewrite_csv(b, lambda rows: rows[0].update(query_id="wrong"))
    elif kind == "nan":
        rewrite_csv(b, lambda rows: rows[0].update(contact_probability="nan"))
    elif kind == "metadata":
        rewrite_csv(b, lambda rows: rows[0].update(scene_family="wrong"))
    elif kind == "omit":
        rewrite_csv(b, lambda rows: rows.pop())
    elif kind == "partial_pair":
        atomic_json(e, json.loads(e.read_text())[:1])
    elif kind == "split":
        rows = [json.loads(x) for x in labels_path.read_text().splitlines()]
        rows[0]["split"] = "assessment"
        labels_path.write_text("".join(json.dumps(x) + "\n" for x in rows))
    with pytest.raises(ValueError, match=match):
        score(b)


def test_assessment_rejected_before_labels_are_read(tmp_path):
    with pytest.raises(ValueError, match="locked release"):
        score_directory(
            "absent", "absent", "must-not-open", "absent", split="assessment", families=["arena"]
        )


def test_external_video_group_map_works_and_refuses_split_related_groups(tmp_path):
    b = make_run(tmp_path / "r", task="ssv2")
    data = json.loads(b[3].read_text())
    mapping = {r["episode_id"]: r["group_id"] for r in data["records"]}
    atomic_json(b[3], mapping)
    assert score(b)["primary"] == 1
    mapping["unselected-related-video"] = next(iter(mapping.values()))
    atomic_json(b[3], mapping)
    with pytest.raises(ValueError, match="partial related group"):
        score(b)


def test_failed_fit_receipt_preserves_all_planned_examples(tmp_path):
    b = make_run(tmp_path / "r")
    d = tmp_path / "failed"
    d.mkdir()
    atomic_json(d / "failure.json", {"status": "failed", "error": "known fit failure"})
    r = score((d, *b[1:]))
    assert not r["complete"] and r["families"]["projectile_arena"]["coverage"]["failed"] == 2
