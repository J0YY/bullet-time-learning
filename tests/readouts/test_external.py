import numpy as np
import pytest
from bullet_time.evaluation.external import ssv2_partitions,validate_external_groups,assemble_action_clip


def test_ssv2_partition_fixed_disjoint_nested_and_order_independent():
    rows=[{'video_id':str(i+1),'class_id':i//20,'official_split':'train'} for i in range(60)]
    result=ssv2_partitions(rows)
    assert result==ssv2_partitions(list(reversed(rows)))
    assert len(result['dev'])==6 and len(result['train'])==54 and len(result['train_10pct'])==3
    assert not set(result['dev'])&set(result['train'])
    assert set(result['train_10pct'])<=set(result['train'])
    groups={row['video_id']:row['video_id'] for row in rows}
    assert validate_external_groups(result,groups)['passed']
    groups[result['dev'][0]]=groups[result['train'][0]]
    with pytest.raises(ValueError,match='cross train/dev'):validate_external_groups(result,groups)
    rows[0]['official_split']='validation'
    with pytest.raises(ValueError,match='official training'):ssv2_partitions(rows)


def test_action_adapter_short_video_repeats_only_selected_frames():
    clip,indices=assemble_action_clip([np.full((10,20,3),i*50,dtype=np.uint8) for i in range(3)],size=32)
    assert clip.shape==(3,16,32,32)
    assert indices[0]==0 and indices[-1]==2 and len(set(indices))==3
