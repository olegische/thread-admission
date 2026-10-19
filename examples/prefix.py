"""Executable example from article/parts/04-verified-prefix-and-summary.md."""

from hashlib import sha256


import rfc8785


def prefix_hash(records):
    return sha256(rfc8785.dumps(records)).hexdigest()


def make_checkpoint(records):
    return {
        "offset": len(records),
        "prefix_sha256": prefix_hash(records),
    }


def split_verified_prefix(records, checkpoint):
    # checkpoint was loaded from the authorized service catalog.
    offset = checkpoint["offset"]
    if len(records) < offset:
        raise ValueError("History is shorter than the saved prefix")

    prefix, tail = records[:offset], records[offset:]
    if prefix_hash(prefix) != checkpoint["prefix_sha256"]:
        raise ValueError("Saved prefix was changed")

    return prefix, tail  # Verification has not admitted the tail.
