"""Enumerate independent pilot slots; never launch them or replace failed slots."""

from dataclasses import asdict, replace
from bullet_time.models.video import ModelConfig
from bullet_time.training.runner import TrainConfig
from bullet_time.evaluation.training import ReadoutConfig
from bullet_time.provenance import identity


def pilot_slots():
    model = ModelConfig()
    base = TrainConfig()
    conditions = ("view", "time", "mix50", "joint", "shuffled_time", "regrouped")
    seeds = (17, 29, 43)
    training = []
    checkpoints = []

    def add(kind, condition, seed, mc, tc):
        run_id = f"pilot-v1-{kind}-{condition}-s{seed}"
        slot = {
            "run_id": run_id,
            "kind": kind,
            "condition": condition,
            "seed": seed,
            "model": asdict(mc),
            "training": asdict(tc),
            "status": "planned_not_admitted",
            "requires": ["immutable_corpus", "real_gate_evidence", "resources"],
        }
        training.append(slot)
        checkpoints.append((run_id, 20))
        if kind == "controlled" and seed == 17 and condition in ("view", "time", "mix50"):
            checkpoints.append((run_id, 4))

    for condition in conditions:
        for seed in seeds:
            add("controlled", condition, seed, model, replace(base, condition=condition, seed=seed))
    for condition in ("view", "time"):
        add("native", condition, 17, model, replace(base, condition=condition, recipe="native"))
    for seed in seeds:
        add(
            "image_mae",
            "image_only",
            seed,
            replace(model, frames=1, tubelet=1),
            replace(base, seed=seed, mask_ratio=0.75, microbatch_clips=16),
        )
    references = [
        {
            "run_id": f"pilot-v1-untrained-s{seed}",
            "kind": "untrained",
            "seed": seed,
            "status": "not_materialized",
        }
        for seed in seeds
    ]
    references.append(
        {"run_id": "pilot-v1-dinov2-vits14", "kind": "external_image", "status": "not_materialized"}
    )
    checkpoints.extend((r["run_id"], 0) for r in references)
    heads = []
    for run_id, passes in checkpoints:
        for task in ("collision", "order", "tracking", "ssv2"):
            for readout_seed in (101, 102, 103):
                config = ReadoutConfig(
                    task=task, seed=readout_seed, label_budget=None if task == "ssv2" else 300
                )
                heads.append(
                    {
                        "slot_id": f"{run_id}-p{passes}-{task}-r{readout_seed}",
                        "run_id": run_id,
                        "checkpoint_pass": passes,
                        "task": task,
                        "readout": asdict(config),
                        "label_budget": "10pct_of_internal_train" if task == "ssv2" else 300,
                        "input_access": "internal_dev_only"
                        if task == "ssv2" or passes == 4
                        else "train_dev_then_pilot_assessment",
                        "status": "planned_not_admitted",
                        "requires": [
                            "checkpoint_hash",
                            "input_split_hashes",
                            "label_subset_hash",
                            "resources",
                        ],
                    }
                )
    diagnostics = []
    for task, mode in [
        ("collision", "sequence"),
        ("order", "sequence"),
        ("tracking", "sequence"),
        ("collision", "final_frame"),
        ("order", "final_frame"),
        ("order", "bag"),
        ("tracking", "current_frame"),
    ]:
        diagnostics.append(
            {
                "slot_id": f"pilot-v1-supervised-{task}-{mode}",
                "readout": asdict(
                    ReadoutConfig(
                        task=task, seed=101, mode=mode, kind="diagnostic", label_budget=600
                    )
                ),
                "backbone_reference": "pilot-v1-dinov2-vits14",
                "initialization_policy": "same external pretrained image weights across all seven supervised controls",
                "label_budget": 600,
                "status": "planned_not_admitted",
                "requires": ["S3_measurement_sets", "common_dev_recipe", "resources"],
            }
        )
    result = {
        "schema_version": "bullet-time.execution-plan.v1",
        "training": training,
        "references": references,
        "readouts": heads,
        "supervised_diagnostics": diagnostics,
        "launches": 0,
    }
    result["plan_sha256"] = identity(result)
    return result


def estimate_resources(benchmark, *, grids=1000, passes=20, runs=18):
    if (
        benchmark["frames_per_sequence"] != 16
        or benchmark["clips"] <= 0
        or benchmark["seconds"] <= 0
    ):
        raise ValueError("need a positive measured video update benchmark")
    clips = grids * 16 * passes * runs
    seconds_per_clip = benchmark["seconds"] / benchmark["clips"]
    return {
        "scope": "measured single-update extrapolation; not an allocation or end-to-end benchmark",
        "benchmark_binding": benchmark["binding_sha256"],
        "controlled_clips": clips,
        "controlled_device_hours": clips * seconds_per_clip / 3600,
        "raw_pretraining_rgb_bytes": grids * 256 * 224 * 224 * 3,
        "excluded_costs": [
            "rendering",
            "native/image training",
            "seven supervised fits",
            "360 frozen heads",
            "feature extraction",
            "tuning",
            "failures",
            "evaluation storage",
            "checkpoints",
        ],
        "uncertainty": "single-update throughput may include startup/cache effects; measure on intended full model/hardware",
    }
