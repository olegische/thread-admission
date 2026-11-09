"""The tool evidence profile: the executor's statement about one call."""
import json
from time import time

from digests import argument_digests, commitment
from model_calls import verify_selected
import sdjwt

TOKEN_TYPE = "dc+sd-jwt"  # SD-JWT VC header type.
VCT = "https://thread-admission.example/tool-call/v1"
DISCLOSABLE = ("arguments", "result")


def issue_tool_statement(claims, key, schema):
    sdjwt.validated(claims, schema)
    if claims["vct"] != VCT:
        raise ValueError("Unexpected tool statement type")
    return sdjwt.issue(sdjwt.selective(claims, DISCLOSABLE), key, TOKEN_TYPE)


def present_tool_statement(issuance, disclose=DISCLOSABLE):
    return sdjwt.present(issuance, dict.fromkeys(disclose, True))


def verify_tool_statement(presentation, accepted_issuers, schema):
    """Full-result verification: the schema requires the arguments and result claims."""
    claims = sdjwt.verify(presentation, accepted_issuers, TOKEN_TYPE, schema)
    if claims["vct"] != VCT:
        raise ValueError("Unknown tool statement type")
    return claims


class Executor:
    """A tool executor that verifies the model's request and signs its result.

    `handlers` maps tool identifiers to functions of the parsed arguments
    returning an MCP `CallToolResult`; `catalog` declares each tool's
    `source_class`. Statements are keyed by the model evidence digest
    and `call_id`: presenting the same evidence again returns the existing
    statement. The store is a dictionary in memory.
    """

    def __init__(self, issuer, key, catalog, handlers, model_key, model_schema, tool_schema):
        self.issuer, self.key = issuer, key
        self.catalog, self.handlers = catalog, handlers
        self.model_key, self.model_schema, self.tool_schema = model_key, model_schema, tool_schema
        self.executions = {}
        self.dispatched = 0

    def call(self, tool_name, raw_arguments, model_evidence, subject, response_id):
        """Process one tools/call request; returns (result, tool statement issuance)."""
        claims = verify_selected(model_evidence, self.model_key, subject, response_id, self.model_schema)
        disclosed = [item for item in claims["response"]
                     if item.get("type") == "function_call" and "name" in item]
        if len(disclosed) != 1:
            raise ValueError("Expected exactly one disclosed function call")
        call = disclosed[0]
        if call["name"] != tool_name or call["arguments"] != raw_arguments:
            raise ValueError("Request differs from the disclosed model call")
        if tool_name not in self.catalog:
            raise ValueError("Unknown tool")
        key = (sdjwt.signed_jwt_sha256(model_evidence), call["call_id"])
        if key not in self.executions:
            result = self.handlers[tool_name](json.loads(raw_arguments))
            self.dispatched += 1
            tool = self.catalog[tool_name]
            statement = {
                "vct": VCT, "iss": self.issuer, "sub": subject, "iat": int(time()),
                "call_id": call["call_id"], "tool_id": tool["tool_id"],
                "source_class": tool["source_class"],
                "outcome": "errored" if result.get("isError") else "executed",
                "model_call": {"issuer_jwt_sha256": key[0]},
                "arguments": argument_digests(raw_arguments),
                "result": commitment(result),
            }
            self.executions[key] = (result, issue_tool_statement(statement, self.key, self.tool_schema))
        return self.executions[key]
