## Restore the verified prefix and summarize the tail

Suppose the service exported 100 records and the user returns one array containing 120. The service can verify the first 100 without requiring a separate copy of the original snapshot.

At export, save a checkpoint containing the record offset and the hash of `records[:offset]`. The offset is measured in records, not bytes: `offset = 100` leaves the tail at `records[100:]`.

Store the checkpoint in the service catalog under the authenticated owner, thread, and exported revision. Both the offset and hash come from that saved entry, not from replacement values supplied by the uploader.

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "type": "object",
  "required": ["offset", "prefix_sha256"],
  "properties": {
    "offset": { "type": "integer", "minimum": 0 },
    "prefix_sha256": { "type": "string", "pattern": "^[0-9a-f]{64}$" }
  }
}
```

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

The code assumes parsed, validated runtime records. Rewritten IDs or compaction within the prefix invalidate the match. If it fails, ask for the original snapshot or offer continuation from a summary of the whole submission.

### Keep the first 100 records; summarize the next 20

Once the prefix matches, restore those 100 records unchanged. Compact only the 20 records from the offset onward and append their summary as a new user-context message. The summary describes the local continuation; it does not recreate its assistant turns or tool results as recorded history.

Save the checkpoint after pending tool calls have completed, so that summarizing the tail does not separate calls from their results.

Compaction reduces detail, not the need for normal input controls. The resulting summary remains supplied context. After accepting it, the service can save the restored prefix and the new summary message as a new revision. A later hash match will recognize that revision, including the summary as a user-context message.

This can be the complete design: the saved prefix is restored, and the local continuation enters as a summary. The next approach changes how verification data is collected: instead of recognizing only an exported revision, the service records what it observes during model calls and uses those records to verify the whole history.
