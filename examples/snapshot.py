"""Executable example from article/parts/03-snapshot-and-catalog.md."""

from hashlib import sha256


def matches_saved_snapshot(catalog, owner_id, thread_id, revision, upload):
    entry = catalog.get((owner_id, thread_id, revision))
    if entry is None:
        return False
    return sha256(upload).hexdigest() == entry["sha256"]
