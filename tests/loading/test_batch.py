from dataclasses import replace
import torch
import pytest
from bullet_time.loading.manifest import Corpus
from bullet_time.loading.schedule import CONDITIONS, construct
from bullet_time.loading.batch import sample_transform, transform_grid, collate, audit_batch, patchify
from fixtures.consumer.factory import make_corpus


def test_actual_collator_exposure_equal_across_all_arms(tmp_path):
    corpus=Corpus(make_corpus(tmp_path,count=1),image_size=32);g=corpus.grids[0]
    rgb=corpus.read_grid(g)
    transform=sample_transform(32,17,g.grid_id,0,crop_fraction=.75,color_jitter=.2)
    pixels=transform_grid(rgb,transform)
    reference=None
    for condition in CONDITIONS:
        schedule=construct(g,condition,0,17,0)
        audit={}
        for offset in range(0,16,3):
            batch=collate(g,pixels,schedule,list(range(offset,min(offset+3,16))),patch_size=8,mask_ratio=.9,seed=17)
            audit.update(audit_batch(batch))
        assert len(audit)==256
        if reference is None: reference=audit
        assert audit==reference
    # A schedule bug in the target tensor must fail instead of self-attesting from IDs.
    batch.targets=batch.targets.roll(1,1)
    with pytest.raises(ValueError,match='targets'): audit_batch(batch)


def test_patchify_semantics_not_just_shape():
    video=torch.arange(1*3*16*8*8).reshape(1,3,16,8,8).float()
    out=patchify(video,4)
    expected=video[0,:,0:2,0:4,4:8].permute(1,2,3,0).reshape(-1)
    assert torch.equal(out[0,1],expected)
    norm=patchify(video,4,normalize=True).reshape(1,-1,32,3)
    torch.testing.assert_close(norm.mean(2),torch.zeros_like(norm.mean(2)),atol=1e-6,rtol=0)
    torch.testing.assert_close(norm.var(2),torch.ones_like(norm.var(2)),atol=1e-6,rtol=0)


def test_native_targets_and_masks_are_separate_diagnostic(tmp_path):
    corpus=Corpus(make_corpus(tmp_path,count=1),image_size=32);g=corpus.grids[0]
    pixels=transform_grid(corpus.read_grid(g),sample_transform(32,17,g.grid_id,0))
    audits=[]
    for condition in ('view','time'):
        batch=collate(g,pixels,construct(g,condition,0,17,0),list(range(16)),patch_size=8,mask_ratio=.9,seed=17,recipe='native')
        audits.append(audit_batch(batch))
    assert audits[0]!=audits[1]  # Native reference does not support exact target equality.
