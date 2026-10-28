import json
from dataclasses import asdict,replace
from pathlib import Path
import subprocess
import sys
from bullet_time.training.runner import TrainConfig
from bullet_time.models.video import ModelConfig


def run(*args,ok=True):
    result=subprocess.run([sys.executable,'-m','bullet_time.cli',*map(str,args)],capture_output=True,text=True)
    assert (result.returncode==0)==ok,result.stderr
    return json.loads(result.stdout) if ok else result.stderr


def test_fixture_cli_checkpoint_and_resume(tmp_path):
    fixture=run('make-fixture','--output',tmp_path/'data','--grids',8)
    manifest=fixture['manifest']
    assert run('verify-corpus','--manifest',manifest,'--image-size',32)['images']==2048
    config=tmp_path/'train.json';config.write_text(json.dumps(asdict(TrainConfig(total_passes=4,warmup_passes=1,microbatch_clips=4))))
    model=Path(__file__).resolve().parents[2]/'configs/models/videomae-test.json'
    common=['--manifest',manifest,'--model-config',model,'--training-config',config,'--scope','synthetic']
    first=run('train',*common,'--output',tmp_path/'run-a','--stop-after-updates',1)
    second=run('train',*common,'--output',tmp_path/'run-b','--stop-after-updates',2,'--resume',first['latest_checkpoint'])
    assert first['global_step']==1 and second['global_step']==2 and second['fixed_budget_steps']==4
    assert 'admission' in run('train','--manifest',manifest,'--model-config',model,'--training-config',config,
        '--scope','pilot_full','--output',tmp_path/'forbidden','--stop-after-updates',2,ok=False)
    assert not (tmp_path/'forbidden').exists()
    assert 'File exists' in run('train',*common,'--output',tmp_path/'run-a','--stop-after-updates',1,ok=False)
