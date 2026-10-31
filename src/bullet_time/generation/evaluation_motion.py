"""Forward controlled arcade trajectories; no rendered pixels or model labels as input.

These are development microtasks, not evidence of visual solvability or gameplay
transfer. Collision reflection and rail release are the same laws in both branches.
"""

import math
import random
from collections import Counter

import numpy as np

from bullet_time.provenance import identity, integer

PHYSICS_HZ = 64
OBSERVATION_STRIDE = 4
QUERY_TICK = 60
FUTURE_TICKS = (16, 32, 64)


def pool(kind, content):
    """Assign content prototypes, never arbitrary episode IDs, before rendering."""
    value = int(identity(["evaluation-pools-v1", kind, content])[:16], 16) % 100
    return (
        "pretrain"
        if value < 40
        else "train"
        if value < 70
        else "dev"
        if value < 85
        else "assessment"
    )


def rotate(point, angle):
    x, y, z = point
    c, s = math.cos(angle), math.sin(angle)
    return [c * x - s * z, y, s * x + c * z]


def sphere(oid, position, radius, color):
    return dict(id=oid, kind="sphere", position=position, radius=radius, color=color)


def box(oid, position, size, color):
    return dict(id=oid, kind="box", position=position, size=size, color=color)


def reflect_steps(initial, velocity, barrier, *, hz=64, seconds=124 / 64):
    """Independent forward time-step integrator for a sphere/immovable-sphere axis.

    Integrate to the actual time of contact, reverse the velocity, then consume the
    remaining substep. Never reverse recorded video or integrate backward in time.
    """
    position = float(initial)
    points, motions, contacts = [position], [], []
    for step in range(1, round(seconds * hz) + 1):
        motion = velocity / hz
        motions.append(motion)
        next_position = position + motion
        if velocity > 0 and next_position >= barrier - 1e-12:
            contact_time = (step - 1) / hz + max(0, (barrier - position) / velocity)
            contacts.append(contact_time)
            next_position = 2 * barrier - next_position
            velocity = -velocity
        position = next_position
        points.append(position)
    return points, motions, contacts


def forecast_candidate(seed, index, task):
    if task not in ("collision", "order"):
        raise ValueError("forecast task required")
    integer(seed, "seed")
    integer(index, "index")
    rng = random.Random(int(identity([seed, task, index])[:16], 16))
    palette = [rng.randrange(32) for _ in range(3)]
    color = [0.18 + x * 0.024 for x in palette]
    angle_bin, camera_bin = rng.randrange(64), rng.randrange(32)
    angle = math.tau * angle_bin / 64
    radius_bin = rng.randrange(4)
    radius = 0.27 + radius_bin * 0.025
    target_radius = 0.38
    objects = [box("floor", [0, -0.15, 0], [12, 0.3, 12], [0.22 + 0.3 * c for c in color])]
    frames, branches, probes = {}, [], []
    if task == "collision":
        speed_bin, contact_bin = rng.randrange(4), rng.randrange(4)
        speed, contact_ticks = 1.5 + speed_bin * 0.5, [12, 20, 24, 28][contact_bin]
        gap = speed * contact_ticks / 64
        target = [gap + radius + target_radius, 0.65, 0]
        trajectory = [task, angle_bin, radius_bin, speed_bin, contact_bin]
        for branch, hit_tick in enumerate([QUERY_TICK + contact_ticks, QUERY_TICK - contact_ticks]):
            initial = gap - speed * hit_tick / 64
            points, motions, contacts = reflect_steps(initial, speed, gap)
            analytic = [gap - abs(speed * (t - hit_tick) / 64) for t in range(125)]
            if not np.allclose(points, analytic, atol=1e-11, rtol=0):
                raise ValueError("independent contact integration disagrees")
            refinements = []
            for hz in (128, 256):
                finer, _, events = reflect_steps(initial, speed, gap, hz=hz)
                if not np.allclose(finer[:: hz // 64], points, atol=1e-11, rtol=0):
                    raise ValueError("time-step refinement changed trajectory")
                refinements.append(events)
            ids = []
            for t in range(0, 61, 4):
                key = "final" if t == 60 else f"b{branch}-t{t:03d}"
                position = rotate([points[t], 0.65, 0], angle)
                if t == 60:
                    position = [0.0, 0.65, 0.0]
                frame = {"projectile": position}
                if key in frames and frames[key] != frame:
                    raise ValueError("final states differ")
                frames[key] = frame
                ids.append(key)
            branches.append(
                dict(
                    branch=branch,
                    observed=ids,
                    history_positions=[rotate([p, 0.65, 0], angle) for p in points[:61]],
                    contacts=contacts,
                    refinement_contacts=refinements,
                    labels={
                        str(t / 64): int(
                            any(QUERY_TICK / 64 < c <= (QUERY_TICK + t) / 64 for c in contacts)
                        )
                        for t in FUTURE_TICKS
                    },
                )
            )
            probes.append(
                dict(
                    branch=branch,
                    radius=radius,
                    positions=[rotate([p, 0.65, 0], angle) for p in points[:-1]],
                    motions=[rotate([m, 0, 0], angle) for m in motions],
                    expected_contact_tick=hit_tick,
                )
            )
        continuation = "elastic_axis_reflection_v1; no post-query action or randomness"
    else:
        rail_bin, distance_bin = rng.randrange(24), rng.randrange(4)
        rail_radius = 0.75 + rail_bin * 0.015
        speed = math.tau * rail_radius
        target = [rail_radius, 0.65, 1.5 + distance_bin * 0.12]
        clearance = math.hypot(target[0], target[2]) - rail_radius - radius - target_radius
        if clearance <= 0:
            raise ValueError("target intersects rail trajectory")
        trajectory = [task, angle_bin, radius_bin, rail_bin, distance_bin]
        # One canonical pose table makes identical physical states identical bytes.
        poses = [
            rotate(
                [
                    rail_radius * math.cos(math.tau * i / 64),
                    0.65,
                    rail_radius * math.sin(math.tau * i / 64),
                ],
                angle,
            )
            for i in range(64)
        ]
        for i in range(0, 64, 4):
            frames[f"pose-{i:02d}"] = {"projectile": poses[i]}
        for branch, direction in enumerate((1, -1)):
            indices = [(direction * (t - QUERY_TICK)) % 64 for t in range(0, 61, 4)]
            ids = [f"pose-{i:02d}" for i in indices]
            gap = target[2] - radius - target_radius
            if direction == 1:
                future, motions, contacts = reflect_steps(0, speed, gap, seconds=1)
            else:
                future = [-speed * t / 64 for t in range(65)]
                motions, contacts = [-speed / 64] * 64, []
            branches.append(
                dict(
                    branch=branch,
                    observed=ids,
                    history_positions=[
                        poses[(direction * (t - QUERY_TICK)) % 64] for t in range(61)
                    ],
                    contacts=[c + QUERY_TICK / 64 for c in contacts],
                    refinement_contacts=[],
                    labels={
                        str(t / 64): int(any(0 < c <= t / 64 for c in contacts))
                        for t in FUTURE_TICKS
                    },
                )
            )
            probes.append(
                dict(
                    branch=branch,
                    radius=radius,
                    positions=[rotate([rail_radius, 0.65, p], angle) for p in future[:-1]],
                    motions=[rotate([0, 0, m], angle) for m in motions],
                    expected_contact_tick=None if not contacts else math.ceil(contacts[0] * 64),
                    tick_offset=QUERY_TICK,
                )
            )
        if Counter(branches[0]["observed"]) != Counter(branches[1]["observed"]):
            raise ValueError("rail image bag differs")
        continuation = "one-second constrained rail; release tangential velocity at tick 60; elastic collision, no new action"
    objects += [
        sphere(
            "projectile",
            [0, 0.65, 0],
            radius,
            [0.85 + 0.1 * color[0], 0.18 + 0.25 * color[1], 0.08 + 0.12 * color[2]],
        ),
        sphere("target", rotate(target, angle), target_radius, [0.15, 0.65, 0.25]),
    ]
    camera = dict(
        position=[0, 10, 0],
        look_at=[0, 0, 0],
        up=rotate([0, 0, -1], math.tau * camera_bin / 32),
        size=9.5,
    )
    prototypes = dict(
        trajectory=trajectory,
        asset=palette,
        configuration=[task, camera_bin, radius_bin, trajectory],
    )
    return dict(
        schema_version="bullet-time.measurement-request.v1",
        task=task,
        index=index,
        physics_hz=64,
        observation_stride=4,
        query_tick=QUERY_TICK,
        objects=objects,
        camera=camera,
        frames=frames,
        branches=branches,
        probes=probes,
        continuation=continuation,
        prototypes=prototypes,
        groups={k: identity([k, v]) for k, v in prototypes.items()},
        assigned_pools={k: pool(k, v) for k, v in prototypes.items()},
        scope="development controlled arena microtask; visual solvability unmeasured",
    )


def select_groups(seed, split, count, task, *, limit=100000):
    if split not in ("train", "dev"):
        raise ValueError("initial generator is train/dev only")
    integer(count, "count", 1)
    selected, seen, considered = [], {k: set() for k in ("trajectory", "asset", "configuration")}, 0
    # No scene, trajectory or appearance prototype recurs within a task drop.
    # The pool map also prevents sharing any prototype across splits.
    for index in range(limit):
        candidate = (
            tracking_candidate(seed, index)
            if task == "tracking"
            else forecast_candidate(seed, index, task)
        )
        considered += 1
        if set(candidate["assigned_pools"].values()) != {split}:
            continue
        if any(candidate["groups"][k] in seen[k] for k in ("trajectory", "asset", "configuration")):
            continue
        for k in seen:
            seen[k].add(candidate["groups"][k])
        gid = f"{task}-{identity([seed, task, index])[:16]}"
        candidate.update(group_id=gid, split=split)
        selected.append(candidate)
        if len(selected) == count:
            return selected, {
                "candidates_considered": considered,
                "accepted": count,
                "selection": "content pool and duplicate prototype checks only; no model outcomes",
            }
    raise ValueError(
        "insufficient disjoint prototypes; change the development version, never silently shrink"
    )


def tracking_candidate(seed, index):
    """Two identical drones fly below a roof at distinct noncolliding heights.

    The tracked surface point is the sphere's fixed top pole. A common orthographic
    camera and disabled shadows make height unavailable as an identity shortcut.
    Constant motion before/during/after occlusion supplies the temporal cue.
    """
    rng = random.Random(int(identity([seed, "tracking", index])[:16], 16))
    palette = [rng.randrange(32) for _ in range(3)]
    color = [0.18 + x * 0.024 for x in palette]
    entry_bin, exit_bin = rng.randrange(64), rng.randrange(32)
    entry = 0.45 + 0.004 * entry_bin
    exit_position = 0.7 + 0.008 * exit_bin
    entry_sign, exit_sign = rng.choice((-1, 1)), rng.choice((-1, 1))
    camera_bin = rng.randrange(32)
    radius = 0.35
    frames = {}
    for frame in range(28):
        x = entry_sign * entry + (frame - 16) / 9 * (exit_sign * exit_position - entry_sign * entry)
        z = -1.125 + (frame - 16) * 0.25
        frames[f"frame-{frame:02d}"] = {"projectile": [x, 0.55, z], "distractor": [-x, 1.45, z]}
    objects = [
        box("floor", [0, -0.15, 0], [14, 0.3, 14], [0.22 + 0.3 * c for c in color]),
        box("roof", [0, 2.5, 0], [3.4, 0.3, 2.0], [0.25, 0.3, 0.42]),
        sphere(
            "projectile",
            frames["frame-00"]["projectile"],
            radius,
            [0.85 + 0.1 * color[0], 0.18 + 0.25 * color[1], 0.08 + 0.12 * color[2]],
        ),
        sphere(
            "distractor",
            frames["frame-00"]["distractor"],
            radius,
            [0.85 + 0.1 * color[0], 0.18 + 0.25 * color[1], 0.08 + 0.12 * color[2]],
        ),
    ]
    prototypes = dict(
        trajectory=["tracking", entry_bin, exit_bin, entry_sign, exit_sign],
        asset=palette,
        configuration=["tracking", camera_bin, entry_bin, exit_bin, entry_sign, exit_sign],
    )
    return dict(
        schema_version="bullet-time.measurement-request.v1",
        task="tracking",
        index=index,
        physics_hz=64,
        observation_stride=4,
        frames=frames,
        objects=objects,
        camera=dict(
            position=[0, 10, 0],
            look_at=[0, 0, 0],
            up=rotate([0, 0, -1], math.tau * camera_bin / 32),
            size=10.5,
        ),
        probes=[],
        branches=[],
        continuation="constant controlled drone velocity; no actions or randomness",
        tracking=dict(
            reference_frame=16,
            auxiliary_frame=17,
            primary_frames=[25, 26, 27],
            local_surface_point=[0, radius, 0],
            normal=[0, 1, 0],
            minimum_physical_clearance=1.45 - 0.55 - 2 * radius,
        ),
        prototypes=prototypes,
        groups={k: identity([k, v]) for k, v in prototypes.items()},
        assigned_pools={k: pool(k, v) for k, v in prototypes.items()},
        scope="development controlled arena microtask; visual solvability unmeasured",
    )
