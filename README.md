# Thread admission

An engineering article and runnable Python examples for accepting a user-held
agent thread back into a service.

The examples compare saved snapshots, verify an unchanged prefix, and authenticate
one model call's input and output through an operator index, DSSE, or SD-JWT.
The cross-format example compares selected message claims from a Codex App Server
transcript with claims captured at the model API boundary.

## Article

- [Assembled English article](article/context_admission_medium_v01.md)
- [Ten source sections](article/parts/)
- [Editorial notes and section guide](article/README.md)
- [Executed checks and limits](article/notes/sd-jwt-example.md)

Edit the section files, then rebuild:

```sh
python3 article/build.py
python3 article/build.py --check
```

The assembled article and its source sections were copied without text changes
from the current Medium draft on 2026-10-20. The original copy remains in the
content repository. This project does not depend on that repository at runtime.

## Run the code

Use Python 3.12. These commands work in fish as well as POSIX shells; environment
activation is unnecessary.

```sh
python3.12 -m venv .venv
.venv/bin/python -m pip install -r requirements.lock
.venv/bin/python examples/run.py
.venv/bin/python scripts/check.py
```

`requirements.txt` pins direct dependencies; `requirements.lock` records the full
environment used for verification. The examples use local fixtures and generate
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
| [schemas/](schemas/) | JSON Schemas copied from the article. |
| [fixtures/](fixtures/) | API call and App Server transcript used throughout the article. |

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
RFC conformance or production readiness. See the [verification note](article/notes/sd-jwt-example.md).

## Local history

The article and code share one Git history. Commit their changes together so the
matching implementation is preserved with each revision.

GitHub: [olegische/thread-admission](https://github.com/olegische/thread-admission).

## License

[Apache License 2.0](LICENSE).
