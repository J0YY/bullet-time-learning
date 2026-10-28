"""Exact-image constructions with balanced four-pass assignments, independent RNGs."""
from collections import Counter, defaultdict
from dataclasses import dataclass
import random
from bullet_time.provenance import integer, seed_for

CONDITIONS = ('view', 'mix25', 'mix50', 'mix75', 'time', 'joint', 'shuffled_time', 'regrouped')
FRACTIONS = {'view': 0, 'mix25': 1, 'mix50': 2, 'mix75': 3, 'time': 4}


@dataclass(frozen=True)
class Schedule:
    grid_id: str
    condition: str
    pass_index: int
    orientation: str
    direction: int
    phase: int
    clips: tuple[tuple[tuple[int, int], ...], ...]


def grid_order(grids, seed, pass_index):
    integer(pass_index, 'pass_index')
    # Same order within a four-pass cycle permits prefix-balanced orientation ranks.
    return tuple(sorted(grids, key=lambda g: (seed_for(seed, 'order', pass_index // 4, g.grid_id), g.grid_id)))


def family_ranks(grids, seed, pass_index):
    counts, ranks = defaultdict(int), {}
    for grid in grid_order(grids, seed, pass_index):
        ranks[grid.grid_id] = counts[grid.scene_family]
        counts[grid.scene_family] += 1
    return ranks


def construct(grid, condition, pass_index, seed, family_rank):
    if condition not in CONDITIONS:
        raise ValueError('unknown condition')
    integer(pass_index, 'pass_index')
    integer(family_rank, 'family_rank')
    cycle, p = divmod(pass_index, 4)
    offset = seed_for(seed, 'orientation', cycle, grid.scene_family) % 4
    orientation = condition
    if condition in FRACTIONS:
        orientation = 'time' if (family_rank + offset + p) % 4 < FRACTIONS[condition] else 'view'
    direction = 1 if (family_rank + pass_index + seed_for(seed, 'direction', grid.scene_family)) % 2 else -1
    phase = seed_for(seed, 'view-phase', pass_index, grid.grid_id) % 16
    time = [[(t, c) for t in range(16)] for c in range(16)]
    if orientation == 'view':
        clips = [[(t, (phase + direction * c) % 16) for c in range(16)] for t in range(16)]
    elif orientation == 'time':
        clips = time
    elif orientation == 'joint':
        clips = [[(t, (direction * t + k) % 16) for t in range(16)] for k in range(16)]
    elif orientation == 'shuffled_time':
        clips = time
        for c, clip in enumerate(clips):
            random.Random(seed_for(seed, 'shuffle-time', grid.grid_id, pass_index, c)).shuffle(clip)
    else:
        cells = [(t, c) for t in range(16) for c in range(16)]
        random.Random(seed_for(seed, 'regroup', grid.grid_id, pass_index)).shuffle(cells)
        clips = [cells[i:i+16] for i in range(0, 256, 16)]
    result = Schedule(grid.grid_id, condition, pass_index, orientation, direction, phase,
                      tuple(tuple(clip) for clip in clips))
    validate_schedule(result)
    return result


def validate_schedule(schedule):
    cells = Counter(cell for clip in schedule.clips for cell in clip)
    expected = Counter((t, c) for t in range(16) for c in range(16))
    if len(schedule.clips) != 16 or any(len(c) != 16 for c in schedule.clips) or cells != expected:
        raise ValueError('schedule must partition all 256 cells exactly once')


def updates(grids, seed, pass_index, grids_per_update=8):
    integer(grids_per_update, 'grids_per_update', 1)
    ordered = grid_order(grids, seed, pass_index)
    return tuple(ordered[i:i + grids_per_update] for i in range(0, len(ordered), grids_per_update))
