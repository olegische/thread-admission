# Thread admission

Engineering articles and runnable Python examples for accepting a user-held
agent thread back into a service.

The examples compare saved snapshots, verify an unchanged prefix, and authenticate
one model call's input and output through an operator index, DSSE, or SD-JWT.
The cross-format example compares selected message claims from a Codex App Server
transcript with claims captured at the model API boundary.

## Articles

### Thread admission

- [Published on Medium](https://medium.com/@romoleg/agent-history-lives-on-the-users-device-how-can-an-ai-service-verify-it-f3344cdd4cbd)
- [Assembled English article](articles/thread_admission/context_admission.md)
- [Ten source sections](articles/thread_admission/parts/)
- [Editorial notes and section guide](articles/thread_admission/README.md)
- [Executed checks and limits](articles/thread_admission/notes/sd-jwt-example.md)

Edit the section files, then rebuild:

```sh
uv run --locked python articles/thread_admission/build.py
uv run --locked python articles/thread_admission/build.py --check
```

The assembled article and its source sections were initially copied without text
changes from the article draft on 2026-10-20. The previous draft location now links
to this repository. This project does not depend on that repository at runtime.

### Tool admission (draft)

- [Assembled English draft](articles/tool_admission/tool_admission_v01.md)
- [Eleven source sections](articles/tool_admission/parts/)
- [Editorial notes and draft status](articles/tool_admission/README.md)
- [Executed checks and limits](articles/tool_admission/notes/executed-checks.md)

Edit the section files, then rebuild:

```sh
uv run --locked python articles/tool_admission/build.py
uv run --locked python articles/tool_admission/build.py --check
```

## Run the code

Use [uv](https://docs.astral.sh/uv/). The project pins Python 3.12 in
`.python-version`. These commands work in fish as well as POSIX shells;
environment activation is unnecessary.

```sh
uv sync --locked
uv run --locked python examples/run.py
uv run --locked python examples/run_tool.py
uv run --locked python scripts/check.py
```

`pyproject.toml` declares the project and its direct dependencies; `uv.lock`
locks the resolved dependency graph. `uv sync --locked` creates `.venv` from that
lockfile without changing it. The examples use local fixtures and generate
ephemeral demo keys in memory. They make no model API calls and save no keys or
disclosure packages to disk.

| Code | Purpose |
|---|---|
| [snapshot.py](examples/snapshot.py) | Recognize saved snapshot bytes against a catalog entry. |
| [prefix.py](examples/prefix.py) | Verify the prefix at a saved offset and separate the unverified tail. |
| [call_index.py](examples/call_index.py) | Record and compare full input/output arrays for one completed model call. |
| [dsse_envelope.py](examples/dsse_envelope.py) | Sign and verify that record with a single-signature DSSE envelope. |
| [sdjwt_evidence.py](examples/sdjwt_evidence.py) | Issue, present and verify selected claims using the reference SD-JWT library. |
| [runtime_adapter.py](examples/runtime_adapter.py) | Match returned user/assistant messages to authenticated claims. |
| [run.py](examples/run.py) | Run all examples using checked-in fixtures. |
| [sdjwt.py](examples/sdjwt.py) | Issue, present and verify an SD-JWT for any profile; digest of the signed JWT. |
| [digests.py](examples/digests.py) | Raw and canonical argument digests; digest and length of a JSON value. |
| [model_calls.py](examples/model_calls.py) | Disclose chosen claims of chosen items of model-call evidence and verify such a presentation. |
| [mcp.py](examples/mcp.py) | The accepted conversion of an MCP result into the model's input. |
| [tool_evidence.py](examples/tool_evidence.py) | The tool statement profile and an executor that verifies the request, dispatches once and signs. |
| [tool_record.py](examples/tool_record.py) | Link checks, the admission status and the receiving service's path for one tool record. |
| [run_tool.py](examples/run_tool.py) | Run the tool admission example and its rejection table. |
| [checks.py](examples/checks.py) | Assertions shared by the run scripts. |
| [schemas/](schemas/) | JSON Schemas copied from the article. |
| [fixtures/](fixtures/) | API call and App Server transcript used throughout the first article; `fixtures/tool/` holds the tool article's model calls, MCP results and tool catalog. |

The standalone modules execute independently of Markdown. The check script also
compares their function definitions, constants, schemas and fixtures with the
article and runs the original published-code checks, including 43 rejection cases.
If a published algorithm changes, update both copies deliberately.

## What the evidence establishes

The inference proxy observes a completed call, scoped by the authenticated API
account and agent-facing response ID. It does not observe runtime thread identity
or know whether the runtime selected its latest call. Request-side assistant
messages remain client-supplied context. The text adapter leaves the returned tool
record uncovered; observing its report at the API boundary does not prove execution.

These are executable article examples, not a deployed proxy or a complete admission
service. Streaming capture, evidence delivery, runtime integration, authentication,
key management and admission policy are not implemented here. The examples consume
finalized items. No live Codex/proxy round trip is claimed.

The pinned `sd-jwt==0.10.4` reference release predates RFC 9901 and accepts
unreferenced disclosures. The checks reproduce that gap; they do not establish full
RFC conformance or production readiness. See the [verification note](articles/thread_admission/notes/sd-jwt-example.md).

## Local history

The article and code share one Git history. Commit their changes together so the
matching implementation is preserved with each revision.

GitHub: [olegische/thread-admission](https://github.com/olegische/thread-admission).

## License

[Apache License 2.0](LICENSE).
