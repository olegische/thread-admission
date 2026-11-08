## The experiment

We will test these rules on a tool call and a returned thread.

### Setup

The environment is a simulated tool-use benchmark with domain state held in a database file: hidden state, a real executor, an independent verifier beside it. The example thread of both articles is one of its fixtures.

The issuer of tool evidence sits where the tool runs. The planned implementation uses a small open-source tool runtime whose single dispatch point validates arguments against a JSON Schema and calls the host's handler. For a model-originated request, the client also sends the proxy's evidence with disclosures for the requested tool and its arguments. The executor verifies it, checks that the disclosed tool name, `call_id` and arguments match the request, and assigns an execution ID before dispatch. The runtime assembles a call record with the reference, execution ID, argument digests, result digest, `tool_id`, the tool's declared `source_class` and `tool_kind`. A separate package signs it as an SD-JWT under the `tool-call/v1` type with the executor's key. The handler's author does not need to add signing code.

The executor durably reserves the pair of the model-evidence digest and `call_id` before dispatch, scoped to its own identity. For retries it returns the existing execution or reports that it is still in progress; it does not dispatch a second execution under the same pair. After a crash, the executor may be unable to determine whether dispatch occurred and must retain that uncertainty. A call ID must identify exactly one disclosed function call in the model response. A deliberate new execution requires a new model call. This rule does not prevent a different executor from receiving the same evidence; the receiving service must handle multiple statements. It is part of the experiment and must be tested under concurrent retries and after a restart.

### Four claims under test

1. A tool result without tool evidence is indistinguishable from a substituted one, however valid the model evidence covering it.
2. The two link checks detect a substituted result and substituted arguments between neighbouring statements.
3. One tool reads a temperature sensor; another asks a model to predict the temperature. Their executors sign the results and declare `source_class`. The receiving service can use those claims to distinguish a sensor reading from a prediction when it accepts the issuers' claims.
4. A receiving service can repeat an accepted conversion of an MCP result and compare it with the result shown to the model.

### Comparing covered values

This example compares claims after each statement has been verified and its issuer accepted. It selects candidates by `call_id`, checks the arguments and verifies the full MCP result against the tool statement. It then repeats a rule accepted by the receiver: for a result with one text block, send that block's text to the model, adding an error prefix if `isError` is true. It compares the resulting string with the proxy's evidence. The rule does not support other result shapes.

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


def model_input_for_mcp_result(result):
    """Convert one text block, preserving the MCP tool error flag."""
    if not isinstance(result, dict):
        return None
    is_error = result.get("isError", False)
    if type(is_error) is not bool:
        return None
    content = result.get("content")
    if not isinstance(content, list) or len(content) != 1:
        return None
    block = content[0]
    if not isinstance(block, dict) or block.get("type") != "text":
        return None
    value = block.get("text")
    if not isinstance(value, str):
        return None
    return "MCP tool error: " + value if is_error else value


def link_checks(previous_model, tool, next_model, tool_result):
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

    def check_result(result):
        commitment = tool.get("result")
        if not isinstance(result, dict) or not isinstance(commitment, dict):
            return None
        digest = commitment.get("sha256")
        length = commitment.get("length")
        if not isinstance(digest, str) or type(length) is not int:
            return None
        try:
            encoded = rfc8785.dumps(result)
        except (TypeError, ValueError):
            return None
        return len(encoded) == length and sha256(encoded).hexdigest() == digest

    call = find_one(previous_model, "response", "function_call")
    shown = find_one(next_model, "request", "function_call_output")
    verified_result = check_result(tool_result)
    expected = model_input_for_mcp_result(tool_result) if verified_result else None
    shown_output = shown.get("output") if shown else None
    return {
        "arguments": compare(call.get("arguments") if call else None,
                             tool.get("arguments", {}).get("raw_sha256")),
        "tool_result": verified_result,
        "result": (shown_output == expected
                   if isinstance(shown_output, str) and expected is not None
                   else None),
    }
```

Each check returns `True` for a match, `False` for a mismatch and `None` when the data is missing, the candidate is ambiguous or the conversion rule does not apply. The receiver selects the rule under its own policy; the example does not accept executable rules from the returned thread. The function does not verify signatures, compare canonical argument hashes or establish that the statements concern the same execution. Those checks require additional inputs and rules.

### Negative cases

Each case fixes its expected outcome before it is run.

| Case | Expected |
|---|---|
| Result rewritten from exit 1 to exit 0 before the model saw it; model evidence intact | model link passes; tool link fails; record not Restored |
| Arguments in the issued function call differ from the arguments in the tool statement | argument link fails |
| Tool statement references a different model response | reference check fails; record not Restored |
| Model evidence is missing or its signature fails | executor does not issue a model-linked statement; a receiver cannot establish the link |
| Same model evidence and `call_id` submitted concurrently or after restart | at most one dispatch; retries refer to the same execution or report it in progress |
| Tool statement from a different `call_id` presented for this record | no link; record stays Shown |
| Full result verifies, and applying the accepted conversion yields the shown text | result comparison passes; Restored also requires the other checks |
| Full result has been changed | result commitment check fails |
| Full result verifies, but shown text differs from the accepted conversion | result comparison fails |
| Conversion is unknown or the result shape is unsupported | comparison cannot be made; result link is not restored |
| Tool statement from a different issuer under the same `call_id` and digests | verifies as a separate statement; matching values alone do not establish the same execution |
| Record with no tool statement in a thread whose message chain verifies | Shown; message matches unaffected |
| A tool asks a model to predict the temperature and declares `source_class: generator`; all signatures are valid and execution binding is established | Restored as a record; a policy requiring a sensor reading does not use the prediction as grounds |
| The same case with the `source_class` claim removed | Type Metadata marks the claim mandatory and never disclosable; validation fails; statement rejected, not downgraded |
| Tool statement with `outcome` of `refused`, thread claims success | contradiction surfaced; record not Restored |
| Terminal tool statement omits `result` | full-result validation fails for every outcome |
| Statement with an unknown `vct` or an unknown `source_class` value | rejected; the verifier does not guess |

### Vectors

Test vectors follow the split proposed in the MCP thread's vector pull request and used in supply-chain conformance suites: normative cases cover bytes, signatures and link checks and must produce identical results in any implementation; policy cases cover lifetimes, accepted algorithms and clock skew and are normative only once the profile fixes those policies. Time-dependent cases carry a fixed verification time in their expected output. Interoperability is defined as two implementations producing the same expected output for every normative case.

### What the experiment cannot show

It runs against a simulated environment and a mock proxy. It will not show that the call record survives a real runtime's export and re-import, which the earlier article already lists as its own open issue. It will not show that any executor outside the experiment issues anything. It tests the rules, not the ecosystem.
