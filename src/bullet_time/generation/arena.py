"""Deterministic, separately seeded game/appearance/camera specifications."""

import hashlib
import json
import math
import random


def fingerprint(value):
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    ).hexdigest()


def stream(seed, index, name):
    return random.Random(int(fingerprint([seed, index, name])[:16], 16))


def camera_position(camera, phase):
    theta = camera["phase"] + phase
    center = camera["center"]
    return [
        center[0] + camera["radius_x"] * math.cos(theta),
        center[1] + camera["height_amplitude"] * math.sin(2 * theta),
        center[2] + camera["radius_z"] * math.sin(theta),
    ]


def make_request(plan, index):
    if type(index) is not int or not 0 <= index < plan["maximum_grids"]:
        raise ValueError("grid index outside integration plan")
    if (
        plan["schema_version"] != "bullet-time.arena-plan.v1"
        or plan["family"] != "projectile_arena"
        or plan["split"] != "pretrain"
        or plan["physics_hz"] != 64
        or plan["states"] != 16
        or plan["cameras"] != 16
        or plan["image_size"] != 224
        or plan["stride_ticks"] != [16, 8, 4]
    ):
        raise ValueError("unsupported arena integration plan")
    physics = stream(plan["seed"], index, "physics")
    appearance = stream(plan["seed"], index, "appearance")
    view = stream(plan["seed"], index, "camera")
    objects = []

    def box(oid, role, pos, size, color, rigid=False):
        objects.append(
            dict(
                id=oid,
                role=role,
                kind="box",
                position=pos,
                size=size,
                color=color,
                rigid=rigid,
                mass=1.0,
                friction=0.7,
                bounce=0.15,
            )
        )

    floor = [appearance.uniform(0.35, 0.65) for _ in range(3)]
    target = [appearance.uniform(0.3, 0.9) for _ in range(3)]
    box("floor", "floor", [0, -0.2, 0], [9, 0.4, 7], floor)
    for oid, pos, size in [
        ("wall_left", [-4.5, 0.4, 0], [0.2, 0.8, 7]),
        ("wall_right", [4.5, 0.4, 0], [0.2, 0.8, 7]),
        ("wall_back", [0, 0.4, -3.5], [9, 0.8, 0.2]),
        ("wall_front", [0, 0.4, 3.5], [9, 0.8, 0.2]),
    ]:
        box(oid, "wall", pos, size, [0.25, 0.29, 0.34])
    offset = physics.uniform(-0.35, 0.35)
    box("launch_pad", "pad", [-3.0, 0.08, offset], [1.0, 0.16, 1.0], [0.2, 0.4, 0.6])
    box("target_pad", "pad", [1.8, 0.08, 0], [1.6, 0.16, 2.8], [0.45, 0.4, 0.25])
    for column in range(2):
        for level in range(2):
            box(
                f"target_{column}_{level}",
                "target",
                [1.8, 0.16 + 0.4 + 0.81 * level, -0.65 + 1.3 * column],
                [0.8, 0.8, 0.8],
                target,
                True,
            )
    box(
        "obstacle",
        "obstacle",
        [physics.uniform(-0.5, 0.3), 0.5, -1.65],
        [0.65, 1.0, 0.65],
        [0.3, 0.34, 0.42],
    )
    objects.append(
        dict(
            id="projectile",
            role="projectile",
            kind="sphere",
            position=[-3.0, 0.55, offset],
            radius=0.32,
            color=[0.95, appearance.uniform(0.1, 0.3), 0.08],
            rigid=True,
            mass=1.8,
            friction=0.55,
            bounce=0.6,
        )
    )
    camera = dict(
        look_at=[0, 0.55, 0],
        fov_degrees=58.0,
        phase=view.uniform(0, math.tau),
        height_amplitude=view.uniform(0.1, 0.3),
    )
    if index % 2 == 0:
        camera.update(
            kind="orbit",
            center=[0, view.uniform(5.5, 6.5), 0],
            radius_x=view.uniform(8.8, 9.5),
            radius_z=view.uniform(8.5, 9.2),
        )
    else:
        azimuth = view.uniform(0, math.tau)
        camera.update(
            kind="local_oval",
            center=[9.5 * math.cos(azimuth), 6.0, 9.5 * math.sin(azimuth)],
            radius_x=1.0,
            radius_z=0.8,
        )
    camera["poses"] = [camera_position(camera, i * math.tau / 16) for i in range(16)]
    launch = [physics.uniform(5.3, 6.7), physics.uniform(3.0, 4.0), physics.uniform(-0.7, 0.7)]
    layout = [{k: v for k, v in o.items() if k not in {"color"}} for o in objects]
    assets = [{"id": o["id"], "color": o["color"]} for o in objects]
    return dict(
        schema_version="bullet-time.arena-request.v1",
        grid_id=f"arena-{plan['seed']}-{index:04d}",
        seed=plan["seed"],
        index=index,
        scene_family="projectile_arena",
        split="pretrain",
        stride_ticks=plan["stride_ticks"][index % 3],
        start_tick=4,
        launch_tick=physics.randint(5, 15),
        launch_velocity=launch,
        objects=objects,
        camera=camera,
        groups={
            "configuration": fingerprint(layout),
            "asset": fingerprint(assets),
            "trajectory": fingerprint([layout, launch]),
            "rollout": fingerprint([plan["seed"], index, "rollout"]),
        },
        action="scripted launch at target stack; same rigid parameters; no UI or labels in RGB",
    )
