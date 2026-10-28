import json
from collections import Counter
import pytest
from bullet_time.loading.manifest import Corpus, Grid
from bullet_time.loading.schedule import CONDITIONS, FRACTIONS, construct, family_ranks, grid_order, updates
from fixtures.consumer.factory import make_corpus


def test_bytes_and_schema_rejections(tmp_path):
    path = make_corpus(tmp_path, count=1)
    corpus = Corpus(path, image_size=32)
    assert corpus.verify()['images'] == 256
    rows = [json.loads(s) for s in path.read_text().splitlines()]
    original = path.read_text()
    for mutate in (lambda r: r.update(velocity=10), lambda r: r['cells'].pop(),
                   lambda r: r['cells'][0].update(world_time_index=True),
                   lambda r: r['cells'][0].update(rgb_path='../secret.png'),
                   lambda r: r['cells'][0].update(image_id=r['cells'][1]['image_id'])):
        r = json.loads(original)
        mutate(r)
        path.write_text(json.dumps(r)+'\n')
        with pytest.raises(ValueError): Corpus(path, image_size=32)
    path.write_text(original)
    bad = tmp_path / rows[0]['cells'][0]['rgb_path']
    bad.write_bytes(b'corrupted after construction')
    with pytest.raises(ValueError, match='hash mismatch'): corpus.verify()


def test_symlink_escape(tmp_path):
    path = make_corpus(tmp_path/'corpus', count=1)
    rows = json.loads(path.read_text())
    external = tmp_path/'external.png'; external.write_bytes(b'x')
    image = path.parent/rows['cells'][0]['rgb_path']; image.unlink(); image.symlink_to(external)
    with pytest.raises(ValueError, match='escapes'): Corpus(path,image_size=32)


def test_all_schedules_balance_at_every_family_prefix():
    grids = [Grid(f'g{i:03}', f'family{i%3}', ()) for i in range(100)]
    expected = Counter((t,c) for t in range(16) for c in range(16))
    for seed in (0,17,29):
        for cycle in range(2):
            histories = {g.grid_id: Counter() for g in grids}
            for p in range(cycle*4,cycle*4+4):
                ranks=family_ranks(grids,seed,p)
                order=grid_order(grids,seed,p)
                for condition in CONDITIONS:
                    for g in grids:
                        s=construct(g,condition,p,seed,ranks[g.grid_id])
                        assert Counter(cell for clip in s.clips for cell in clip)==expected
                        if condition=='joint':
                            assert all([cell[0] for cell in clip]==list(range(16)) for clip in s.clips)
                        if condition in FRACTIONS:
                            histories[g.grid_id][condition] += s.orientation=='time'
                    if condition in FRACTIONS:
                        for family in {g.scene_family for g in grids}:
                            family_grids=[g for g in order if g.scene_family==family]
                            for start in range(0,len(family_grids)-3,4):
                                block=family_grids[start:start+4]
                                assert sum(construct(g,condition,p,seed,ranks[g.grid_id]).orientation=='time' for g in block)==FRACTIONS[condition]
                directions=Counter(construct(g,'joint',p,seed,ranks[g.grid_id]).direction for g in grids)
                assert abs(directions[1]-directions[-1]) <= 3
            for history in histories.values(): assert dict(history)==FRACTIONS
    units=updates(grids,17,0)
    assert list(map(len,units))==[8]*12+[4]
    assert [g.grid_id for u in units for g in u]==[g.grid_id for g in grid_order(grids,17,0)]
