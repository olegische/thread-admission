"""Selective use of the first article's model-call evidence.

`sdjwt_evidence.issue_call` issues the evidence and `present` discloses all
of it. The functions here disclose chosen claims of chosen items, verify
such a presentation, and locate the items of one tool call.
"""
from copy import deepcopy

import sdjwt
from sdjwt_evidence import ISSUER, TOKEN_TYPE

DISCLOSABLE = {"text", "name", "arguments", "output"}


def find_call_item(evidence, group, item_type, call_id):
    """The one item of `item_type` for `call_id` in a group of claims, else None."""
    if evidence is None or call_id is None:
        return None
    matches = [item for item in evidence.get(group, [])
               if item.get("type") == item_type and item.get("call_id") == call_id]
    return matches[0] if len(matches) == 1 else None


def present_items(issuance, choose):
    """Disclose, for each signed item, the claim names `choose(group, item)` returns."""
    signed = sdjwt.signed_payload(issuance)
    selection = {
        group: [dict.fromkeys(choose(group, item) or (), True) for item in signed[group]]
        for group in ("request", "response")
    }
    return sdjwt.present(issuance, selection)


def present_function_call(issuance, call_id):
    """Disclose the tool name and arguments of one function call, nothing else."""
    call = find_call_item(sdjwt.signed_payload(issuance), "response", "function_call", call_id)
    if call is None:
        raise ValueError("call_id must identify exactly one function call")
    return present_items(issuance, lambda group, item: {"name", "arguments"} if item == call else None)


def selective_schema(schema):
    """The model-call schema with the disclosable claims made optional."""
    relaxed = deepcopy(schema)
    for variant in relaxed["$defs"]["observation"]["oneOf"]:
        variant["required"] = [name for name in variant["required"] if name not in DISCLOSABLE]
    return relaxed


def verify_selected(presentation, public_key, subject, response_id, schema):
    """Verify a selective presentation; undisclosed claims are absent from the result."""
    claims = sdjwt.verify(presentation, {ISSUER: public_key}, TOKEN_TYPE, selective_schema(schema))
    if (claims["sub"], claims["response_id"]) != (subject, response_id):
        raise ValueError("Wrong API subject or response")
    return claims
