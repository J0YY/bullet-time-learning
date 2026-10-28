import json
from pathlib import Path
from bullet_time.training.plan import pilot_slots, estimate_resources


def test_actual_slot_inventory_matches_spec_independently():
    p = pilot_slots()
    plan = json.loads((Path(__file__).resolve().parents[2] / "configs/pilot-plan.json").read_text())
    controlled = [r for r in p["training"] if r["kind"] == "controlled"]
    assert {(r["condition"], r["seed"]) for r in controlled} == {
        (c, s) for c in plan["conditions"] for s in plan["pretraining_seeds"]
    }
    assert len(p["training"]) == 23 and len(p["references"]) == 4 and p["launches"] == 0
    assert len(p["supervised_diagnostics"]) == 7
    assert len(p["readouts"]) == 360 and len({s["slot_id"] for s in p["readouts"]}) == 360
    early = [r for r in p["readouts"] if r["checkpoint_pass"] == 4]
    assert len(early) == 36 and all(r["input_access"] == "internal_dev_only" for r in early)
    assert all(r["readout"]["seed"] in plan["readout_seeds"] for r in p["readouts"])
    report = estimate_resources(
        {"frames_per_sequence": 16, "clips": 128, "seconds": 6.4, "binding_sha256": "synthetic"}
    )
    assert (
        report["controlled_device_hours"] == 80
        and report["raw_pretraining_rgb_bytes"] == 38535168000
    )
