# Tool evidence example — executed checks

Updated 2026-11-10. This note is outside the article text. It records what the
companion code checks for the tool admission article, in the same form as the
first article's [per-call evidence note](../../thread_admission/notes/sd-jwt-example.md).

## What was built

The proxy, the executor and the receiving service are code in `examples/`,
in the same package as the first article's examples. The proxy issues
model-call evidence with the first article's `issue_call`, and the first
article's published functions are unchanged.

| Code | Purpose |
|---|---|
| `examples/sdjwt.py` | Issue, present and verify an SD-JWT for any profile. Every rejection is a `ValueError`. |
| `examples/digests.py` | Raw and canonical argument digests (section 3). Digest and length of a JSON value in JCS (section 6). |
| `examples/model_calls.py` | Disclose chosen claims of chosen items of model-call evidence. For the executor these are the tool name and arguments of one call. Verify a selective presentation and locate one call's items by `call_id`. |
| `examples/mcp.py` | The accepted conversion of an MCP result into the model's input (section 5). |
| `examples/tool_evidence.py` | The executor's SD-JWT statement under `typ: dc+sd-jwt` and the `tool-call/v1` type. An `Executor` that verifies the request, executes once per (model-evidence digest, `call_id`) and signs the result. |
| `examples/tool_record.py` | `admit_tool_record`, the receiving service's path from one returned record to a status. It uses `link_checks` to compare the covered values and `admission_status` for the section 4 rules. |
| `examples/run_tool.py` | The run in two phases. During the conversation: signing and the executor's refusals. When the thread returns: admission of the record and the service's verdicts. |
| `schemas/tool-call.schema.json` | The section 6 schema. |
| `fixtures/tool/` | The model call that requested `run_command`, the full MCP result for success and for the database error, the next model call that received the converted result, and the tool catalog with each tool's `source_class`. |

`scripts/check.py` keeps the code blocks in sections 7 and 8 identical to the
modules and the schema identical to section 6. It recomputes the two argument
digests printed in section 3 from the fixture string, and checks that the
fixtures agree with each other and with the request example in section 6.

## Fixtures

The first article's fixture shows the model a runtime-wrapped output
(`Chunk ID`, `Process exited with code 0`, `Output:`). The conversion rule in
section 5 sends the text of a single content block. The two do not agree, so
the tool article has its own fixtures under `fixtures/tool/` with a clean MCP
result, and the first article's fixtures are untouched. The model received
`Wrote export.csv (128 rows).\n`, which is what the rule produces from the
signed result.

The catalog has two tools that return the same success result for
`python export.py`. `run_command` declares `computation`.
`predict_command_output` stands for a tool that predicts the output without
running the command and declares `generator`. This is the `Tests passed` case
of section 1 inside the export example.

## Reproduction

Executed on 2026-11-10 against Python 3.12.13, `sd-jwt==0.10.4`,
`jwcrypto==1.6.1`, `jsonschema==4.26.0`, `rfc8785==0.1.4`.

```sh
uv sync --locked
uv run --locked python examples/run_tool.py
uv run --locked python scripts/check.py
```

## Executed checks

The run has a matching case and 30 rejection and boundary cases. Each case has
its expected outcome fixed in the code before the run. Six cases belong to the
conversation and 24 to the return, as in sections 7 and 8.

### During the conversation

Matching case. The proxy signs the model call. The client presents it with
exactly two disclosures, the tool name and arguments of `call-1`. The executor
verifies the presentation, compares it with the request, runs the handler and
signs a statement with the reference digest. The runtime converts the result
with the section 5 rule and the proxy signs the next call.

Six cases before the record returns:

- The executor refuses a request whose arguments differ from the disclosed call.
- The executor refuses a request that names a different tool.
- The executor refuses to run without model evidence.
- The executor refuses model evidence signed by a key it does not accept.
- The client cannot present a `call_id` that is not in the signed response.
- The same model evidence presented twice to the same executor runs the handler once and returns the same statement.

### When the thread returns

Matching case. The service verifies both model presentations and the tool
statement, checks the reference, compares the covered values and returns
**Restored**.

24 cases on the receiving side:

- **Changed result (1).** The executor signed the database error with `outcome: errored`, and the result shown to the model was rewritten to success. Both signatures verify and the full-result check passes. The result comparison fails, and the record is Shown with the `result` discrepancy.
- **Changed arguments or reference (2).** A statement over different arguments fails the argument link. A statement referencing another model response fails the reference check.
- **Missing or different model evidence (3).** A statement without `model_call` is Produced when no model evidence is present and Shown when it is. Model evidence under an unknown key fails verification and leaves the record Shown.
- **Different call or issuer (3).** A statement from a different `call_id` leaves the record Shown. A statement under a key the service does not accept is rejected. A second accepted issuer signing the same digests verifies as a separate statement identified by its issuer.
- **Result and conversion (3).** A changed full result fails the commitment check. Shown text that differs from the conversion fails the result comparison. A two-block result makes the comparison `None`, and the record is not Restored.
- **Missing evidence (2).** No tool statement: Shown. No evidence at all: Supplied.
- **Source class (1).** `run_command` and `predict_command_output` return identical bytes and both records are Restored. A policy asking whether the export ran accepts the `computation` class and not the `generator` class.
- **Statement validation (9).** Rejected: `source_class` removed, `result` removed, an unknown `source_class`, an unknown `outcome`, an extra claim, an unknown `vct`, an `iat` in the future, a presentation withholding `result`, and a tampered disclosure.

## Limits

The proxy is a mock that signs fixtures. The executor runs in process and
takes the raw argument string directly, so the JSON-RPC wrapper and the `_meta`
key from section 6 are not exercised. The record of issued statements is a
dictionary: the replay rule is tested in one process, not under concurrency or
after a restart. No Type Metadata document is published, and the verifier
checks `vct` against a constant. The library gap from the first article
remains: `sd-jwt 0.10.4` accepts unreferenced disclosures. No runtime export
or re-import was tested.
