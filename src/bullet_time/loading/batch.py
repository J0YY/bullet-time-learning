"""One transformation per grid; actual post-collator exposure auditing."""
from dataclasses import dataclass
import random
import numpy as np
import torch
from torch.nn import functional as F
from bullet_time.provenance import digest, integer, number, seed_for

MEAN = (0.485, 0.456, 0.406)
STD = (0.229, 0.224, 0.225)


@dataclass(frozen=True)
class Transform:
    top: int
    left: int
    size: int
    brightness: float


def sample_transform(size, seed, grid_id, pass_index, crop_fraction=1.0, color_jitter=0.0):
    number(crop_fraction, 'crop_fraction', 0.25, 1.0)
    number(color_jitter, 'color_jitter', 0, 0.5)
    rng = random.Random(seed_for(seed, 'augmentation', grid_id, pass_index))
    crop = max(1, round(size * crop_fraction))
    return Transform(rng.randrange(size-crop+1), rng.randrange(size-crop+1), crop,
                     rng.uniform(1-color_jitter, 1+color_jitter))


def transform_grid(rgb, transform):
    if rgb.dtype != np.uint8 or rgb.ndim != 5 or rgb.shape[:2] != (16,16) or rgb.shape[-1] != 3:
        raise ValueError('expected uint8 time,camera,height,width,RGB grid')
    size = rgb.shape[2]
    if rgb.shape[3] != size or transform.top < 0 or transform.left < 0 or transform.size <= 0 or (
        transform.top+transform.size > size or transform.left+transform.size > size):
        raise ValueError('crop outside grid')
    pixels = torch.from_numpy(rgb.copy()).reshape(256,size,size,3).permute(0,3,1,2).float()/255
    pixels = pixels[:,:,transform.top:transform.top+transform.size,transform.left:transform.left+transform.size]
    if transform.size != size:
        pixels = F.interpolate(pixels,size=(size,size),mode='bilinear',align_corners=False,antialias=True)
    return (pixels*transform.brightness).clamp(0,1).reshape(16,16,3,size,size).contiguous()


def spatial_mask(size, patch_size, mask_ratio, seed, grid_id, pass_index, clip_index=None):
    integer(patch_size,'patch_size',1)
    number(mask_ratio,'mask_ratio',0,1)
    if size % patch_size:
        raise ValueError('patch size must divide image')
    count = (size//patch_size)**2
    masked = int(mask_ratio*count)
    if not 0 < masked < count:
        raise ValueError('need both visible and masked patches')
    indices = list(range(count))
    # Native reference keys by clip; controlled arm omits condition and clip entirely.
    random.Random(seed_for(seed,'mask',grid_id,pass_index,clip_index)).shuffle(indices)
    result=torch.zeros(count,dtype=torch.bool);result[indices[:masked]]=True
    return result


def patchify(raw, patch_size, tubelet=2, normalize=False):
    """B,C,T,H,W -> B,(tube,row,column),(frame,row_pixel,column_pixel,channel)."""
    b,c,t,h,w = raw.shape
    if c!=3 or t%tubelet or h%patch_size or w%patch_size:
        raise ValueError('incompatible patch geometry')
    p=patch_size;u=tubelet
    patches=raw.reshape(b,c,t//u,u,h//p,p,w//p,p).permute(0,2,4,6,3,5,7,1).contiguous()
    patches=patches.reshape(b,-1,u*p*p,3)
    if normalize:
        patches=(patches-patches.mean(-2,keepdim=True))/(patches.var(-2,unbiased=True,keepdim=True).sqrt()+1e-6)
    return patches.flatten(2)


@dataclass
class Batch:
    inputs: torch.Tensor
    mask: torch.Tensor
    targets: torch.Tensor
    image_ids: tuple[tuple[str,...],...]
    raw: torch.Tensor
    patch_size: int
    tubelet: int
    normalized_targets: bool

    @property
    def labels(self):
        b,_,d=self.targets.shape
        return self.targets[self.mask].reshape(b,-1,d)


def collate(grid, transformed, schedule, clip_indices, *, patch_size, mask_ratio, seed,
            recipe='controlled', tubelet=2):
    if recipe not in ('controlled','native'):
        raise ValueError('unknown recipe')
    if not clip_indices or any(type(i) is not int or not 0<=i<16 for i in clip_indices):
        raise ValueError('invalid clip indices')
    clips=[];ids=[];masks=[]
    for i in clip_indices:
        cells=schedule.clips[i]
        clips.append(torch.stack([transformed[t,c] for t,c in cells],1))
        ids.append(tuple(grid.cell(t,c).image_id for t,c in cells))
        mask=spatial_mask(transformed.shape[-1],patch_size,mask_ratio,seed,grid.grid_id,
                          schedule.pass_index,i if recipe=='native' else None)
        masks.append(mask.repeat(16//tubelet))
    raw=torch.stack(clips)
    mean=raw.new_tensor(MEAN)[None,:,None,None,None]
    std=raw.new_tensor(STD)[None,:,None,None,None]
    return Batch((raw-mean)/std,torch.stack(masks),patchify(raw,patch_size,tubelet,recipe=='native'),
                 tuple(ids),raw,patch_size,tubelet,recipe=='native')


def tensor_hash(tensor):
    return digest(tensor.detach().cpu().contiguous().numpy().tobytes())


def audit_batch(batch):
    """Map *actual* collator tensors to source-image coordinates, not local token IDs."""
    b,c,t,h,w=batch.raw.shape;p=batch.patch_size;u=batch.tubelet;s=(h//p)*(w//p)
    if batch.mask.dtype!=torch.bool or batch.mask.shape!=(b,t//u*s):
        raise ValueError('bad post-collator mask shape/type')
    # Back-project the input normalization to check that targets represent its actual pixels.
    reconstructed=batch.inputs*batch.inputs.new_tensor(STD)[None,:,None,None,None]+batch.inputs.new_tensor(MEAN)[None,:,None,None,None]
    if not torch.allclose(reconstructed,batch.raw,atol=1e-7,rtol=0):
        raise ValueError('input and target pixels differ')
    expected=patchify(batch.raw,p,u,batch.normalized_targets)
    if not torch.equal(expected,batch.targets):
        raise ValueError('post-collator targets do not match actual pixels')
    targets=batch.targets.reshape(b,t//u,s,u,p,p,3)
    records={}
    for clip in range(b):
        for frame,image_id in enumerate(batch.image_ids[clip]):
            if image_id in records:
                raise ValueError('duplicate source image in batch')
            mask=batch.mask[clip].reshape(t//u,s)[frame//u]
            records[image_id]={
                'transformed_rgb_sha256':tensor_hash(batch.raw[clip,:,frame]),
                'visible_patches':torch.where(~mask)[0].tolist(),
                'target_patches':torch.where(mask)[0].tolist(),
                'target_components_sha256':tensor_hash(targets[clip,frame//u,:,frame%u][mask]),
            }
    return records
