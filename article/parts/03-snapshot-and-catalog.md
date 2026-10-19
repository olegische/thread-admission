## An unchanged snapshot is the easy case

When saving a thread, the service computes its hash and keeps that hash under the owner, thread, and revision identifiers. The user keeps the complete snapshot. On return, the service hashes the uploaded bytes and compares the result with its saved value.

The catalog entry can be this small:

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "type": "object",
  "required": ["owner_id", "thread_id", "revision", "sha256"],
  "properties": {
    "owner_id": { "type": "string" },
    "thread_id": { "type": "string" },
    "revision": { "type": "string" },
    "sha256": { "type": "string", "pattern": "^[0-9a-f]{64}$" }
  }
}
```

The snapshot uses the runtime's existing history format. The catalog contains no messages or tool results. For an authenticated owner authorized to access the thread, the comparison is:

```python
from hashlib import sha256


def matches_saved_snapshot(catalog, owner_id, thread_id, revision, upload):
    entry = catalog.get((owner_id, thread_id, revision))
    if entry is None:
        return False
    return sha256(upload).hexdigest() == entry["sha256"]
```

A match identifies the saved bytes, not the latest revision or the correctness of the conversation. The service can parse and restore that snapshot under its current policy. A catalog error should propagate as an error rather than be reported as a mismatch.

The difficult case starts when the file has legitimately changed. The user may have continued locally, the runtime may have rewritten the JSON, or compaction may have replaced messages with a summary. The whole-file hash then fails without telling us which records changed.

For an extended thread, we need to answer two separate questions: **can we still verify the old part, and how do we accept the additions?**
