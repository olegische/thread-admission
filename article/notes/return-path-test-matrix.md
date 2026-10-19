# Return-path validation matrix

Editorial working note, outside the publication. Updated 2026-10-20 for per-call evidence. This is a design checklist, not a report that every row was implemented. Executed checks are documented in [sd-jwt-example.md](sd-jwt-example.md).

| Test input or failure | Expected behavior |
|---|---|
| Supply duplicate JSON object keys | Reject during parsing rather than silently replacing values. |
| Change, remove, duplicate or reorder snapshot records | Exact-snapshot recognition fails. |
| Append local work | Whole-snapshot digest changes; a protected checkpoint can still recognize its unchanged prefix. |
| Compact an unverified tail | Keep the verified prefix unchanged; treat the summary as new supplied context. |
| Save a checkpoint with pending tool calls | Wait for a completed boundary required by that checkpoint contract. |
| Change records before the saved prefix offset or return too few records | Prefix recognition fails. |
| Substitute a submitted checkpoint for the catalog checkpoint | Use the authorized catalog's reference. |
| Split output text into different streaming deltas | Finalized item evidence is independent of delta boundaries. |
| Interrupt a response before completion | Do not issue it as a completed-call record. |
| Replay earlier context in a later full request | Record it again as part of the later request's input. |
| Supply assistant messages or function calls in request input | They can be authenticated as client-supplied context; this alone does not prove prior model generation. |
| Change a whole API item, array length, order or request/response membership | Per-call whole-item comparison fails. |
| Change function arguments or call IDs in a whole-item path | The item's digest changes. |
| Use another API account or require another response ID | Scope checks reject that record. |
| Present evidence from another runtime thread with matching content | Per-call evidence has no runtime-thread binding; compare covered values and apply import policy. |
| Substitute another valid call for a specifically selected response | Response-ID scope or content comparison fails. |
| Choose an older valid call | It remains valid call evidence, without proving it is the latest call in the runtime thread. |
| Modify a DSSE payload or payload type | Signature or supported-type verification fails. |
| Issue SD-JWT evidence for the last full-input call | Include all request input and completed output, not only new input items. |
| Change a disclosed value or salt | Required original claims are not authenticated successfully. |
| Omit a disclosure required by the profile | Application-schema validation fails. |
| Add an unreferenced disclosure | A conforming RFC 9901 verifier rejects it; the pinned reference release has a documented gap. |
| Change subject, response ID or ordered arrays inside the signed JWT | Signature verification fails. |
| Regenerate runtime record IDs but keep selected values | Claim comparison may pass; runtime IDs remain outside coverage. |
| Change, reorder or duplicate returned message claims | The worked message-sequence comparison fails. |
| Find an assistant-role claim in authenticated request input | Report that it was observed in request, not that it was generated in response. |
| Change a returned tool record while preserving the two messages | The text adapter still matches only messages; do not report full-thread verification. |
| Return a transformed shell or MCP result | Require an adapter for the selected values; do not infer lost content from digests. |
| Receive only a delta plus an opaque provider reference | Do not claim full-context coverage without establishing the resolved input. |
| Return old records replaced by a summary before the selected call | The call covers its summary, not the discarded originals. |
| Add work after the selected completed call | The added records have no coverage from that evidence. |
| Retrieve evidence at save/unsubscribe time | Return evidence captured during the call; do not retroactively attest a new upload. |
| Delete the ready package before delayed retrieval | Report it unavailable; discarded disclosures cannot be recovered from their digests. |
| Require no content retention after call completion | Deliver disclosures to the client at completion rather than retaining a later-retrieval package. |
| Put approvals into an uploaded transcript | They do not restore permissions or the environment's audit trail. |
| Fail to reach an index or evidence endpoint | Report verification unavailable, not successful recognition. |

Exercise actual persistence, read APIs, export, import and compaction for every supported runtime. Isolated signature tests do not establish that the ready package and its salts survive that path.

The receiving service should distinguish snapshot recognition, verified-prefix continuation, and comparison with an observed model-call context. API-account identity, response identity, runtime thread identity and latest revision are different claims. Only assert those supported by the chosen reference and evidence.
