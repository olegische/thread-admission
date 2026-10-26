## The experiment

The rules above are claims, and claims of this kind are cheap. The earlier article kept itself honest by publishing runnable examples checked against the text by a script. This article will do the same. At the time of this draft the experiment is specified and not yet run; this section states what it will test, how, and what each test is expected to show. Nothing below is reported as a result.

### Four claims under test

1. A tool result without tool evidence is indistinguishable from a substituted one, however valid the model evidence covering it.
2. The two link checks detect a substituted result and substituted arguments between neighbouring statements.
3. A signed source class distinguishes a model behind a server from a sensor when all signatures are valid.
4. Different verifiers of one tool statement need different disclosures; if they do not, whole-record signing suffices and the profile should say so.

### Setup

The issuer of tool evidence sits where the tool runs. The reference implementation uses a small open-source tool runtime whose single dispatch point validates arguments against a JSON Schema, calls the host's handler, and normalizes the result into a deterministic envelope. At that point the runtime assembles a call record: `call_id`, the two argument digests, the complete result envelope including failures, `tool_id`, the tool's declared `source_class` and `tool_kind`. A separate package signs the record as an SD-JWT under the `tool-call/v1` type with the executor's key. The handler's author writes nothing for this to happen; that is the zero-cost pattern from the receiving-side section, applied.

The issuer of model evidence is the earlier article's proxy example, unchanged except for the move to `vct` typing. The verifier and the admission rules live in the earlier article's repository, independent of both issuers, and import its model-evidence verifier rather than copying it.

The environment is a simulated tool-use benchmark with domain state held in a database file: hidden state, a real executor, an independent verifier beside it. The example thread of both articles is one of its fixtures.

### Negative cases

Each case fixes its expected outcome before it is run.

| Case | Expected |
|---|---|
| Result rewritten from exit 1 to exit 0 before the model saw it; model evidence intact | model link passes; tool link fails; record not Restored |
| Arguments in the issued function call differ from the arguments in the tool statement | argument link fails |
| Tool statement from a different `call_id` presented for this record | no link; record stays Shown |
| Shown output is a prefix of the produced result | link recorded as `truncated`; Restored with annotation |
| Shown output differs from the produced result and is not a prefix | mismatch |
| Tool statement from a different issuer under the same `call_id` and digests | verifies as a second statement; admission requires the issuer's `tool_id` to match the call's tool |
| Record with no tool statement in a thread whose message chain verifies | Shown; message matches unaffected |
| Model behind a server, class `generator`, all signatures valid | Restored as record; control-plane policy requiring an observation rejects it as grounds |
| The same case with the `source_class` claim removed | Type Metadata marks the claim mandatory and never disclosable; validation fails; statement rejected, not downgraded |
| Two verifiers present different disclosure sets of one statement | both verify; each sees only its disclosures; the auditor's set contains no result content |
| Tool statement with `outcome` of `refused`, thread claims success | contradiction surfaced; record not Restored |
| Statement with an unknown `vct` or an unknown `source_class` value | rejected; the verifier does not guess |

### Vectors

Test vectors follow the split proposed in the MCP thread's vector pull request and used in supply-chain conformance suites: normative cases cover bytes, signatures and link checks and must produce identical results in any implementation; policy cases cover lifetimes, accepted algorithms and clock skew and are normative only once the profile fixes those policies. Time-dependent cases carry a fixed verification time in their expected output. Interoperability is defined as two implementations producing the same expected output for every normative case.

### What the experiment cannot show

It runs against a simulated environment and a mock proxy. It will not show that the call record survives a real runtime's export and re-import, which the earlier article already lists as its own open issue. It will not show that any executor outside the experiment issues anything. It tests the rules, not the ecosystem.
