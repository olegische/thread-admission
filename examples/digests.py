"""Digests that bind a statement to the values it covers."""
from hashlib import sha256
import json

import rfc8785


def argument_digests(raw_arguments):
    parsed = json.loads(raw_arguments)
    return {
        "raw_sha256": sha256(raw_arguments.encode("utf-8")).hexdigest(),
        "jcs_sha256": sha256(rfc8785.dumps(parsed)).hexdigest(),
    }


def commitment(value):
    """Digest and length of a JSON value in its canonical (JCS) encoding."""
    encoded = rfc8785.dumps(value)
    return {"sha256": sha256(encoded).hexdigest(), "length": len(encoded)}
