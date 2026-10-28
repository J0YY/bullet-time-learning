"""Explicit local commands; no automatic experiment launch or dataset download."""
import argparse
from dataclasses import asdict
import json
from pathlib import Path
import sys
import traceback
import torch
from bullet_time.provenance import strict_json,atomic_json,digest
from bullet_time.loading.manifest import Corpus
from bullet_time.models.video import ModelConfig,build_model,model_identity
from bullet_time.training.runner import Runner,TrainConfig
from bullet_time.training.admission import admit


def read_config(path, cls):
    return cls(**strict_json(Path(path).read_bytes()))


def new_output(path):
    path=Path(path)
    path.mkdir(parents=True,exist_ok=False)
    return path


def load_backbone(checkpoint):
    path=Path(checkpoint);meta=strict_json(Path(str(path)+'.json').read_bytes())
    if digest(path.read_bytes())!=meta['sha256']: raise ValueError('backbone checkpoint hash mismatch')
    payload=torch.load(path,map_location='cpu',weights_only=True)
    if payload.get('schema_version')!='bullet-time.checkpoint.v1': raise ValueError('unknown backbone checkpoint')
    config=ModelConfig(**payload['binding']['model'])
    model=build_model(config,payload['binding']['training']['seed'])
    model.load_state_dict(payload['model'],strict=True)
    if model_identity(model)!=meta['model_sha256']: raise ValueError('backbone parameter hash mismatch')
    return model,{'checkpoint_sha256':meta['sha256'],'binding':payload['binding'],'global_step':payload['global_step']}


def command_train(args):
    model_config=read_config(args.model_config,ModelConfig);training=read_config(args.training_config,TrainConfig)
    model_config.validate();training.validate()
    corpus=Corpus(args.manifest,image_size=model_config.image_size)
    admission=admit(corpus,model_config,training,args.scope,receipt_path=args.admission,stop_after_updates=args.stop_after_updates)
    runner=Runner(corpus,model_config,training)
    if args.resume: runner.resume(args.resume)
    stop=args.stop_after_updates
    if stop is None: stop=runner.global_step+1
    if stop<=runner.global_step or stop>runner.total_steps: raise ValueError('stop must be an absolute later step within fixed budget')
    output=new_output(args.output)
    run_record={'schema_version':'bullet-time.run.v1','status':'running',
        'run_id':runner.binding_sha256,'objective':'image_mae' if model_config.frames==1 else 'videomae',
        'condition':'image_only' if model_config.frames==1 else training.condition,
        'recipe':training.recipe,'paired_pretraining_seed':training.seed,
        'binding':runner.binding,'binding_sha256':runner.binding_sha256,'admission':admission,
        'initial_step':runner.global_step,'stop_after_updates':stop,
        'resume_source':str(Path(args.resume).resolve()) if args.resume else None}
    atomic_json(output/'run.json',run_record)
    try:
        with (output/'updates.jsonl').open('x') as log:
            while runner.global_step<stop:
                event=runner.step(detailed_audit=args.detailed_audit)
                log.write(json.dumps(event,sort_keys=True,allow_nan=False)+'\n');log.flush()
                runner.save(output/f'step-{runner.global_step:06d}.pt')
        result={'status':'completed_requested_segment','scope':args.scope,'global_step':runner.global_step,
                'fixed_budget_steps':runner.total_steps,'binding_sha256':runner.binding_sha256,
                'latest_checkpoint':str((output/f'step-{runner.global_step:06d}.pt').resolve()),
                'updates_sha256':digest((output/'updates.jsonl').read_bytes()),'scientific_gate_pass':False}
        atomic_json(output/'result.json',result)
        run_record.update(status=result['status'],completed_step=runner.global_step,updates_sha256=result['updates_sha256'])
        atomic_json(output/'run.json',run_record)
        return result
    except BaseException as exc:
        run_record.update(status='failed',last_completed_step=runner.global_step)
        atomic_json(output/'run.json',run_record)
        atomic_json(output/'failure.json',{'status':'failed','last_completed_step':runner.global_step,
            'error':str(exc),'exception_type':type(exc).__name__})
        raise


def command_fit(args):
    from bullet_time.evaluation.inputs import ImageStore,EvaluationInputs
    from bullet_time.evaluation.training import ReadoutConfig,Targets,build_readout,fit,predict
    config=read_config(args.readout_config,ReadoutConfig);config.validate()
    store=ImageStore(args.images);inputs=EvaluationInputs(args.inputs,store)
    targets=Targets(args.labels,inputs,classes=config.classes)
    backbone,source=load_backbone(args.backbone)
    if config.image_size!=backbone.bt_config.image_size: raise ValueError('readout/backbone geometry mismatch')
    model=build_readout(backbone,config)
    output=new_output(args.output)
    try:
        report=fit(model,inputs,targets,config)
        report['backbone_source']=source
        atomic_json(output/'fit.json',report)
        state={'schema_version':'bullet-time.readout.v1','readout_config':asdict(config),
               'backbone_config':asdict(backbone.bt_config),'backbone_seed':source['binding']['training']['seed'],
               'backbone_source':source,'model':model.state_dict(),'fit_sha256':digest((output/'fit.json').read_bytes())}
        path=output/'readout.pt'
        with path.open('xb') as file: torch.save(state,file)
        atomic_json(str(path)+'.json',{'sha256':digest(path.read_bytes()),'model_sha256':model_identity(model)})
        return {'status':'fitted_development_only','report':str((output/'fit.json').resolve()),'checkpoint':str(path.resolve())}
    except BaseException as exc:
        atomic_json(output/'failure.json',{'status':'failed','error':str(exc),'exception_type':type(exc).__name__})
        raise


def command_predict(args):
    from bullet_time.evaluation.inputs import ImageStore,EvaluationInputs
    from bullet_time.evaluation.training import ReadoutConfig,build_readout,predict
    from bullet_time.evaluation.export import write_predictions,KEY
    path=Path(args.checkpoint);meta=strict_json(Path(str(path)+'.json').read_bytes())
    if digest(path.read_bytes())!=meta['sha256']: raise ValueError('readout byte hash mismatch')
    state=torch.load(path,map_location='cpu',weights_only=True)
    if state['schema_version']!='bullet-time.readout.v1': raise ValueError('unknown readout checkpoint')
    config=ReadoutConfig(**state['readout_config'])
    backbone=build_model(ModelConfig(**state['backbone_config']),state['backbone_seed'])
    model=build_readout(backbone,config);model.load_state_dict(state['model'],strict=True)
    if model_identity(model)!=meta['model_sha256']: raise ValueError('readout parameter hash mismatch')
    inputs=EvaluationInputs(args.inputs,ImageStore(args.images),allowed_splits=(args.split,))
    expected=strict_json(Path(args.expected).read_bytes())
    selected=[e for e in inputs.examples if e.task_id==config.task]
    by_key={(row['episode_or_video_id'],row['query_id'],str(row['horizon_or_frame'])):row for row in expected}
    if len(by_key)!=len(expected) or set(by_key)!={e.key for e in selected}:
        raise ValueError('expected-key inventory differs from actual declared input')
    for e in selected:
        row=by_key[e.key]
        if row['task_id']!=config.task or row['split']!=e.split or row['readout_seed']!=config.seed or row['prediction_role']!=e.prediction_role:
            raise ValueError('prediction inventory metadata mismatch')
    observed=[]
    for example,values in predict(model,inputs,config):
        row={key:by_key[example.key][key] for key in KEY};row.update(status='ok',error='')
        if config.task in ('collision','order'): row['contact_probability']=values[0]
        elif config.task=='tracking': row.update(x=values[0],y=values[1],visibility_probability=values[2])
        else: row['class_id']=max(range(len(values)),key=values.__getitem__)
        observed.append(row)
    return write_predictions(args.output,expected,observed,{'readout_sha256':meta['sha256'],
        'input_sha256':inputs.sha256,'image_manifest_sha256':inputs.store.manifest_sha256,
        'fit_sha256':state['fit_sha256'],'classes':config.classes,'split':args.split})


def parser():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--threads',type=int,default=1)
    commands=p.add_subparsers(dest='command',required=True)
    make=commands.add_parser('make-fixture');make.add_argument('--output',required=True);make.add_argument('--grids',type=int,default=8);make.add_argument('--image-size',type=int,default=32)
    verify=commands.add_parser('verify-corpus');verify.add_argument('--manifest',required=True);verify.add_argument('--image-size',type=int,default=224)
    train=commands.add_parser('train')
    for name in ('manifest','model-config','training-config','output'):train.add_argument('--'+name,required=True)
    train.add_argument('--scope',choices=('synthetic','integration','pilot_early','pilot_full','reference'),required=True)
    train.add_argument('--admission');train.add_argument('--resume');train.add_argument('--stop-after-updates',type=int);train.add_argument('--detailed-audit',action='store_true')
    fit=commands.add_parser('fit-readout')
    for name in ('images','inputs','labels','backbone','readout-config','output'):fit.add_argument('--'+name,required=True)
    predict=commands.add_parser('predict-readout')
    for name in ('images','inputs','checkpoint','expected','output'):predict.add_argument('--'+name,required=True)
    predict.add_argument('--split',choices=('dev','assessment'),required=True)
    slots=commands.add_parser('pilot-slots');slots.add_argument('--output',required=True)
    resource=commands.add_parser('estimate-resources');resource.add_argument('--benchmark',required=True);resource.add_argument('--output',required=True)
    split=commands.add_parser('ssv2-partitions');split.add_argument('--metadata',required=True);split.add_argument('--output',required=True)
    return p


def main(argv=None):
    args=parser().parse_args(argv)
    try:
        if args.threads<1: raise ValueError('threads must be positive')
        torch.set_num_threads(args.threads)
        if args.command=='make-fixture':
            from bullet_time.testing import make_corpus
            if args.grids<1 or args.image_size<2: raise ValueError('invalid fixture dimensions/count')
            result={'manifest':str(make_corpus(args.output,args.grids,args.image_size).resolve()),'synthetic_only':True}
        elif args.command=='verify-corpus':result=Corpus(args.manifest,image_size=args.image_size).verify()
        elif args.command=='train':result=command_train(args)
        elif args.command=='fit-readout':result=command_fit(args)
        elif args.command=='predict-readout':result=command_predict(args)
        elif args.command in ('pilot-slots','estimate-resources'):
            from bullet_time.training.plan import pilot_slots,estimate_resources
            result=pilot_slots() if args.command=='pilot-slots' else estimate_resources(strict_json(Path(args.benchmark).read_bytes()))
            if Path(args.output).exists(): raise ValueError('refuse to overwrite plan/report')
            atomic_json(args.output,result)
        else:
            from bullet_time.evaluation.external import ssv2_partitions
            result=ssv2_partitions(strict_json(Path(args.metadata).read_bytes()))
            path=Path(args.output)
            if path.exists(): raise ValueError('refuse to overwrite partition proposal')
            atomic_json(path,result)
        print(json.dumps(result,indent=2,sort_keys=True,allow_nan=False));return 0
    except (ValueError,TypeError,KeyError,OSError,RuntimeError) as exc:
        print(f'ERROR: {exc}',file=sys.stderr);return 1


if __name__=='__main__':sys.exit(main())
