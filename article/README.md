# Context admission

An English engineering article about accepting a user-held agent thread back into a service.

- [Assembled article](context_admission.md)
- [Source sections](parts/)
- [Build script](build.py)
- [Codex example checked against source code](notes/codex-thread-example.md)

## Sections and argument

| File | Content |
|---|---|
| [00-opening.md](parts/00-opening.md) | A user stores a thread and returns it to the service: what the backend does when they select Continue. |
| [01-what-returning-a-thread-means.md](parts/01-what-returning-a-thread-means.md) | Codex example; record integrity and scope; import versus admission; four return scenarios; the separate boundary for approvals and audit. |
| [02-choose-what-you-need-to-preserve.md](parts/02-choose-what-you-need-to-preserve.md) | Three continuation options: summarize the whole submission, restore a verified prefix and summarize the tail, or compare returned content with proxy observations. |
| [03-snapshot-and-catalog.md](parts/03-snapshot-and-catalog.md) | A minimal catalog entry with a hash, its JSON Schema, Python comparison, and the transition to changed histories. |
| [04-verified-prefix-and-summary.md](parts/04-verified-prefix-and-summary.md) | A verified prefix and tail compaction: offset and hash, JSON Schema, Python, and continuation from a summary. |
| [05-verify-api-requests-and-responses.md](parts/05-verify-api-requests-and-responses.md) | Complete input/output arrays for one call; an operator index scoped by API account and response ID; whole-item hashing and comparison without thread IDs, global positions, or cross-call deduplication. |
| [06-portable-verification.md](parts/06-portable-verification.md) | Signed evidence for one completed call: full input/output, payload schema, and DSSE; retrieval by response ID as a proxy extension. |
| [07-metadata-loss-and-compaction.md](parts/07-metadata-loss-and-compaction.md) | Definitions of thread, transcript, model context, and response output; why equal API items obscured the difference between these objects; when the last complete call is sufficient; the conceptual save/admission flow; transition to SD-JWT. |
| [08-sd-jwt-component-evidence.md](parts/08-sd-jwt-component-evidence.md) | Claims for a specific call, disclosure policy, and an existing SD-JWT API: issuance, client-held disclosures and salts, presentation, verification, and claim extraction from a runtime transcript. |
| [09-conclusion.md](parts/09-conclusion.md) | Choosing a mechanism: the runtime associates its thread with a call, and the receiving service verifies the covered values. |

The [return-path test matrix](notes/return-path-test-matrix.md) is outside the publication build. It is a working checklist, not a report that every listed test has been executed.

## Editorial decisions

The scope covers integrity of returned history, coverage of additions, format conversion, and compaction. It excludes content provenance/data lineage, citations, links between model conclusions and sources, answer truth, and WCA. Tool call/result links remain part of the thread structure. No new `origin` fields or permitted-use maps are introduced.

Data structures use JSON Schema; logic uses readable Python. The article uses neither Mermaid nor ASCII diagrams.

The explanation was rewritten rather than merely shortened. There is no abstract, R1–R8 requirement catalog, mandatory L0–L3 ladder, or separate survey of every source. The earlier levels are expressed through concrete choices: supplied context, reuse of verification results, verifiable records, and action controls.

The assumptions remain: user-held storage, limited operator records, no guaranteed access to original artifacts, and a distinction between preserving a record and establishing what it reports. The catalog is one implementation choice. Messages and tool results travel with evidence for history integrity and coverage. Permissions, approval decisions, and environment audit are not portable thread state in this problem. Audit events are collected separately through environment telemetry; their storage, protection, verification, and exchange are outside scope. In the checked Codex implementation, OTel logs and traces differ: `tool_decision` uses log-only export.

The worked thread asks an agent to create a CSV file. Its payloads, pseudocode, and tests are illustrative; no deployment or measured results are claimed. The published article contains no internal ADRs, issue IDs, project paths, or private-code links.

Public facts link directly to primary documents in the article. Claude Desktop behavior, transcript provenance, and preserved thinking were checked against documentation on 2026-10-17. A transfer format is not presented as proof of a product's security policy. DSSE signs application-defined verification data; it does not supply a complete thread-return protocol.

The proxy's observation unit in sections 5–8 is one inference call. It attests to the complete received input and finalized output, bound to the API account and response ID. It does not assign thread IDs, global positions, predecessor chains, or an item's first occurrence. Repeated context appears again in the next call's evidence. An assistant role in the input is authenticated as client-supplied context, not as proven earlier model output.

Section 7 distinguishes a runtime thread from a call's context, then describes the conceptual algorithm: the runtime freezes a revision, selects the corresponding completed call, saves its evidence, and returns that evidence with the transcript; the receiver compares the covered values. One complete call may cover the required context without proving that it is the latest call in the thread. Section 8 implements this flow using SD-JWT and an existing library. Section 7 also retains template-with-a-hole as a working alternative that can expose sensitive metadata.

SD-JWT uses JWS directly, rather than nesting inside section 6's DSSE envelope. RFC 9901 defines disclosures and their protection; claim selection, API-account/response-ID binding, and comparison rules belong to the application profile. The example uses `sd-jwt==0.10.4`. Full RFC conformance is not claimed: acceptance of unreferenced disclosures is reproduced and documented. The text adapter compares message claims and retains request/response membership, but does not verify returned tool records or their positions in the runtime thread. The client holds disclosures and salts; delayed retrieval of the complete package requires transient proxy retention.

The [published-code checker](notes/check_sdjwt_example.py) extracts Python and JSON directly from the sections, executes issuance, presentation, verification, and matching, and checks rejection cases and the DSSE path. See the [SD-JWT example note](notes/sd-jwt-example.md) for details and commands.

## Build

From the repository root:

```sh
uv run --locked python article/build.py
uv run --locked python article/build.py --check
```

Edit `article/parts/`, then run the build. The script joins ten sections in a fixed order; `--check` verifies that the assembled file matches them exactly. The article ends with section 9's conclusion. Section 1 defines the approval/audit boundary, while the test matrix remains in the technical notes.

The first edition had **5,025 words versus 10,950 in academic v04**, a **54.1% reduction**. Both counts split the Markdown body on whitespace, excluding YAML and References but including headings, tables, and code. This is a historical comparison for the first edition; the current build reports the article's word count without depending on the academic repository.
