"""Private prospective assessment requests; no rendering, scoring or release.

Fresh private randomness derives a candidate stream under the master data seed.
Existing measurement and prior assessment content is explicitly reserved. Shared
pretraining lineage and actual cross-pool RGB checks remain separate admissions.
"""

from collections import Counter
from pathlib import Path
import secrets
import platform

import numpy as np

from bullet_time.provenance import (
    atomic_json,
    canonical_bytes,
    digest,
    fields,
    identity,
    integer,
    sha256,
    strict_json,
)
from .bundle import ROOT
from .evaluation_motion import (
    forecast_candidate,
    tracking_candidate,
    tracking_background,
    background_conflict,
)

TASKS = ("collision", "order", "tracking")
KINDS = ("trajectory", "asset", "configuration")
SCHEMA = "bullet-time.private-assessment-selection.v1"


def source_binding():
    paths = [
        "src/bullet_time/generation/assessment_selection.py",
        "src/bullet_time/generation/evaluation_motion.py",
        "src/bullet_time/provenance.py",
        "configs/pilot-plan.json",
        "scripts/data/plan_assessment.py",
    ]
    return {
        "files": {name: digest((ROOT / name).read_bytes()) for name in paths},
        "runtime": {
            "python": platform.python_version(),
            "numpy": np.__version__,
            "platform": platform.platform(),
        },
    }


def pilot_counts():
    pilot = strict_json((ROOT / "configs/pilot-plan.json").read_bytes())
    counts = {}
    for task in TASKS:
        row = pilot["evaluation_sets"][task]
        unit = 1 if task == "tracking" else 2
        if row["pair_size"] != unit or row["assessment"] != 400:
            raise ValueError("version this producer before changing assessment counts")
        counts[task] = 400 // unit
    return integer(pilot["data_seed"], "master seed"), counts


def candidate(seed, task, index, split):
    result = (
        tracking_candidate(seed, index)
        if task == "tracking"
        else forecast_candidate(seed, index, task)
    )
    result.update(group_id=f"{task}-{identity([seed, task, index])[:16]}", split=split)
    return result


def read_known(sources):
    """Validate exact request bytes and reconstruction, without repeating RGB checks.

    Callers must include all prior assessment selections in this pilot lineage.
    The later release adapter must match this declared set to its version registry.
    """
    if not isinstance(sources, list) or not sources:
        raise ValueError("known measurement sources required")
    requests, bindings, required_prior = [], [], set()
    seen = set()
    has_development = False
    for source in sources:
        fields(source, {"path", "sha256"})
        path = Path(source["path"]).resolve(strict=True)
        checksum = sha256(source["sha256"])
        raw = path.read_bytes()
        if digest(raw) != checksum or checksum in seen:
            raise ValueError("known receipt changed or was listed twice")
        seen.add(checksum)
        report = strict_json(raw)
        root = path.parent
        schema = report["schema_version"]
        if schema == "bullet-time.measurement-bundle.v1":
            has_development = True
            seed = report["plan"]["seed"]
            rows = []
            names = sorted(
                name
                for name in report["inventory"]
                if name.startswith("private/") and name.endswith("/request.json")
            )
            for name in names:
                target = root / name
                # Never follow paths outside the explicitly declared private bundle.
                if target.resolve(strict=True).is_relative_to(root) is False:
                    raise ValueError("known request escapes source root")
                data = target.read_bytes()
                if digest(data) != report["inventory"][name]:
                    raise ValueError("known request bytes changed")
                rows.append(strict_json(data))
            expected = report["plan"]["groups_per_task"]
            if report["plan"]["schema_version"] == "bullet-time.measurement-plan.v1":
                expected = {task: expected for task in TASKS}
            if Counter((r["task"], r["split"]) for r in rows) != {
                (task, split): n for task, splits in expected.items() for split, n in splits.items()
            }:
                raise ValueError("known measurement request inventory is incomplete")
            if any(r["split"] not in ("train", "dev") for r in rows):
                raise ValueError("known development bundle contains another split")
        elif schema == SCHEMA:
            for name in ("private-config.json", "requests.jsonl"):
                if digest((root / name).read_bytes()) != report["inventory"][name]:
                    raise ValueError("prior assessment selection changed")
            config = strict_json((root / "private-config.json").read_bytes())
            seed = config["candidate_seed"]
            required_prior.update(r["sha256"] for r in config["known_sources"])
            rows = [
                strict_json(line) for line in (root / "requests.jsonl").read_bytes().splitlines()
            ]
            if Counter(r["task"] for r in rows) != report["groups_per_task"] or any(
                r["split"] != "assessment" for r in rows
            ):
                raise ValueError("prior assessment request inventory is incomplete")
        else:
            raise ValueError("unsupported known measurement receipt")
        for row in rows:
            if row["task"] not in TASKS or row != candidate(
                seed, row["task"], row["index"], row["split"]
            ):
                raise ValueError("known request does not reconstruct from actual content")
            if set(row["assigned_pools"].values()) != {row["split"]}:
                raise ValueError("known prototype is assigned to another split")
        requests.extend(rows)
        bindings.append(
            {
                "path": str(path),
                "sha256": checksum,
                "request_content_sha256": identity(rows),
                "groups": len(rows),
            }
        )
    if not has_development or not required_prior <= seen:
        raise ValueError("include development and every prior selection dependency")
    return requests, bindings


def select_requests(seed, known, counts, *, limit=200000):
    integer(seed, "candidate seed")
    if set(counts) != set(TASKS):
        raise ValueError("all assessment tasks required")
    reserved = {kind: {r["groups"][kind] for r in known} for kind in KINDS}
    backgrounds = [tracking_background(r) for r in known if r["task"] == "tracking"]
    selected, stats = [], {}
    for task in TASKS:
        wanted = integer(counts[task], "group count", 1)
        accepted, background_rejections = 0, 0
        for index in range(limit):
            row = candidate(seed, task, index, "assessment")
            if set(row["assigned_pools"].values()) != {"assessment"}:
                continue
            if any(row["groups"][kind] in reserved[kind] for kind in KINDS):
                continue
            if task == "tracking" and any(
                background_conflict(tracking_background(row), b) for b in backgrounds
            ):
                background_rejections += 1
                continue
            selected.append(row)
            for kind in KINDS:
                reserved[kind].add(row["groups"][kind])
            accepted += 1
            if accepted == wanted:
                stats[task] = {
                    "accepted": accepted,
                    "candidates_considered": index + 1,
                    "background_rejections": background_rejections,
                }
                break
        else:
            raise ValueError("insufficient disjoint assessment content; never shrink counts")
    return selected, stats


def _config(master, nonce, sources):
    sha256(nonce)
    return {
        "master_data_seed": master,
        "private_nonce": nonce,
        "candidate_seed": int(identity(["assessment-private-stream-v1", master, nonce]), 16),
        "known_sources": sources,
    }


def _report(output, before, counts, bindings, rows, stats):
    return {
        "schema_version": SCHEMA,
        "scope": "private prospective assessment only; no capture, RGB/joint-lineage admission or release",
        "source_binding": before,
        "groups_per_task": counts,
        "known_bindings": bindings,
        "selection": stats,
        "request_content_sha256": identity(rows),
        "episodes": sum(counts[t] * (1 if t == "tracking" else 2) for t in TASKS),
        "prospective_rgb_images": sum(len(row["frames"]) for row in rows),
        "inventory": {
            name: digest((output / name).read_bytes())
            for name in ("private-config.json", "requests.jsonl")
        },
        "assessment_authorized": False,
        "scientific_gate_pass": False,
    }


def plan_assessment(output, known_sources):
    output = Path(output)
    if output.exists() or output.is_symlink():
        raise ValueError("new private assessment selection directory required")
    before = source_binding()
    master, counts = pilot_counts()
    known, bindings = read_known(known_sources)
    sources = [{"path": b["path"], "sha256": b["sha256"]} for b in bindings]
    config = _config(master, secrets.token_hex(32), sources)
    output.mkdir(parents=True, mode=0o700, exist_ok=False)
    atomic_json(output / "private-config.json", config)
    rows, stats = select_requests(config["candidate_seed"], known, counts)
    # Private requests contain original identifiers, states, branch outcomes and RNG.
    path = output / "requests.jsonl"
    with path.open("xb") as stream:
        path.chmod(0o600)
        stream.write(b"".join(canonical_bytes(row) + b"\n" for row in rows))
    if source_binding() != before or read_known(sources)[1] != bindings:
        raise ValueError("selection source or known request bytes changed")
    report = _report(output, before, counts, bindings, rows, stats)
    atomic_json(output / "selection.json", report)
    return report


def verify_selection(output):
    output = Path(output)
    if output.is_symlink() or any(p.is_symlink() for p in output.rglob("*")):
        raise ValueError("private selection cannot contain symlinks")
    if {p.name for p in output.iterdir()} != {
        "selection.json",
        "private-config.json",
        "requests.jsonl",
    }:
        raise ValueError("private selection inventory differs")
    if output.stat().st_mode & 0o077 or any(p.stat().st_mode & 0o077 for p in output.iterdir()):
        raise ValueError("private reconstruction material is readable outside its owner")
    before = source_binding()
    report = strict_json((output / "selection.json").read_bytes())
    if report["schema_version"] != SCHEMA or report["source_binding"] != source_binding():
        raise ValueError("assessment selection source changed")
    for name in ("private-config.json", "requests.jsonl"):
        if digest((output / name).read_bytes()) != report["inventory"][name]:
            raise ValueError("private assessment selection bytes changed")
    config = strict_json((output / "private-config.json").read_bytes())
    master, counts = pilot_counts()
    if config != _config(master, config["private_nonce"], config["known_sources"]):
        raise ValueError("private candidate stream differs from master/nonce")
    known, bindings = read_known(config["known_sources"])
    rows, stats = select_requests(config["candidate_seed"], known, counts)
    actual = [strict_json(line) for line in (output / "requests.jsonl").read_bytes().splitlines()]
    if source_binding() != before or read_known(config["known_sources"])[1] != bindings:
        raise ValueError("source or known requests changed during verification")
    if rows != actual or report != _report(output, before, counts, bindings, rows, stats):
        raise ValueError("assessment selection does not reconstruct")
    return report
