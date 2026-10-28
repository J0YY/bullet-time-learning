#!/usr/bin/env python3
"""Validate prospective pilot accounting; no data, model, or science execution."""

import argparse
import copy
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]


def require(condition, message):
    if not condition:
        raise ValueError(message)


def positive_int(value):
    return type(value) is int and value > 0


def unique(values):
    return bool(values) and len(values) == len(set(values))


def validate(p):
    require(p['schema_version'] == 'bullet-time.pilot-plan.v1', 'Unknown plan version')
    require(p['status'] == 'planning_only_not_a_training_configuration', 'Not a runtime config')
    require(p['resource_policy']['launch_authorized'] is False, 'Plan cannot authorize jobs')
    require(p['objective'] == 'videomae_raw_rgb', 'Pilot is one raw-RGB VideoMAE objective')
    require(p['grid_shape'] == [16, 16] and p['rgb_shape'] == [224, 224, 3], 'Wrong grid/RGB shape')
    require(p['observed_frames'] == 16, 'Expected 16 observed frames')
    for key in ('physics_hz', 'evaluation_hz', 'pretraining_grids', 'grids_per_update', 'total_passes'):
        require(positive_int(p[key]), f'{key} must be a positive integer')
    require(p['physics_hz'] % p['evaluation_hz'] == 0, 'RGB cadence must divide physics cadence')
    horizons = p['forecast_horizon_seconds']
    require(unique(horizons) and all(h > 0 for h in horizons), 'Invalid horizons')
    require(p['primary_horizon_seconds'] in horizons, 'Primary horizon missing')
    require(all(float(h * p['physics_hz']).is_integer() for h in horizons), 'Fractional physics horizon')
    for key in ('pretraining_seeds', 'readout_seeds'):
        require(unique(p[key]) and all(positive_int(s) for s in p[key]), f'Invalid {key}')
    conditions = p['conditions']
    require(unique(conditions), 'Duplicate conditions')
    require(set(conditions) == {'view', 'time', 'mix50', 'joint', 'shuffled_time', 'regrouped'},
            'Pilot requires the six declared arms')
    require(unique(p['checkpoint_passes']) and p['checkpoint_passes'] == sorted(p['checkpoint_passes']),
            'Checkpoints must be unique and sorted')
    require(all(positive_int(c) and c % 4 == 0 for c in p['checkpoint_passes']),
            'Checkpoints must finish four-pass cycles')
    require(p['checkpoint_passes'][-1] == p['total_passes'], 'Final checkpoint mismatch')
    require(p['pretraining_grids'] % p['grids_per_update'] == 0, 'Full pilot must have complete updates')
    handoffs = p['grid_handoffs']
    require(handoffs == sorted(set(handoffs)) and all(positive_int(n) for n in handoffs),
            'Grid handoffs must be increasing unique counts')
    require(handoffs[0] == 1 and p['grids_per_update'] in handoffs and 100 in handoffs,
            'Need preview, first-update and 100-grid audit drops')
    require(handoffs[-1] == p['pretraining_grids'], 'Final handoff mismatch')
    require(100 % p['grids_per_update'] == p['renderer_audit_tail_grids'], 'Wrong audit tail')
    early = p['early_screen']
    require(unique(early['conditions']) and set(early['conditions']) <= set(conditions),
            'Early slots must be unique included conditions')
    require(early['seed'] in p['pretraining_seeds'], 'Early seed must be in main pilot slots')
    require(early['passes'] in p['checkpoint_passes'] and early['passes'] < p['total_passes'],
            'Early screen is an included intermediate checkpoint')
    tasks = p['frozen_readout_tasks']
    require(unique(tasks) and set(tasks) == {'collision', 'order', 'tracking', 'ssv2'}, 'Readout tasks mismatch')
    require(set(p['evaluation_sets']) == set(tasks) - {'ssv2'}, 'Game set inventory mismatch')
    budgets = p['game_label_budgets']
    require(budgets == sorted(set(budgets)) and all(positive_int(b) for b in budgets), 'Invalid budgets')
    require(p['pilot_game_label_budget'] in budgets, 'Pilot label budget not in nested sets')
    for task, record in p['evaluation_sets'].items():
        require(record['unit'] == 'episode', f'{task}: counts must be episodes')
        pair_size = 1 if task == 'tracking' else 2
        require(record['pair_size'] == pair_size, f'{task}: wrong group size')
        for split in ('train', 'dev', 'assessment'):
            require(positive_int(record[split]) and record[split] % pair_size == 0,
                    f'{task}/{split}: must contain complete groups')
        require(all(b <= record['train'] and b % pair_size == 0 for b in budgets),
                f'{task}: label budgets exceed train or split pairs')
    for key in ('external_dev_fraction', 'external_label_fraction'):
        require(0 < p[key] < 1, f'Invalid {key}')
    support = p['support']
    require(unique(support['native_conditions']) and set(support['native_conditions']) == {'view', 'time'},
            'Native diagnostics need View and Time')
    require(unique(support['native_seeds']) and set(support['native_seeds']) <= set(p['pretraining_seeds']),
            'Native seeds must be paired')
    for key in ('image_mae_seeds', 'untrained_seeds'):
        require(unique(support[key]) and set(support[key]) == set(p['pretraining_seeds']),
                f'{key} must cover paired seeds')
    require(positive_int(support['external_image_checkpoints']) and positive_int(support['supervised_diagnostic_fits']),
            'Reference counts must be positive')

    n_runs = len(conditions) * len(p['pretraining_seeds'])
    clips_per_pass = p['pretraining_grids'] * 16
    clips_per_run = clips_per_pass * p['total_passes']
    steps_per_run = p['pretraining_grids'] // p['grids_per_update'] * p['total_passes']
    early_slots = len(early['conditions'])
    heads_per_checkpoint = len(tasks) * len(p['readout_seeds'])
    native_runs = len(support['native_conditions']) * len(support['native_seeds'])
    heads = {
        'controlled': (n_runs + early_slots) * heads_per_checkpoint,
        'native': native_runs * heads_per_checkpoint,
        'image_mae': len(support['image_mae_seeds']) * heads_per_checkpoint,
        'untrained': len(support['untrained_seeds']) * heads_per_checkpoint,
        'external_image': support['external_image_checkpoints'] * heads_per_checkpoint,
    }
    return {
        'scope': 'Planning arithmetic only; no models, data or producer/consumer integration validated',
        'controlled_runs': n_runs,
        'included_early_slots': early_slots,
        'native_training_runs': native_runs,
        'image_mae_training_runs': len(support['image_mae_seeds']),
        'supervised_diagnostic_fits': support['supervised_diagnostic_fits'],
        'frozen_head_fits': heads,
        'total_frozen_head_fits': sum(heads.values()),
        'pretraining_rgb_images': p['pretraining_grids'] * 256,
        'pretraining_rgb_bytes': p['pretraining_grids'] * 256 * 224 * 224 * 3,
        'clips_per_pass': clips_per_pass,
        'clips_per_controlled_run': clips_per_run,
        'controlled_clips_total': n_runs * clips_per_run,
        'updates_per_controlled_run': steps_per_run,
        'controlled_updates_total': n_runs * steps_per_run,
        'controlled_gpu_hours_scenarios': {str(rate): n_runs * clips_per_run / rate / 3600 for rate in (20, 100)},
        'frames_per_image_mae_run': p['pretraining_grids'] * 256 * p['total_passes'],
        'future_physics_steps': [int(h * p['physics_hz']) for h in horizons],
        'observed_span_seconds': (p['observed_frames'] - 1) / p['evaluation_hz'],
        'game_group_counts': {task: {split: v[split] // v['pair_size'] for split in ('train', 'dev', 'assessment')}
                              for task, v in p['evaluation_sets'].items()},
    }


def rejection_checks(plan):
    mutations = [
        lambda p: p['conditions'].append('view'),
        lambda p: p['early_screen'].update(seed=999),
        lambda p: p['early_screen'].update(passes=20),
        lambda p: p['evaluation_sets']['collision'].update(train=601),
        lambda p: p.update(pilot_game_label_budget=301),
        lambda p: p.update(grids_per_update=7),
        lambda p: p.update(renderer_audit_tail_grids=0),
        lambda p: p.update(physics_hz=60),
        lambda p: p['resource_policy'].update(launch_authorized=True),
        lambda p: p['readout_seeds'].append(101),
        lambda p: p['checkpoint_passes'].append(21),
        lambda p: p['support'].update(untrained_seeds=[17]),
    ]
    for mutate in mutations:
        candidate = copy.deepcopy(plan)
        mutate(candidate)
        try:
            validate(candidate)
        except ValueError:
            continue
        raise ValueError('Malformed-plan rejection check failed')
    return len(mutations)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--plan', type=Path, default=ROOT / 'configs/pilot-plan.json')
    parser.add_argument('--self-test', action='store_true', help='Also check rejection of malformed plans')
    parser.add_argument('--check-report', action='store_true', help='Require stored audit to match current sources')
    args = parser.parse_args()
    p = json.loads(args.plan.read_text())
    output = validate(p)
    output['source_sha256'] = {str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest()
                               for path in (ROOT / 'SPEC.md', ROOT / 'docs/pilot-plan.md', ROOT / 'docs/interfaces.md',
                                            ROOT / 'division-of-labor.md', Path(__file__).resolve())}
    output['plan_sha256'] = hashlib.sha256(args.plan.read_bytes()).hexdigest()
    if args.self_test or args.check_report:
        output['malformed_plan_rejection_checks'] = rejection_checks(p)
    if args.check_report:
        recorded = json.loads((ROOT / 'reports/pilot-plan-audit.json').read_text())
        require(recorded == output, 'Stored pilot audit is stale; regenerate with --self-test after review')
    print(json.dumps(output, indent=2, sort_keys=True))


if __name__ == '__main__':
    try:
        main()
    except (OSError, ValueError, KeyError, TypeError, AttributeError) as exc:
        print(f'FAIL: {exc}', file=sys.stderr)
        sys.exit(1)
