## The experiment

The rules above are claims, and claims of this kind are cheap. The earlier article kept itself honest by publishing runnable examples checked against the text by a script. This article will do the same. At the time of this draft the experiment is specified and not yet run; this section states what it will test, how, and what each test is expected to show. Nothing below is reported as a result.

### Four claims under test

1. A tool result without tool evidence is indistinguishable from a substituted one, however valid the model evidence covering it.
2. The two link checks detect a substituted result and substituted arguments between neighbouring statements.
3. A signed source class distinguishes a model behind a server from a sensor when all signatures are valid.
4. Different verifiers of one tool statement need different disclosures; if they do not, whole-record signing suffices and the profile should say so.

### Setup

The issuer of tool evidence sits where the tool runs. The reference implementation uses a small open-source tool runtime whose single dispatch point validates arguments against a JSON Schema, calls the host's handler, and normalizes the result into a deterministic envelope. At that point the runtime assembles a call record: `call_id`, the two argument digests, the complete result envelope including failures, `tool_id`, the tool's declared `source_class` and `tool_kind`. A separate package signs the record as an SD-JWT under the `tool-call/v1` type with the executor's key. The handler's author does not need to add signing code.

The experiment uses the earlier article's proxy example for model evidence without changing its format. The proposed receiving-side verifier checks model and tool evidence separately, reusing the existing model-evidence verifier, and then applies the admission rules.

### Comparing covered values

This example compares claims after each statement has been verified and its issuer accepted. It selects candidates by `call_id` and compares the model's argument and result strings with the hashes in the tool statement.

```python
from hashlib import sha256
import json
import rfc8785


def argument_digests(raw_arguments):
    parsed = json.loads(raw_arguments)
    return {
        "raw_sha256": sha256(raw_arguments.encode("utf-8")).hexdigest(),
        "jcs_sha256": sha256(rfc8785.dumps(parsed)).hexdigest(),
    }


def link_checks(previous_model, tool, next_model):
    """Compare verified claims; None means the check could not be made."""
    call_id = tool.get("call_id")

    def find_one(evidence, group, item_type):
        if evidence is None or call_id is None:
            return None
        matches = [item for item in evidence.get(group, [])
                   if item.get("type") == item_type
                   and item.get("call_id") == call_id]
        return matches[0] if len(matches) == 1 else None

    def compare(value, expected_digest):
        if not isinstance(value, str) or not isinstance(expected_digest, str):
            return None
        return sha256(value.encode("utf-8")).hexdigest() == expected_digest

    call = find_one(previous_model, "response", "function_call")
    shown = find_one(next_model, "request", "function_call_output")
    return {
        "arguments": compare(call.get("arguments") if call else None,
                             tool.get("arguments", {}).get("raw_sha256")),
        "result": compare(shown.get("output") if shown else None,
                          tool.get("result", {}).get("sha256")),
    }
```

Each comparison returns `True` for a match, `False` for a mismatch and `None` when the data is missing or the candidate is ambiguous. The function does not verify signatures, compare canonical argument hashes or establish that the statements concern the same execution. Those checks require additional inputs and rules.

### Tool statement for the experiment

For our profile we use [SD-JWT](https://www.rfc-editor.org/rfc/rfc9901), so the holder can disclose selected claims. A complete statement can also be carried in a DSSE envelope when selective disclosure is not needed.

The [SD-JWT VC draft](https://datatracker.ietf.org/doc/draft-ietf-oauth-sd-jwt-vc/) defines `typ: dc+sd-jwt` and a `vct` claim that identifies the credential type. We use `…/tool-call/v1` for the tool statement. Type Metadata describes its claims, including which are required and which may be selectively disclosed. Model-call evidence keeps its own issuer and format; it does not need to use this type. Our profile requires the verifier to obtain and process the applicable metadata; `vct#integrity` can protect the referenced document.

The tool statement includes:

- **Issuer and call:** `iss`, `sub`, `iat`, `call_id` and `tool_id`. These identify the executor, the account on whose behalf it ran, the time, the call and the tool.
- **Outcome and method:** `outcome`, `source_class` and `tool_kind`. The outcome is `executed`, `refused` or `errored`; the tool kind is `read`, `write`, `think` or `generic`.
- **Arguments and result:** digests of the arguments and result, with the result's byte length. These can be selectively disclosed. The evidence-checking section explains why the arguments have two digests.

Claims such as `iss`, `sub` and `iat` have registered meanings. The tool-specific names, including `source_class`, `tool_id`, `call_id`, `outcome`, `arguments` and `result`, are private names interpreted under the statement's `vct`. We may use `txn` as an additional shared transaction identifier; `call_id` remains the identifier relayed from the model. Holder key binding, revocation and uniqueness can use `cnf`, `status` and `jti`. We do not reuse `amr`, `acr`, `vot`, `vtm`, `events` or `attest` for our private meanings.

The schema below describes the tool claims after disclosure for this experiment. The profile is proposed and its reference implementation has not yet been published.

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "type": "object",
  "required": ["vct", "iss", "sub", "iat", "call_id", "tool_id",
               "source_class", "tool_kind", "outcome", "arguments"],
  "properties": {
    "vct": {"type": "string"},
    "iss": {"type": "string"},
    "sub": {"type": "string"},
    "iat": {"type": "integer", "minimum": 0},
    "call_id": {"type": "string"},
    "tool_id": {"type": "string"},
    "source_class": {"enum": ["observer", "computation", "generator"]},
    "tool_kind": {"enum": ["read", "write", "think", "generic"]},
    "outcome": {"enum": ["executed", "refused", "errored"]},
    "arguments": {
      "type": "object",
      "required": ["raw_sha256", "jcs_sha256"],
      "properties": {
        "raw_sha256": {"type": "string", "pattern": "^[0-9a-f]{64}$"},
        "jcs_sha256": {"type": "string", "pattern": "^[0-9a-f]{64}$"}
      },
      "additionalProperties": false
    },
    "result": {
      "type": "object",
      "required": ["sha256", "length"],
      "properties": {
        "sha256": {"type": "string", "pattern": "^[0-9a-f]{64}$"},
        "length": {"type": "integer", "minimum": 0},
        "parts": {"type": "object", "additionalProperties": {"type": "string"}}
      },
      "additionalProperties": false
    }
  },
  "additionalProperties": false
}
```

The schema permits `result` to be omitted, including when a refusal or error has no result body. When present, `result` carries a digest and length; `parts` can hold the executor's own subdivision for disclosure. The schema does not require `result` for an `executed` outcome, so an additional profile rule would be needed if a verifier must require it. `cnf` and `status` are omitted from this schema; they concern holder binding and revocation.

### Environment

The environment is a simulated tool-use benchmark with domain state held in a database file: hidden state, a real executor, an independent verifier beside it. The example thread of both articles is one of its fixtures.

### Negative cases

Each case fixes its expected outcome before it is run.

| Case | Expected |
|---|---|
| Result rewritten from exit 1 to exit 0 before the model saw it; model evidence intact | model link passes; tool link fails; record not Restored |
| Arguments in the issued function call differ from the arguments in the tool statement | argument link fails |
| Tool statement from a different `call_id` presented for this record | no link; record stays Shown |
| Shown output matches a verified full result under the truncation convention | comparison recorded as `truncated`; Restored only if the execution binding is also established |
| Shown output differs from the verified result under the truncation convention | mismatch |
| Tool statement from a different issuer under the same `call_id` and digests | verifies as a separate statement; matching values alone do not establish the same execution |
| Record with no tool statement in a thread whose message chain verifies | Shown; message matches unaffected |
| Model behind a server, class `generator`, all signatures valid and execution binding established | Restored as record; control-plane policy requiring an observation rejects it as grounds |
| The same case with the `source_class` claim removed | Type Metadata marks the claim mandatory and never disclosable; validation fails; statement rejected, not downgraded |
| Two verifiers present different disclosure sets of one statement | both verify; each sees only its disclosures; the auditor's set contains no result content |
| Tool statement with `outcome` of `refused`, thread claims success | contradiction surfaced; record not Restored |
| Statement with an unknown `vct` or an unknown `source_class` value | rejected; the verifier does not guess |

### Vectors

Test vectors follow the split proposed in the MCP thread's vector pull request and used in supply-chain conformance suites: normative cases cover bytes, signatures and link checks and must produce identical results in any implementation; policy cases cover lifetimes, accepted algorithms and clock skew and are normative only once the profile fixes those policies. Time-dependent cases carry a fixed verification time in their expected output. Interoperability is defined as two implementations producing the same expected output for every normative case.

### What the experiment cannot show

It runs against a simulated environment and a mock proxy. It will not show that the call record survives a real runtime's export and re-import, which the earlier article already lists as its own open issue. It will not show that any executor outside the experiment issues anything. It tests the rules, not the ecosystem.
