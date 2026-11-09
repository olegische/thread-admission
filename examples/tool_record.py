"""Admission of one tool record from a returned thread.

`link_checks` compares verified claims; `admission_status` applies the
rules of section 4; `admit_tool_record` is the receiving service's path
from presentations to a status.
"""
from digests import argument_digests, commitment
from mcp import model_input_for_mcp_result
from model_calls import find_call_item, verify_selected
from sdjwt import signed_jwt_sha256
from tool_evidence import verify_tool_statement


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


def admission_status(model_shown, tool_accepted, reference_ok, checks):
    """What the receiving service may retain, per section 4.

    model_shown: accepted model evidence covers the result sent to the model.
    tool_accepted: an accepted issuer's tool statement verified.
    reference_ok: the tool statement references the accepted model evidence.
    """
    if model_shown and tool_accepted:
        links = {"reference": reference_ok, **checks}
        failed = [name for name, link in links.items() if link is not True]
        return {"status": "Restored" if not failed else "Shown", "discrepancy": failed}
    if model_shown:
        return {"status": "Shown", "discrepancy": []}
    if tool_accepted:
        return {"status": "Produced", "discrepancy": []}
    return {"status": "Supplied", "discrepancy": []}


def admit_tool_record(package, config):
    """Admit one tool record.

    package: previous_model, next_model, tool_statement (SD-JWT presentations
             or None), tool_result (full MCP result or None) and call_id.
    config:  model_key, subject, previous_response_id, next_response_id,
             tool_issuers, model_schema, tool_schema.
    """
    rejected = {}

    def accepted(name, verify):
        if not package.get(name):
            return None
        try:
            return verify(package[name])
        except ValueError as error:
            rejected[name] = str(error)
            return None

    previous = accepted("previous_model", lambda p: verify_selected(
        p, config["model_key"], config["subject"], config["previous_response_id"], config["model_schema"]))
    next_model = accepted("next_model", lambda p: verify_selected(
        p, config["model_key"], config["subject"], config["next_response_id"], config["model_schema"]))
    tool = accepted("tool_statement", lambda p: verify_tool_statement(
        p, config["tool_issuers"], config["tool_schema"]))

    call_id = package["call_id"]
    shown = find_call_item(next_model, "request", "function_call_output", call_id)
    model_shown = shown is not None and "output" in shown
    reference_ok = (tool is not None and previous is not None and tool["call_id"] == call_id
                    and tool.get("model_call", {}).get("issuer_jwt_sha256")
                    == signed_jwt_sha256(package["previous_model"]))
    checks = link_checks(previous, tool or {"call_id": call_id}, next_model, package.get("tool_result"))
    decision = admission_status(model_shown, tool is not None, reference_ok, checks)
    return {**decision, "checks": checks, "reference": reference_ok, "rejected": rejected, "tool": tool}
