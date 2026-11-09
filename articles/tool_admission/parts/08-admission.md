## When the thread returns

When the user returns a saved thread to continue working, the client sends it to the service with its evidence. The service checks each tool call as a separate record. For one call, it needs the tool statement and full result, along with evidence for the model call that requested the tool and the model call that received its result. The example collects these in `record`. The receiving service uses its own `config`, containing accepted issuer keys and schemas, to verify the statements, check their reference and compare the covered data. For the matching fixtures, the service assigns the record **Restored**.

### Comparing covered values

For each returned tool record, the service decides what it can retain and assigns one of the statuses from section 4. It verifies each presentation against an accepted issuer's key, checks that the tool statement references the model evidence presented with the record, compares the arguments and results covered by the statements, and applies the admission rules. `admit_tool_record` takes the record and the service's configuration and returns a status, discrepancies and any verification errors.

```python
def admit_tool_record(record, config):
    """Admit one tool record.

    record:  previous_model, next_model, tool_statement (SD-JWT presentations
             or None), tool_result (full MCP result or None) and call_id.
    config:  model_key, subject, previous_response_id, next_response_id,
             tool_issuers, model_schema, tool_schema.
    """
    rejected = {}

    # 1. Verify each presentation the client returned. A statement that fails is
    #    recorded and treated as absent; the record is not rejected for it.
    def accepted(name, verify):
        if not record.get(name):
            return None
        try:
            return verify(record[name])
        except ValueError as error:
            rejected[name] = str(error)
            return None

    previous = accepted("previous_model", lambda p: verify_selected(
        p, config["model_key"], config["subject"], config["previous_response_id"], config["model_schema"]))
    next_model = accepted("next_model", lambda p: verify_selected(
        p, config["model_key"], config["subject"], config["next_response_id"], config["model_schema"]))
    tool = accepted("tool_statement", lambda p: verify_tool_statement(
        p, config["tool_issuers"], config["tool_schema"]))

    # 2. Model evidence covers the result only if the next call's verified claims
    #    include the output shown to the model for this call_id.
    call_id = record["call_id"]
    shown = find_call_item(next_model, "request", "function_call_output", call_id)
    model_shown = shown is not None and "output" in shown
    # 3. The reference: the statement names this call_id and the digest of the
    #    signed model JWT the client returned, computed here, not taken on trust.
    reference_ok = (tool is not None and previous is not None and tool["call_id"] == call_id
                    and tool.get("model_call", {}).get("issuer_jwt_sha256")
                    == signed_jwt_sha256(record["previous_model"]))
    # 4. Compare the covered values, then apply the section 4 rules to get a status.
    checks = link_checks(previous, tool or {"call_id": call_id}, next_model, record.get("tool_result"))
    decision = admission_status(model_shown, tool is not None, reference_ok, checks)
    return {**decision, "checks": checks, "reference": reference_ok, "rejected": rejected, "tool": tool}
```

A presentation that fails verification is recorded as rejected and treated as absent; the service assigns the record a status based on the evidence that remains.

The comparison has three parts: the arguments requested by the model against the two digests from section 3; the full MCP result against its digest and length from section 6; and the string shown to the model against the result transformed by the rule from section 5. `link_checks` performs these comparisons. The helper `argument_digests` computes the two argument digests, and `commitment` computes a result's digest and length. `model_input_for_mcp_result` applies the conversion rule: it takes the text from one text block and adds an error prefix if `isError` is true. The rule is designed for one text block. If the result contains, for example, multiple blocks or an image, the comparison requires another conversion rule. The service selects rules under its own policy; the example does not execute rules supplied with the returned thread. `find_call_item` selects one item by `call_id` and returns `None` if there is no match or more than one.

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
    # 1. Select by call_id: the model's request in the previous call and the output
    #    shown to the model in the next call. An absent or ambiguous item gives None.
    call_id = tool.get("call_id")
    call = find_call_item(previous_model, "response", "function_call", call_id)
    shown = find_call_item(next_model, "request", "function_call_output", call_id)

    def compare(value, expected, digest):
        try:
            return digest(value) == expected if value is not None and expected is not None else None
        except (TypeError, ValueError):
            return None

    # 2. The full MCP result the client returned must match the digest and length
    #    the executor signed. Only then is the conversion rule applied to it.
    verified_result = compare(tool_result, tool.get("result"), commitment)
    expected = model_input_for_mcp_result(tool_result) if verified_result else None
    shown_output = shown.get("output") if shown else None
    # 3. Three links: the model's raw argument string against both digests the
    #    executor signed; the returned result against the statement; the string
    #    shown to the model against the accepted conversion of that result.
    return {
        "arguments": compare(call.get("arguments") if call else None,
                             tool.get("arguments"), argument_digests),
        "tool_result": verified_result,
        "result": (shown_output == expected
                   if isinstance(shown_output, str) and expected is not None
                   else None),
    }
```

Each check returns `True` for a match, `False` for a mismatch and `None` when the data is missing, the `call_id` matches more than one item or the conversion rule does not apply. Restored requires every check to return `True`.

For the matching fixtures, the reference and all three comparisons pass, and the service returns Restored. The cases below change the evidence or data and show how the checks and status respond.

### Checks and results

The code runs the matching case and 30 rejection and boundary checks: six before the record returns and 24 in the receiving phase. The [results note](../notes/executed-checks.md) records the run and its versions. Among the receiving-side cases:

- **Changed result.** The executor signs a database error and the proxy signs a success message shown to the model. Both signatures verify; the result comparison fails, and the service returns Shown with a `result` discrepancy.
- **Changed arguments or reference.** A signed statement over different arguments fails the argument check. A statement that references a different model call fails the reference check.
- **Missing or different model evidence.** An unlinked statement is Produced without model evidence and Shown when model evidence covers the result. Evidence signed by an unknown key fails verification.
- **Different call or issuer.** A statement for another `call_id` is not linked. An unknown issuer's statement is rejected; a second accepted issuer's statement is checked separately.
- **Result and conversion.** Changing the full result fails its commitment check. Changed model input fails the result comparison. An unsupported two-block result leaves that comparison unavailable.
- **Missing evidence.** A record without a tool statement is Shown when model evidence covers it; a record without either kind of evidence is Supplied.
- **Source class.** The `run_command` and `predict_command_output` fixtures return the same `Wrote export.csv (128 rows).` text; the first declares `computation` and the second `generator`. Both records are Restored. A policy requiring evidence that the export was executed accepts the first claim and does not accept the second as grounds, as in the `Tests passed` example in section 1.
- **Statement validation.** Removing `source_class` or `result`, using an unknown class, outcome or `vct`, adding an extra claim, setting `iat` in the future, withholding the result or changing a disclosure is rejected. JSON Schema requires `source_class`; the example does not mark it for selective disclosure.

The run shows four things. Without a tool statement, a result cannot be told from a substituted one, however valid the model evidence that covers it. Comparing the values covered by the two statements detects a substitution between the model call and the executor. The receiver can repeat the conversion rule it accepts and compare the resulting string with the model evidence. Restored answers what the model was shown, not whether the result may serve as grounds; that question needs the source class and the receiver's policy.

### Limits of the example

The proxy signs fixtures, and the executor and receiving service run in process. The JSON-RPC wrapper and `_meta` field illustrated in section 6 are not exercised.

The verifier checks `vct` against a constant; no Type Metadata document is published for this example. The `sd-jwt` library limitation described in the first article remains: version `0.10.4` accepts unreferenced disclosures. The run does not exercise a real runtime's thread export and re-import.
