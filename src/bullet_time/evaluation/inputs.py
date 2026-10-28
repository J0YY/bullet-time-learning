"""Task input boundary: labels and audit metadata never become model features."""
from dataclasses import dataclass
from pathlib import Path
from io import BytesIO
import numpy as np
from PIL import Image
import torch
from bullet_time.provenance import fields, strict_json, inside, digest, sha256, integer, text_id, number
from bullet_time.loading.batch import MEAN, STD

INPUT_VERSION='bullet-time.evaluation.v2'
SPLITS=('train','dev','assessment')
TASKS=('collision','order','tracking','ssv2')


def point(value):
    if not isinstance(value,list) or len(value)!=2: raise ValueError('expected XY pair')
    return tuple(number(v,'coordinate',0,1) for v in value)


class ImageStore:
    def __init__(self, path):
        self.path=Path(path).resolve(strict=True);self.root=self.path.parent
        self.manifest_sha256=digest(self.path.read_bytes());self.images={}
        names={'image_id','rgb_path','file_sha256','rgb_sha256','height','width','channels'}
        for line in self.path.read_bytes().splitlines():
            r=strict_json(line);fields(r,names)
            identifier=text_id(r['image_id'],'image_id')
            if identifier in self.images: raise ValueError('duplicate image ID')
            for key in ('height','width','channels'): integer(r[key],key,1)
            if r['channels']!=3: raise ValueError('only RGB inputs are allowed')
            sha256(r['file_sha256']);sha256(r['rgb_sha256']);inside(self.root,r['rgb_path'])
            self.images[identifier]=r
        if not self.images: raise ValueError('empty image store')

    def read(self, image_id):
        if image_id not in self.images: raise ValueError('unregistered image ID')
        r=self.images[image_id];raw=inside(self.root,r['rgb_path']).read_bytes()
        if digest(raw)!=r['file_sha256']: raise ValueError('image byte hash mismatch')
        with Image.open(BytesIO(raw)) as image:
            if image.format!='PNG' or image.mode!='RGB' or image.size!=(r['width'],r['height']):
                raise ValueError('image encoding/dimensions mismatch')
            rgb=np.array(image)
        if digest(rgb.tobytes())!=r['rgb_sha256']: raise ValueError('decoded RGB hash mismatch')
        return rgb


def letterbox(rgb, size=224):
    """RGB + exact coordinate map for deterministic resize/center-pad."""
    h,w=rgb.shape[:2]
    if h<2 or w<2 or size<2: raise ValueError('coordinate geometry requires dimensions >=2')
    ratio=min(size/w,size/h)
    nw=max(2,min(size,round(w*ratio)));nh=max(2,min(size,round(h*ratio)))
    left=(size-nw)//2;top=(size-nh)//2
    pixels=np.zeros((size,size,3),dtype=np.uint8)
    pixels[top:top+nh,left:left+nw]=np.asarray(Image.fromarray(rgb).resize((nw,nh),Image.Resampling.BILINEAR))
    # Coordinates use pixel centers and endpoints, not an approximate scale ratio.
    def map_point(xy):
        return ((left+xy[0]*(nw-1))/(size-1),(top+xy[1]*(nh-1))/(size-1))
    return torch.from_numpy(pixels.copy()).permute(2,0,1).float()/255,map_point


def normalize(pixels):
    # Input shape C,T,H,W (or B,C,T,H,W); normalize channel dimension explicitly.
    if pixels.ndim==4:
        shape=(3,1,1,1)
    elif pixels.ndim==5:
        shape=(1,3,1,1,1)
    else: raise ValueError('expected video tensor')
    return (pixels-pixels.new_tensor(MEAN).reshape(shape))/pixels.new_tensor(STD).reshape(shape)


def uniform_frame_indices(frame_count):
    integer(frame_count,'frame_count',1)
    # Exact rational nearest integer; ties down. Avoid platform/bankers-rounding ambiguity.
    return tuple((2*i*(frame_count-1)+14)//30 for i in range(16))


@dataclass(frozen=True)
class Example:
    episode_id: str
    query_id: str
    task_id: str
    split: str
    observed_image_ids: tuple
    observed_frame_indices: tuple
    query_points: tuple
    horizon_seconds: float | None = None
    prediction_frame: int | None = None
    reference_image_id: str | None = None
    reference_frame: int | None = None
    reference_point: tuple | None = None
    prediction_role: str = 'primary'

    @property
    def key(self):
        suffix=self.prediction_frame if self.task_id=='tracking' else self.horizon_seconds if self.task_id in ('collision','order') else 'clip'
        return (self.episode_id,self.query_id,str(suffix))


class EvaluationInputs:
    def __init__(self, path, store, *, allowed_splits=('train','dev')):
        if not set(allowed_splits)<=set(SPLITS): raise ValueError('final/official-validation access is not a pilot operation')
        self.path=Path(path).resolve(strict=True);self.sha256=digest(self.path.read_bytes());self.store=store
        self.examples=[];keys=set();tracking={}
        common={'schema_version','episode_id','query_id','task_id','split','observed_image_ids','observed_frame_indices','query_points'}
        for line in self.path.read_bytes().splitlines():
            r=strict_json(line);task=r.get('task_id')
            extra={'horizon_seconds'} if task in ('collision','order') else (
                {'prediction_frame','reference_image_id','reference_frame','reference_point'} if task=='tracking' else set())
            fields(r,common|extra, {'prediction_role'} if task=='tracking' else ())
            if r['schema_version']!=INPUT_VERSION or task not in TASKS or r['split'] not in allowed_splits:
                raise ValueError('unsupported version/task or inaccessible split')
            for name in ('episode_id','query_id'): text_id(r[name],name)
            ids=r['observed_image_ids'];indices=r['observed_frame_indices']
            if not isinstance(ids,list) or len(ids)!=16 or not isinstance(indices,list) or len(indices)!=16:
                raise ValueError('exactly sixteen observations are required')
            if any(identifier not in store.images for identifier in ids): raise ValueError('unregistered observation')
            for index in indices: integer(index,'frame_index')
            if task!='ssv2' and indices!=list(range(indices[-1]-15,indices[-1]+1)):
                raise ValueError('game observations must be consecutive at fixed 16 Hz')
            if task=='ssv2' and indices!=sorted(indices): raise ValueError('action clip must preserve order')
            queries=tuple(point(p) for p in r['query_points'])
            if len(queries)!=(2 if task in ('collision','order') else 0):
                raise ValueError('invalid task query access')
            if task in ('collision','order'):
                if type(r['horizon_seconds']) not in (float,int) or r['horizon_seconds'] not in (.25,.5,1.):
                    raise ValueError('unsupported fixed horizon')
                r['horizon_seconds']=float(r['horizon_seconds'])
            if task=='tracking':
                integer(r['prediction_frame'],'prediction_frame');integer(r['reference_frame'],'reference_frame')
                if r.get('prediction_role','primary') not in ('primary','auxiliary'):
                    raise ValueError('unknown tracking prediction role')
                if r['prediction_frame']!=indices[-1] or not indices[0]<=r['reference_frame']<r['prediction_frame']:
                    raise ValueError('tracking window/reference is not causal')
                if r['reference_image_id']!=ids[indices.index(r['reference_frame'])]:
                    raise ValueError('reference must be the declared past observed image')
                r['reference_point']=point(r['reference_point'])
            del r['schema_version'];r['observed_image_ids']=tuple(ids);r['observed_frame_indices']=tuple(indices);r['query_points']=queries
            example=Example(**r)
            if example.key in keys: raise ValueError('duplicate evaluation key')
            keys.add(example.key);self.examples.append(example)
            if task=='tracking': tracking.setdefault((example.episode_id,example.query_id),[]).append(example)
        if not self.examples: raise ValueError('empty evaluation input')
        # A full scoring set has exactly three predictions per designated tracking event.
        for examples in tracking.values():
            if sum(e.prediction_role=='primary' for e in examples)!=3 or len({(e.reference_frame,e.reference_image_id,e.reference_point) for e in examples})!=1:
                raise ValueError('tracking requires three frames and one fixed reference')
            if len({e.prediction_frame for e in examples})!=len(examples):
                raise ValueError('tracking repeats a scored frame')

    def assemble(self, example, *, size=224, mode='sequence'):
        if mode not in ('sequence','final_frame','bag','current_frame'): raise ValueError('unknown input mode')
        if mode=='current_frame' and example.task_id!='tracking': raise ValueError('tracking-only control')
        if mode in ('final_frame','bag') and example.task_id not in ('collision','order'):
            raise ValueError('forecast-only control')
        ids=example.observed_image_ids
        if mode in ('final_frame','current_frame'): ids=(ids[-1],)*16
        frames=[];mappers=[]
        for image_id in ids:
            frame,mapper=letterbox(self.store.read(image_id),size);frames.append(frame);mappers.append(mapper)
        video=normalize(torch.stack(frames,1))
        query=torch.tensor([mappers[-1](p) for p in example.query_points],dtype=torch.float32).reshape(-1,2)
        reference=None;reference_point=None
        if example.task_id=='tracking':
            frame,mapper=letterbox(self.store.read(example.reference_image_id),size)
            reference=normalize(frame[:,None].repeat(1,16,1,1))
            reference_point=torch.tensor(mapper(example.reference_point),dtype=torch.float32)
        # No IDs, time indices, labels, family or pair identifiers enter this feature dictionary.
        return {'video':video,'query_points':query,'reference':reference,'reference_point':reference_point}
