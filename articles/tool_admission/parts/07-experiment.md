## Running the profile

The companion code runs the profile against an export call and a returned tool record. A mock proxy signs model-call fixtures using the first article's code; the executor and receiving service are Python modules in the repository. Each run generates temporary keys in memory.

### The export call

The proxy signs the model response that requests `run_command`. The client discloses the tool name and arguments to the executor. The executor verifies the presentation, requires exactly one disclosed function call and checks its name and arguments against the request. It runs the handler and signs a tool statement with the result and the reference to the proxy's signed JWT. In this example, the handler returns a prepared MCP result from `fixtures/tool/`.

The runtime converts that result to the string sent to the next model call. The mock proxy signs the next call, and the receiving service verifies the model and tool statements. For the matching fixtures, the checks pass and the service assigns the record **Restored**. The handler and proxy use fixtures; the example makes no model API call.

The run checks four points:

1. A tool result without tool evidence is indistinguishable from a substituted one, however valid the model evidence covering it.
2. Comparing the covered arguments and results detects substitutions between the model call and the executor's statement.
3. The sensor and prediction handlers return identical fixture data, with `observer` and `generator` classes respectively. A policy requiring an observation accepts the first and does not use the second as grounds.
4. The receiver can repeat the accepted conversion of an MCP result and compare it with the string covered by model evidence.

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


def commitment(value):
    """Digest and length of a JSON value in its canonical (JCS) encoding."""
    encoded = rfc8785.dumps(value)
    return {"sha256": sha256(encoded).hexdigest(), "length": len(encoded)}


def find_call_item(evidence, group, item_type, call_id):
    """The one item of `item_type` for `call_id` in a group of claims, else None."""
    if evidence is None or call_id is None:
        return None
    matches = [item for item in evidence.get(group, [])
               if item.get("type") == item_type and item.get("call_id") == call_id]
    return matches[0] if len(matches) == 1 else None


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
    call = find_call_item(previous_model, "response", "function_call", call_id)
    shown = find_call_item(next_model, "request", "function_call_output", call_id)

    def compare(value, expected, digest):
        try:
            return digest(value) == expected if value is not None and expected is not None else None
        except (TypeError, ValueError):
            return None

    verified_result = compare(tool_result, tool.get("result"), commitment)
    expected = model_input_for_mcp_result(tool_result) if verified_result else None
    shown_output = shown.get("output") if shown else None
    return {
        "arguments": compare(call.get("arguments") if call else None,
                             tool.get("arguments"), argument_digests),
        "tool_result": verified_result,
        "result": (shown_output == expected
                   if isinstance(shown_output, str) and expected is not None
                   else None),
    }
```

Each check returns `True` for a match, `False` for a mismatch and `None` when the data is missing, the candidate is ambiguous or the conversion rule does not apply. The receiver selects the rule under its own policy; the example does not accept executable rules from the returned thread. The function does not verify signatures or establish that the statements concern the same execution. Those checks require additional inputs and rules.

### Checks and results

The code runs the matching case and 30 rejection and boundary checks. The [results note](../notes/executed-checks.md) records the run and its versions. Among the cases:

- **Changed result.** The executor signs a database error and the proxy signs a success message shown to the model. Both signatures verify; the result comparison fails, and the service returns Shown with a `result` discrepancy.
- **Changed request.** The executor rejects a tool name or arguments that differ from the disclosed model call. The receiver detects a signed statement over different arguments.
- **Missing or different model evidence.** The executor rejects absent evidence or evidence signed by an unknown key. A tool statement that references a different model call fails the reference check. An unlinked statement is Produced without model evidence and Shown when model evidence covers the result.
- **Replayed request.** Presenting the same model evidence twice to the same executor instance produces one dispatch and returns the same statement.
- **Result and conversion.** Changing the full result fails its commitment check. Changed model input fails the result comparison. An unsupported two-block result leaves that comparison unavailable.
- **Missing evidence.** A record without a tool statement is Shown when model evidence covers it; a record without either kind of evidence is Supplied.
- **Source class.** Both the simulated sensor reading and prediction are Restored. The example policy accepts the declared `observer` class as grounds for an observation and does not accept `generator` for that purpose.
- **Statement validation.** Removing `source_class` or `result`, using an unknown class, outcome or `vct`, adding an extra claim, withholding the result or changing a disclosure is rejected. JSON Schema requires `source_class`; the example does not mark it for selective disclosure.

### Limits of the example

The proxy signs fixtures, and the executor and receiving service run in process. The JSON-RPC wrapper and `_meta` field illustrated in section 6 are not exercised. The record of issued statements is held in memory and checked within one process. An executor operating across restarts or in parallel must durably store the model-evidence digest and `call_id` and coordinate access. If a failure occurs between execution and recording, the executor may not know whether the operation ran; it must retain that uncertainty rather than execute again.

The verifier checks `vct` against a constant; no Type Metadata document is published for this example. The `sd-jwt` library limitation described in the first article remains: version `0.10.4` accepts unreferenced disclosures. The run does not exercise a real runtime's thread export and re-import.
