"""Fail-explicit prediction exports, with expected keys independent of successes."""
import csv
from pathlib import Path
from bullet_time.provenance import atomic_json, digest, fields, number, integer, identity, sha256, text_id

KEY=('run_id','checkpoint_id','task_id','label_budget','readout_seed','episode_or_video_id','query_id','horizon_or_frame')
COLUMNS=KEY+('split','scene_family','pair_group_id','target_reference_sha256','prediction_role',
             'status','error','contact_probability','x','y','visibility_probability','class_id')
OUTPUTS=('contact_probability','x','y','visibility_probability','class_id')


def key_of(row):
    return tuple(str(row[k]) for k in KEY)


def write_predictions(directory,expected,observed,run_metadata):
    """expected rows must be generated from the full declared input/run inventory."""
    directory=Path(directory)
    if directory.exists() and any(directory.iterdir()): raise ValueError('prediction output must be new/empty')
    directory.mkdir(parents=True,exist_ok=True)
    expected_by_key={}
    required=set(COLUMNS)-set(OUTPUTS)-{'status','error'}
    for row in expected:
        fields(row,required)
        for name in KEY: text_id(str(row[name]),name)
        sha256(row['target_reference_sha256'])
        key=key_of(row)
        if key in expected_by_key: raise ValueError('duplicate expected prediction key')
        expected_by_key[key]=dict(row)
    if not expected_by_key: raise ValueError('empty expected coverage')
    observed_by_key={}
    for row in observed:
        fields(row,set(KEY)|{'status','error'},set(OUTPUTS))
        key=key_of(row)
        if key in observed_by_key or key not in expected_by_key: raise ValueError('duplicate/unplanned output')
        status=row['status'];task=row['task_id']
        if status not in ('ok','failed','missing'): raise ValueError('unknown prediction status')
        needed={'contact_probability'} if task in ('collision','order') else {'x','y','visibility_probability'} if task=='tracking' else {'class_id'} if task=='ssv2' else None
        if needed is None: raise ValueError('unknown task')
        present={k for k in OUTPUTS if row.get(k) not in (None,'')}
        if status=='ok':
            if row['error'] or present!=needed: raise ValueError('incomplete/extraneous successful outputs')
            for name in needed:
                if name=='class_id': integer(row[name],'class_id')
                else: number(row[name],name,0,1)
        elif not row['error'] or present:
            raise ValueError('failure requires reason and blank outputs')
        observed_by_key[key]=row
    rows=[];missing=failed=0
    for key,expected_row in expected_by_key.items():
        row={column:'' for column in COLUMNS};row.update(expected_row)
        actual=observed_by_key.get(key)
        if actual is None:
            row.update(status='missing',error='planned prediction not delivered')
        else: row.update(actual)
        missing+=row['status']=='missing';failed+=row['status']=='failed';rows.append(row)
    path=directory/'predictions.csv'
    with path.open('x',newline='') as file:
        writer=csv.DictWriter(file,fieldnames=COLUMNS);writer.writeheader();writer.writerows(rows)
    coverage={'expected_keys':[list(k) for k in expected_by_key],'expected':len(rows),
              'ok':len(rows)-missing-failed,'failed':failed,'missing':missing,
              'complete':not(missing or failed),'csv_sha256':digest(path.read_bytes())}
    atomic_json(directory/'coverage.json',coverage)
    metadata=dict(run_metadata)
    metadata.update(schema_version='bullet-time.run.v1',prediction_schema_version='bullet-time.prediction.v1',
                    csv_sha256=coverage['csv_sha256'],coverage_sha256=digest((directory/'coverage.json').read_bytes()))
    atomic_json(directory/'run.json',metadata)
    return coverage
