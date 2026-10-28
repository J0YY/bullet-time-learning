"""Actual one-update comparisons across every controlled arm; not a learning gate."""

from dataclasses import replace
from .runner import Runner
from bullet_time.loading.schedule import CONDITIONS
from bullet_time.provenance import identity


def audit_update(corpus, model, config):
    if (
        config.recipe != "controlled"
        or model.frames != 16
        or len(corpus.grids) != 8
        or config.grids_per_update != 8
    ):
        raise ValueError(
            "update audit requires exactly eight complete grids and a controlled video model"
        )
    events = {}
    reference = None
    for condition in CONDITIONS:
        runner = Runner(corpus, model, replace(config, condition=condition))
        event = runner.step(detailed_audit=True)
        signature = {
            "grid_ids": event["grid_ids"],
            "exposure": event["detailed_exposure"],
            "target_values": event["target_values"],
            "learning_rate": event["learning_rate"],
            "initialization_sha256": runner.initialization_sha256,
            "optimizer_steps": event["optimizer_steps"],
            "scheduler_steps": event["scheduler_steps"],
        }
        if reference is None:
            reference = signature
        elif signature != reference:
            raise ValueError(f"actual update exposure/init/budget mismatch: {condition}")
        events[condition] = event
    return {
        "schema_version": "bullet-time.update-audit.v1",
        "all_conditions_pass": True,
        "corpus_sha256": corpus.manifest_sha256,
        "shared_update_sha256": identity(reference),
        "events": events,
        "scientific_gate_pass": False,
        "scope": "one actual optimizer update per arm; no empirical learning/solvability claim",
    }
