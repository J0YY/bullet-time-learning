from copy import deepcopy
import numpy as np
import pytest
from scipy.stats import ttest_1samp
from bullet_time.evaluation.statistics import (
    paired_tost,
    holm,
    main_components,
    conjunction,
    paired_reports,
    paired_group_bootstrap,
    simulate_joint_power,
)
from bullet_time.evaluation.scoring import score_directory
from fixtures.scoring.factory import make_run
from bullet_time.provenance import identity


def paired_fixture(template, side, seed, readout):
    report = deepcopy(template)
    report["predictor"].update(
        run_id=identity([side, seed]),
        checkpoint_id=identity([side, seed, "checkpoint"]),
        readout_seed=readout,
    )
    return report


def test_tost_matches_independent_scipy_tests_and_strict_boundaries():
    values = np.array([0.001, -0.002, 0.004, -0.001, 0.002])
    result = paired_tost(values, 0.02)
    assert result["p_lower"] == pytest.approx(
        ttest_1samp(values, -0.02, alternative="greater").pvalue
    )
    assert result["p_upper"] == pytest.approx(ttest_1samp(values, 0.02, alternative="less").pvalue)
    assert result["equivalent"] and result["component_confidence"] == 0.9
    outside = paired_tost(values + 0.03, 0.02)
    assert not outside["equivalent"]
    boundary = paired_tost(values, result["component_interval"][1])
    assert not boundary["equivalent"]
    zero = paired_tost([0, 0, 0], 0.02)
    assert not zero["equivalent"] and not zero["inference_available"]
    with pytest.raises(ValueError):
        paired_tost([0], 0.02)


def test_holm_and_complete_conjunction():
    h = holm({"a": 0.01, "b": 0.02, "c": 0.06})
    assert [h[k]["holm_adjusted_p"] for k in ["a", "b", "c"]] == pytest.approx([0.03, 0.04, 0.06])
    assert h["a"]["reject"] and not h["c"]["reject"]
    assert len(main_components()) == 30 and len(main_components(True)) == 70
    result = paired_tost([0, 0.001, -0.001], 0.02)
    components = {key: result for key in main_components()}
    assert conjunction(components)["all_components_equivalent"]
    components.pop(next(iter(components)))
    assert not conjunction(components)["all_components_equivalent"]
    components = {key: result for key in main_components()}
    components[next(iter(components))] = {"equivalent": False}
    assert not conjunction(components)["all_components_equivalent"]


def test_readout_average_before_paired_seed_inference_and_group_bootstrap(tmp_path):
    d, e, labels_path, g, f = make_run(tmp_path / "r")
    template = score_directory(d, e, labels_path, g, split="dev", families=f)
    left = {}
    right = {}
    seeds = [17, 29, 43]
    readouts = [101, 102, 103]
    for s in seeds:
        for r in readouts:
            left[s, r] = paired_fixture(template, "left", s, r)
            right[s, r] = paired_fixture(template, "right", s, r)
            left[s, r]["primary"] = 0.5 + (s / 1000) + (r - 102) * 0.1
    result = paired_reports(left, right, seeds, readouts, 0.1)
    assert result["inference"]["n_paired_pretraining_seeds"] == 3
    assert result["inference"]["paired_differences"] == pytest.approx([0.017, 0.029, 0.043])
    assert result["seed_averages"][0]["condition_readout_sd"] == pytest.approx(0.1)
    bootstrap = paired_group_bootstrap(left, right, seeds, readouts, replicates=100, crossed=True)
    # The fake scalar scores above cannot trick resampling: it recomputes actual rows.
    assert bootstrap["percentile_interval_95"] == [0, 0]
    right.pop((17, 101))
    assert not paired_reports(left, right, seeds, readouts, 0.1)["complete"]
    right[17, 101] = paired_fixture(template, "right", 17, 101)
    right[17, 101]["rows"][0]["group_id"] = "wrong"
    with pytest.raises(ValueError, match="unpaired"):
        paired_reports(left, right, seeds, readouts, 0.1)


def test_bootstrap_keeps_three_frame_tracking_events_together(tmp_path):
    d, e, labels_path, g, f = make_run(tmp_path / "r", task="tracking")
    template = score_directory(d, e, labels_path, g, split="dev", families=f)
    reports = {
        (s, r): paired_fixture(template, "same", s, r)
        for s in [17, 29, 43]
        for r in [101, 102, 103]
    }
    result = paired_group_bootstrap(reports, reports, [17, 29, 43], [101, 102, 103], replicates=100)
    assert result["percentile_interval_95"] == [0, 0]


def test_pairing_rejects_checkpoint_mix_and_different_fitted_examples(tmp_path):
    d, e, labels_path, g, f = make_run(tmp_path / "r")
    template = score_directory(d, e, labels_path, g, split="dev", families=f)
    seeds, readouts = [17, 29, 43], [101, 102, 103]
    left = {(s, r): paired_fixture(template, "left", s, r) for s in seeds for r in readouts}
    right = {(s, r): paired_fixture(template, "right", s, r) for s in seeds for r in readouts}
    for reports in (left, right):
        for report in reports.values():
            report["readout_training"] = {
                "training_episode_ids": ["a", "b"],
                "label_sha256": "1" * 64,
            }
    bad = deepcopy(left)
    bad[17, 102]["predictor"]["checkpoint_id"] = "f" * 64
    with pytest.raises(ValueError, match="one backbone checkpoint"):
        paired_reports(bad, right, seeds, readouts, 0.02)
    bad = deepcopy(left)
    for r in readouts:
        bad[29, r]["predictor"] = deepcopy(bad[17, r]["predictor"])
    with pytest.raises(ValueError, match="distinct pretraining seeds"):
        paired_reports(bad, right, seeds, readouts, 0.02)
    for binding in [
        {"training_episode_ids": ["a", "c"], "label_sha256": "1" * 64},
        {"training_episode_ids": ["a", "b"], "label_sha256": "2" * 64},
        None,
    ]:
        bad = deepcopy(left)
        bad[17, 101]["readout_training"] = binding
        with pytest.raises(ValueError, match="training inventories"):
            paired_reports(bad, right, seeds, readouts, 0.02)


def test_joint_power_is_seeded_prospective_and_conjunction_is_harder():
    a = simulate_joint_power(5, 71, [0.01], 0.01, 0, trials=3000)
    assert 0.25 < a["global_power"] < 0.34  # exact single-component scenario is about .294
    assert a == simulate_joint_power(5, 71, [0.01], 0.01, 0, trials=3000)
    b = simulate_joint_power(5, 71, [0.01] * 30, 0.01, 0, trials=1000)
    assert b["global_power"] < a["global_power"]
    c = simulate_joint_power(5, 71, [0.01] * 30, 0.01, 1, trials=1000)
    assert 0.23 < c["global_power"] < 0.36 and c["planning_only"]
