"""Compare optimized admission to direct pixel arithmetic, including empty masks."""

import numpy as np
from PIL import Image
import pytest

from bullet_time.generation.evaluation_bundle import check_duplicates


def brute_force(rows, iou, mae):
    for sa, pa, ma in rows:
        for sb, pb, mb in rows:
            if sa != "train" or sb != "dev":
                continue
            if np.array_equal(pa, pb):
                return True
            union = ma | mb
            if not union.any():
                difference = np.abs(pa.astype(float) - pb).mean() / 255
            elif not ma.any() or not mb.any():
                continue
            else:
                if (ma & mb).sum() / union.sum() < iou:
                    continue
                difference = np.abs(pa[union].astype(float) - pb[union]).mean() / 255
            if difference <= mae:
                return True
    return False


def compare(tmp_path, rows, iou=0.98, mae=1 / 255):
    requests = []
    for index, (split, pixels, fg) in enumerate(rows):
        gid = f"fixture-{index}"
        mask = np.zeros_like(pixels)
        mask[fg, 0] = 255
        for path, array in [
            (tmp_path / "inputs/rgb" / gid / "f.png", pixels),
            (tmp_path / "private" / gid / "masks/f.png", mask),
        ]:
            path.parent.mkdir(parents=True)
            Image.fromarray(array).save(path)
        requests.append(dict(group_id=gid, split=split, frames={"f": {}}))
    plan = dict(near_duplicate_foreground_iou=iou, near_duplicate_rgb_mae=mae)
    if brute_force(rows, iou, mae):
        with pytest.raises(ValueError, match="duplicate RGB"):
            check_duplicates(tmp_path, requests, plan)
        return None
    report = check_duplicates(tmp_path, requests, plan)
    assert report["images"] == len(rows)
    assert report["cross_split_image_pairs"] == sum(r[0] == "train" for r in rows) * sum(
        r[0] == "dev" for r in rows
    )
    return report


@pytest.mark.parametrize("difference,removed", [(3, 2), (4, 2), (3, 3)])
def test_inclusive_iou_and_mae_boundaries(tmp_path, difference, removed):
    a = np.zeros((224, 224, 3), dtype=np.uint8)
    b = a.copy()
    fg = np.zeros((224, 224), dtype=bool)
    fg[10:20, 10:20] = True
    smaller = fg.copy()
    smaller[10, 10 : 10 + removed] = False
    b[fg, 0] = difference
    compare(tmp_path, [("train", a, fg), ("dev", b, smaller)])


@pytest.mark.parametrize(
    "case", ["empty-near", "empty-far", "empty-equal-means", "one-empty", "same-rgb-different-mask"]
)
def test_empty_masks_and_exact_rgb_override(tmp_path, case):
    a = np.full((224, 224, 3), 100, dtype=np.uint8)
    b = a.copy()
    b[:, :, 0] += 3 if case == "empty-near" else 30
    ma = np.zeros((224, 224), dtype=bool)
    mb = ma.copy()
    if case == "empty-equal-means":
        b[:112] = 80
        b[112:] = 120
    if case in ("one-empty", "same-rgb-different-mask"):
        mb[2:12, 2:12] = True
    if case == "same-rgb-different-mask":
        b = a.copy()
    compare(tmp_path, [("train", a, ma), ("dev", b, mb)])


def test_randomized_oracle_and_duplicate_comparison_reuse(tmp_path):
    rng = np.random.default_rng(71)
    rows = []
    for index in range(24):
        pixels = rng.integers(0, 256, (224, 224, 3), dtype=np.uint8)
        fg = np.zeros((224, 224), dtype=bool)
        x, y = rng.integers(10, 120, 2)
        if index % 5:
            fg[y : y + 30, x : x + 30] = True
        rows.append(("train" if index < 12 else "dev", pixels, fg))
    rows += [rows[0], rows[0], rows[-1]]
    report = compare(tmp_path, rows)
    assert report["unique_raster_mask_pairs"] == 24
    assert report["unique_cross_split_comparisons"] == 144
    assert report["retained_mask_bytes"] == 24 * 224 * 224 // 8
    assert report["rgb_cache_capacity"] == 64
