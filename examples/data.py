"""Load the checked-in example fixtures; reject ambiguous JSON objects."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def unique_keys(pairs):
    value = {}
    for key, item in pairs:
        if key in value:
            raise ValueError(f"Duplicate JSON key: {key}")
        value[key] = item
    return value


def read_json(value):
    return json.loads(value, object_pairs_hook=unique_keys)


def load_json(relative_path):
    return read_json((ROOT / relative_path).read_text(encoding="utf-8"))
