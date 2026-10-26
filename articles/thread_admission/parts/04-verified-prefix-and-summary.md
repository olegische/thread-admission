## Restore the verified prefix and summarize the tail

Suppose the service exported 100 records and the user returns one array containing 120. The service can verify the first 100 without requiring a separate copy of the original snapshot.

At export, save a checkpoint containing the record offset and the hash of `records[:offset]`. The offset is measured in records, not bytes: `offset = 100` leaves the tail at `records[100:]`.

For this approach, the catalog entry keeps the owner, thread, and revision identifiers from the previous section and replaces the whole-file `sha256` with a `checkpoint` object containing `offset` and `prefix_sha256`. The full entry is:

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "type": "object",
  "required": ["owner_id", "thread_id", "revision", "checkpoint"],
  "properties": {
    "owner_id": { "type": "string" },
    "thread_id": { "type": "string" },
    "revision": { "type": "string" },
    "checkpoint": {
      "type": "object",
      "required": ["offset", "prefix_sha256"],
      "properties": {
        "offset": { "type": "integer", "minimum": 0 },
        "prefix_sha256": { "type": "string", "pattern": "^[0-9a-f]{64}$" }
      }
    }
  }
}
```

At export, store this entry under `(owner_id, thread_id, revision)`. On return, authenticate the owner, authorize access to the thread, and load the entry for the revision being checked. The saved `checkpoint.offset` determines where to split the returned array; `checkpoint.prefix_sha256` is the expected hash. The client can return one array containing both the original records and the additions.

The checkpoint hashes the record array, rather than the complete exported file. This example uses JCS at both export and return so that JSON whitespace and object-key order do not affect the comparison. Record values and array order remain significant. The Python package `rfc8785` supplies the canonical bytes. [RFC 8785](https://www.rfc-editor.org/rfc/rfc8785.html), [Python implementation](https://github.com/trailofbits/rfc8785.py)

```python
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
```

The catalog entry wraps the checkpoint with its identifiers:

```python
# At export, records is the saved revision's array.
entry = {
    "owner_id": owner_id,
    "thread_id": thread_id,
    "revision": revision,
    "checkpoint": make_checkpoint(records),
}
catalog[(owner_id, thread_id, revision)] = entry

# On return, after authorization and selection of the saved revision.
entry = catalog[(owner_id, thread_id, revision)]
prefix, tail = split_verified_prefix(returned_records, entry["checkpoint"])
```

The code assumes parsed, validated runtime records. Rewritten IDs or compaction within the prefix invalidate the match. If it fails, ask for the original snapshot or offer continuation from a summary of the whole submission.

### Keep the first 100 records; summarize the next 20

Once the prefix matches, restore those 100 records unchanged and summarize the next 20 as a new user-context message. Save checkpoints after pending tool calls have completed, so the boundary does not separate calls from their results.

This raises a source-of-truth question. The service can save the prefix and summary as a new revision, but that revision no longer contains the detailed local continuation. If it replaces the user's local history, those records are lost. Keeping the originals separately preserves them, but the summary is only a derived context, not their verified replacement.

In a user-held history model, the detailed record remains with the user, while the service still needs to check what it receives. We therefore turn to an approach that compares returned records with evidence captured during model calls, allowing covered content to be retained without replacing it with a summary.
