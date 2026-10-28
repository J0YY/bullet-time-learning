"""Strict allowlisted RGB consumer. Does not import the producer's schema."""
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
import numpy as np
from PIL import Image

from bullet_time.provenance import digest, fields, inside, integer, sha256, strict_json, text_id


@dataclass(frozen=True)
class Cell:
    world_time_index: int
    camera_index: int
    image_id: str
    rgb_path: str
    file_sha256: str
    rgb_sha256: str
    height: int
    width: int
    channels: int


@dataclass(frozen=True)
class Grid:
    grid_id: str
    scene_family: str
    cells: tuple[Cell, ...]  # canonical world-time-major order

    def cell(self, time, camera):
        return self.cells[time * 16 + camera]


class Corpus:
    """Admission metadata is separate; this class can access only RGB manifest data."""
    def __init__(self, manifest, *, image_size=224):
        self.manifest = Path(manifest).resolve(strict=True)
        self.root = self.manifest.parent
        raw = self.manifest.read_bytes()
        self.manifest_sha256 = digest(raw)
        self.image_size = integer(image_size, 'image_size', 1)
        grids, image_ids, grid_ids = [], set(), set()
        for line in raw.splitlines():
            if not line.strip():
                raise ValueError('empty manifest record')
            row = strict_json(line)
            fields(row, {'schema_version', 'grid_id', 'scene_family', 'cells'})
            if row['schema_version'] != 'bullet-time.grid.v1':
                raise ValueError('unsupported grid version')
            gid = text_id(row['grid_id'], 'grid_id')
            family = text_id(row['scene_family'], 'scene_family')
            if gid in grid_ids:
                raise ValueError('duplicate grid ID')
            grid_ids.add(gid)
            cells, positions = [], set()
            if not isinstance(row['cells'], list) or len(row['cells']) != 256:
                raise ValueError('grid must have 256 cells')
            for record in row['cells']:
                fields(record, Cell.__dataclass_fields__)
                t = integer(record['world_time_index'], 'world_time_index')
                c = integer(record['camera_index'], 'camera_index')
                if t >= 16 or c >= 16 or (t, c) in positions:
                    raise ValueError('duplicate or invalid cell index')
                positions.add((t, c))
                image_id = text_id(record['image_id'], 'image_id')
                if image_id in image_ids:
                    raise ValueError('duplicate image ID')
                image_ids.add(image_id)
                for name in ('file_sha256', 'rgb_sha256'):
                    sha256(record[name])
                if any(type(record[k]) is not int for k in ('height', 'width', 'channels')) or (
                    record['height'], record['width'], record['channels']) != (image_size, image_size, 3):
                    raise ValueError('unexpected image dimensions')
                inside(self.root, record['rgb_path'])
                cells.append(Cell(**record))
            grids.append(Grid(gid, family, tuple(sorted(cells, key=lambda cell: (cell.world_time_index, cell.camera_index)))))
        if not grids:
            raise ValueError('empty corpus')
        self.grids = tuple(sorted(grids, key=lambda grid: grid.grid_id))
        self.by_id = {grid.grid_id: grid for grid in self.grids}

    def read_cell(self, cell):
        # Revalidate actual bytes at use, so edited files cannot hide behind cached metadata.
        raw = inside(self.root, cell.rgb_path).read_bytes()
        if digest(raw) != cell.file_sha256:
            raise ValueError(f'file hash mismatch: {cell.image_id}')
        with Image.open(BytesIO(raw)) as image:
            if image.format != 'PNG' or image.mode != 'RGB' or image.size != (cell.width, cell.height):
                raise ValueError('expected lossless RGB PNG with declared size')
            decoded = np.array(image, dtype=np.uint8)
        if digest(decoded.tobytes(order='C')) != cell.rgb_sha256:
            raise ValueError(f'decoded hash mismatch: {cell.image_id}')
        return decoded

    def read_grid(self, grid):
        return np.stack([self.read_cell(cell) for cell in grid.cells]).reshape(16, 16, self.image_size, self.image_size, 3)

    def verify(self):
        for grid in self.grids:
            for cell in grid.cells:
                self.read_cell(cell)
        return {'manifest_sha256': self.manifest_sha256, 'grids': len(self.grids),
                'images': 256 * len(self.grids), 'evidence': 'RGB bytes only; renderer/split validation separate'}
