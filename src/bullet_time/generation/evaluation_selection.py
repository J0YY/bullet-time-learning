"""Immutable prospective train/dev request inventory, before any rendering cost."""

from collections import Counter
from pathlib import Path
import platform
import subprocess
import time

import numpy as np

from bullet_time.provenance import (
    atomic_json,
    canonical_bytes,
    digest,
    integer,
    inside,
    strict_json,
    fields,
    identity,
    sha256,
)
from .bundle import ROOT
from .evaluation_motion import select_collection, tracking_background, background_conflict

SCOPE = "prospective train/dev selection only; no rendering, assessment or learning"


def selection_runtime():
    return {
        "python": platform.python_version(),
        "platform": platform.platform(),
        "numpy": np.__version__,
    }


def selection_sources():
    files = [
        "src/bullet_time/generation/evaluation_motion.py",
        "src/bullet_time/generation/evaluation_selection.py",
        "src/bullet_time/generation/bundle.py",
        "src/bullet_time/generation/arena.py",
        "src/bullet_time/provenance.py",
        "scripts/data/plan_evaluation.py",
        "configs/pilot-plan.json",
        "configs/generation/evaluation-raster-exclusions.json",
        read_exclusions()["evidence"]["path"],
    ]
    return {path: digest((ROOT / path).read_bytes()) for path in files}


def counts_from_pilot(plan):
    if plan["schema_version"] != "bullet-time.pilot-plan.v1":
        raise ValueError("unsupported pilot plan")
    integer(plan["data_seed"], "data seed")
    expected = {"collision": 2, "order": 2, "tracking": 1}
    if set(plan["evaluation_sets"]) != set(expected):
        raise ValueError("pilot measurement tasks differ")
    counts = {}
    for task, pair_size in expected.items():
        record = plan["evaluation_sets"][task]
        if record["unit"] != "episode" or integer(record["pair_size"], "pair size", 1) != pair_size:
            raise ValueError("unsupported measurement group unit")
        counts[task] = {}
        for split in ("train", "dev"):
            episodes = integer(record[split], "episode count", 1)
            if episodes % pair_size:
                raise ValueError("episode count would split a related pair")
            counts[task][split] = episodes // pair_size
    return counts


def check_collection(requests, counts):
    expected = {(task, split): n for task, row in counts.items() for split, n in row.items()}
    if Counter((r["task"], r["split"]) for r in requests) != expected:
        raise ValueError("wrong prospective collection counts")
    kinds = ("trajectory", "asset", "configuration")
    for kind in kinds:
        groups = [r["groups"][kind] for r in requests]
        if len(set(groups)) != len(requests):
            raise ValueError(f"duplicate {kind} prototype across collection")
    if len({r["group_id"] for r in requests}) != len(requests):
        raise ValueError("duplicate measurement group ID")
    if any(set(r["assigned_pools"].values()) != {r["split"]} for r in requests):
        raise ValueError("prototype assigned to a different split")
    backgrounds = {
        split: [
            tracking_background(r)
            for r in requests
            if r["task"] == "tracking" and r["split"] == split
        ]
        for split in ("train", "dev")
    }
    if any(background_conflict(a, b) for a in backgrounds["train"] for b in backgrounds["dev"]):
        raise ValueError("tracking background proximity crosses splits")
    return {
        "groups": len(requests),
        "episodes": sum(1 if r["task"] == "tracking" else 2 for r in requests),
        "prospective_rgb_images": sum(len(r["frames"]) for r in requests),
        "unique_prototypes": {kind: len(requests) for kind in kinds},
        "background_guard": "tracking camera bin modulo 16; cross-split palette L1 distance must exceed 4; pixel admission still required",
        "rendered": False,
        "near_duplicate_check": "not run: requires actual pixels",
        "joint_pretraining_lineage": "not admitted",
        "scientific_gate_pass": False,
    }


def read_pilot():
    return strict_json((ROOT / "configs/pilot-plan.json").read_bytes())


def read_exclusions():
    record = strict_json(
        (ROOT / "configs/generation/evaluation-raster-exclusions.json").read_bytes()
    )
    fields(record, {"schema_version", "data_seed", "reason", "evidence", "records"})
    if record["schema_version"] != "bullet-time.measurement-raster-exclusions.v1":
        raise ValueError("unknown raster exclusions")
    if record["data_seed"] != read_pilot()["data_seed"]:
        raise ValueError("raster exclusions belong to another seed")
    fields(record["evidence"], {"path", "sha256"})
    path = inside(ROOT, record["evidence"]["path"])
    if digest(path.read_bytes()) != sha256(record["evidence"]["sha256"]):
        raise ValueError("raster exclusion evidence changed")
    witnesses = strict_json(path.read_bytes())["failures"]
    seen = set()
    for row in record["records"]:
        fields(row, {"task", "split", "index", "group_id"})
        integer(row["index"], "excluded index")
        if row["task"] not in ("collision", "order", "tracking") or row["split"] != "dev":
            raise ValueError("raster repair replaces complete dev groups only")
        gid = f"{row['task']}-{identity([record['data_seed'], row['task'], row['index']])[:16]}"
        if (
            row["group_id"] != gid
            or gid in seen
            or not any(w.get("dev_group") == gid for w in witnesses)
        ):
            raise ValueError("raster exclusion does not match an actual witness")
        seen.add(gid)
    return record


def exclusion_candidates():
    return [{k: r[k] for k in ("task", "split", "index")} for r in read_exclusions()["records"]]


def plan_collection(output):
    output = Path(output).resolve()
    if output.exists():
        raise ValueError("refusing to overwrite a prospective selection")
    if subprocess.check_output(["git", "status", "--porcelain"], cwd=ROOT):
        raise ValueError("commit sources before creating a prospective selection")
    source = selection_sources()
    pilot = read_pilot()
    counts = counts_from_pilot(pilot)
    start = time.perf_counter()
    requests, selection = select_collection(
        pilot["data_seed"], counts, exclusions=exclusion_candidates()
    )
    summary = check_collection(requests, counts)
    output.mkdir(parents=True, mode=0o700)
    (output / "private").mkdir(mode=0o700)
    request_path = output / "private/requests.jsonl"
    request_path.write_bytes(b"".join(canonical_bytes(r) + b"\n" for r in requests))
    if source != selection_sources():
        raise ValueError("selection source/config changed; retain rejected attempt")
    report = {
        "schema_version": "bullet-time.measurement-selection.v1",
        "scope": SCOPE,
        "source_commit": subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
        ).strip(),
        "source_sha256": source,
        "runtime": selection_runtime(),
        "data_seed": pilot["data_seed"],
        "groups_per_task": counts,
        "selection": selection,
        "raster_exclusions": read_exclusions(),
        "summary": summary,
        "seconds": time.perf_counter() - start,
        "inventory": {"private/requests.jsonl": digest(request_path.read_bytes())},
    }
    atomic_json(output / "selection.json", report)
    return report


def verify_selection(output):
    """Reconstruct once from current pinned code/counts, not just artifact hashes."""
    output = Path(output).resolve(strict=True)
    report = strict_json((output / "selection.json").read_bytes())
    if (
        report["schema_version"] != "bullet-time.measurement-selection.v1"
        or report["scope"] != SCOPE
    ):
        raise ValueError("unsupported prospective selection")
    if report["source_sha256"] != selection_sources():
        raise ValueError("selection source changed; use its pinned revision")
    if report.get("raster_exclusions") != read_exclusions():
        raise ValueError("raster exclusions differ")
    if report["runtime"] != selection_runtime():
        raise ValueError("selection runtime changed; verify on its pinned runtime")
    actual = {
        p.relative_to(output).as_posix()
        for p in output.rglob("*")
        if p.is_file() and p != output / "selection.json"
    }
    if actual != set(report["inventory"]) or actual != {"private/requests.jsonl"}:
        raise ValueError("selection file inventory differs")
    path = inside(output, "private/requests.jsonl")
    if digest(path.read_bytes()) != report["inventory"]["private/requests.jsonl"]:
        raise ValueError("selection bytes differ")
    pilot = read_pilot()
    counts = counts_from_pilot(pilot)
    if report["groups_per_task"] != counts or report["data_seed"] != pilot["data_seed"]:
        raise ValueError("selection differs from checked-in pilot counts/seed")
    requests, selection = select_collection(
        report["data_seed"], counts, exclusions=exclusion_candidates()
    )
    expected = b"".join(canonical_bytes(r) + b"\n" for r in requests)
    if expected != path.read_bytes() or report["selection"] != selection:
        raise ValueError("selection differs from reproducible global reservation")
    summary = check_collection(requests, counts)
    if report["summary"] != summary:
        raise ValueError("selection summary differs")
    if report["source_sha256"] != selection_sources():
        raise ValueError("selection source changed during verification")
    return report
