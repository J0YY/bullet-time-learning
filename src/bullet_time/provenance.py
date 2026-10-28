"""Stable identities and strict file boundaries shared by consumer components."""

import hashlib
import json
import math
from pathlib import Path
import os
import tempfile


def canonical_bytes(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def identity(value) -> str:
    return digest(canonical_bytes(value))


def seed_for(seed: int, stream: str, *keys) -> int:
    if type(seed) is not int or seed < 0:
        raise ValueError("seed must be a nonnegative integer")
    return int(identity([seed, stream, *keys])[:16], 16) % (2**63 - 1)


def strict_json(data):
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError(f"duplicate JSON key: {key}")
            result[key] = value
        return result

    def constant(value):
        raise ValueError(f"nonfinite JSON constant: {value}")

    return json.loads(data, object_pairs_hook=pairs, parse_constant=constant)


def fields(record, required, optional=()):
    if (
        not isinstance(record, dict)
        or not set(required) <= record.keys()
        or record.keys() - set(required) - set(optional)
    ):
        raise ValueError(f"unexpected or missing fields; required {sorted(required)}")


def integer(value, name, minimum=0):
    if type(value) is not int or value < minimum:
        raise ValueError(f"{name} must be an integer >= {minimum}")
    return value


def number(value, name, low=None, high=None):
    if type(value) not in (int, float) or not math.isfinite(value):
        raise ValueError(f"{name} must be finite")
    if low is not None and value < low or high is not None and value > high:
        raise ValueError(f"{name} outside allowed range")
    return value


def text_id(value, name):
    if not isinstance(value, str) or not value or any(ord(c) < 32 for c in value):
        raise ValueError(f"invalid {name}")
    return value


def sha256(value):
    if (
        not isinstance(value, str)
        or len(value) != 64
        or any(c not in "0123456789abcdef" for c in value)
    ):
        raise ValueError("expected lowercase SHA-256")
    return value


def inside(root, relative):
    root = Path(root).resolve()
    if not isinstance(relative, str) or not relative or "\\" in relative:
        raise ValueError("invalid relative path")
    path = Path(relative)
    if path.is_absolute() or ".." in path.parts:
        raise ValueError("path escapes bundle")
    result = (root / path).resolve(strict=True)
    if not result.is_relative_to(root) or not result.is_file():
        raise ValueError("path escapes bundle or is not a file")
    return result


def atomic_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    data = json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n"
    fd, tmp = tempfile.mkstemp(prefix="." + path.name, dir=path.parent)
    try:
        with os.fdopen(fd, "w") as file:
            file.write(data)
            file.flush()
            os.fsync(file.fileno())
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)
