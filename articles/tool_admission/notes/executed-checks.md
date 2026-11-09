# Tool evidence example — executed checks

Updated 2026-11-08. This note is outside the article text. It records what the
companion code checks for the tool admission article, in the same form as the
first article's [per-call evidence note](../../thread_admission/notes/sd-jwt-example.md).

## What was built

The proxy, the executor and the receiving service are code in `examples/`,
in the same package as the first article's examples. The proxy issues
model-call evidence with the first article's `issue_call`; the first
article's published functions are unchanged. The argument link now compares
both digests, raw and canonical, against the executor's statement.

| Code | Purpose |
|---|---|
| `examples/sdjwt.py` | Issue, present and verify an SD-JWT for any profile; every rejection is a ValueError. The first article's functions are the published special case and stay verbatim. |
| `examples/digests.py` | Raw and canonical argument digests; digest and length of a JSON value in JCS. |
| `examples/model_calls.py` | Disclose chosen claims of chosen items of model-call evidence (for the executor: the tool name and arguments of one call); verify a selective presentation; locate one call's items. |
| `examples/mcp.py` | The accepted conversion of an MCP result into the model's input. |
| `examples/tool_evidence.py` | The executor's SD-JWT statement under `typ: dc+sd-jwt` and the `tool-call/v1` type; an `Executor` that verifies the request, dispatches once per (reference, `call_id`) and signs the result. |
| `examples/tool_record.py` | `link_checks`, `admission_status` (section 4) and `admit_tool_record`, the receiving service's path from presentations to a status. |
| `examples/run_tool.py` | Phase 1, the conversation: signing and the executor's refusals. Phase 2, the return: admission of the record and the receiver's verdicts. |
| `schemas/tool-call.schema.json` | The section 6 schema. |
| `fixtures/tool/` | The model call that requested `run_command`, the full MCP result for success and for the database error, the next model call that received the converted result, and the tool catalog with `source_class`. |

`scripts/check.py` keeps the code in sections 7 and 8 identical to the modules, the schema identical to section 6, and recomputes the two argument
digests printed in section 3 from the fixture string.

## Fixtures

The first article's fixture shows the model a runtime-wrapped output
(`Chunk ID`, `Process exited with code 0`, `Output:`). The conversion rule in
section 5 sends the text of a single content block. The two do not agree, so
the tool article has its own fixtures under `fixtures/tool/` with a clean MCP
result; the first article's fixtures are untouched. The model received
`Wrote export.csv (128 rows).\n`, which is what the rule produces from the
signed result.

## Reproduction

Executed against Python 3.12, `sd-jwt==0.10.4`, `jwcrypto==1.6.1`,
`jsonschema==4.26.0`, `rfc8785==0.1.4`.

```sh
uv sync --locked
uv run --locked python examples/run_tool.py
uv run --locked python scripts/check.py
```

## Executed checks

Positive path: the proxy signs the model call; the client presents it with
exactly two disclosures, the tool name and arguments of `call-1`; the executor
verifies the presentation, compares it with the request, runs the handler,
signs a statement with the reference digest; the runtime converts
the result with the section 5 rule and the proxy signs the next call; the
service verifies everything and returns **Restored**.

Rejection cases, 30 in all, each with its expected outcome fixed before the run:

- Executor signed the database error (`outcome: errored`); the result shown to the model was rewritten to success. Both signatures verify, the full-result check passes, the result comparison fails; the record is Shown with the `result` discrepancy, not Restored.
- Executor refuses a request whose arguments or tool name differ from the disclosed call. A statement over different arguments fails the argument link.
- A statement referencing another model response fails the reference check.
- Executor refuses to run without model evidence or with evidence under an unknown key. A statement without `model_call` is Produced when no model evidence is present and Shown when it is. Forged model evidence leaves the record Shown.
- The same model evidence and `call_id` submitted twice dispatches once and returns the same execution.
- A statement from a different `call_id` leaves the record Shown.
- Changed full result fails the commitment check; shown text that differs from the conversion fails the result comparison; a two-block result makes the comparison `None` and the record is not Restored.
- A statement under a key the service does not accept is rejected. A second accepted issuer signing the same digests verifies as a separate statement identified by its issuer.
- No tool statement: Shown. No evidence: Supplied.
- `run_command` and `predict_command_output` return identical success bytes; both records are Restored; a policy asking whether the export ran accepts the `computation` class and not the `generator` class (the `Tests passed` case of section 1).
- Removing `source_class` or `result`, an unknown `source_class` or `outcome`, an extra claim, a future `iat`, an unknown `vct`, a presentation withholding `result`, and a tampered disclosure are all rejected.
- Presenting a `call_id` that is not in the signed response is rejected.

## Limits

The proxy is a mock that signs fixtures; the executor runs in process and
takes the raw argument string directly, so the JSON-RPC wrapper and the `_meta`
key from section 6 are not exercised. The record of issued statements is a
dictionary: the replay rule is tested in one process, not under concurrency or
after a restart. No Type Metadata document is published; the verifier checks
`vct` against a constant. The library gap from the first article remains:
`sd-jwt 0.10.4` accepts unreferenced disclosures. No runtime export or
re-import was tested.
