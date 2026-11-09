"""Run the tool admission example in two phases: the conversation, then the return.

During the conversation the proxy signs model calls and the executor signs
its statement; nothing is admitted yet. When the thread returns, the client
presents the record and the receiving service assigns a status. Both phases
run in one process here: the proxy is a mock that signs fixtures with the
first article's `issue_call`, the record is passed as a dictionary and keys
are ephemeral.
"""
from copy import deepcopy

from jwcrypto.jwk import JWK

from checks import rejects, require
from data import load_json
from digests import argument_digests, commitment
from mcp import model_input_for_mcp_result
from model_calls import present_function_call, present_items
from sdjwt import signed_jwt_sha256
from sdjwt_evidence import issue_call
from tool_evidence import Executor, issue_tool_statement, present_tool_statement, verify_tool_statement
from tool_record import admit_tool_record

EXECUTOR = "https://executor.example"
OTHER_EXECUTOR = "https://other.example"


def for_receiver(group, item):
    """What the holder discloses from the next model call: message texts and the shown result."""
    return {"message": {"text"}, "function_call_output": {"output"}}.get(item["type"])


def main():
    call_1 = load_json("fixtures/tool/model-call-1.json")
    call_2 = load_json("fixtures/tool/model-call-2.json")
    success = load_json("fixtures/tool/tool-result.json")
    failure = load_json("fixtures/tool/tool-result-error.json")
    catalog = load_json("fixtures/tool/tools.json")
    model_schema = load_json("schemas/component-call.schema.json")
    tool_schema = load_json("schemas/tool-call.schema.json")
    subject = call_1["sub"]
    request = call_1["output"][0]
    call_id, tool_name, raw_arguments = request["call_id"], request["name"], request["arguments"]

    proxy_key = JWK.generate(kty="EC", crv="P-256")
    proxy_public = JWK.from_json(proxy_key.export_public())
    executor_key = JWK.generate(kty="EC", crv="P-256")
    other_key = JWK.generate(kty="EC", crv="P-256")
    reading = {"content": [{"type": "text", "text": "{\"temperature\":22.5}"}],
               "structuredContent": {"temperature": 22.5}}
    handlers = {
        "run_command": lambda args: deepcopy(success),
        "read_sensor": lambda args: deepcopy(reading),
        "predict_temperature": lambda args: deepcopy(reading),
    }
    rejected = 0

    def executor(handler_map=handlers):
        return Executor(EXECUTOR, executor_key, catalog, handler_map, proxy_public, model_schema, tool_schema)

    def model_call(call, key=proxy_key):
        return issue_call(call["input"], call["output"], key, subject, call["response_id"])

    def refused(action, message):
        nonlocal rejected
        rejects(action, message)
        rejected += 1

    # ---- Phase 1: during the conversation ------------------------------------

    # The proxy signs the model call; the client discloses only the tool call.
    issuance_1 = model_call(call_1)
    request_evidence = present_function_call(issuance_1, call_id)
    require(request_evidence.count("~") == 3, "Expected exactly two disclosures for the executor")

    # The executor verifies the request, runs the tool and signs its result.
    result, tool_issuance = executor().call(tool_name, raw_arguments, request_evidence, subject, call_1["response_id"])
    require(result == success, "Executor returned an unexpected result")

    # The runtime converts the result; the proxy signs the next call.
    require(model_input_for_mcp_result(result) == call_2["input"][2]["output"],
            "Fixture output differs from the accepted conversion")
    next_evidence = present_items(model_call(call_2), for_receiver)
    print("PASS: model request disclosed selectively; executor verified, executed and signed")

    # What the executor refuses, before anything is executed.
    refused(lambda: executor().call(tool_name, '{"cmd":"rm -rf /","workdir":"/workspace"}',
                                    request_evidence, subject, call_1["response_id"]),
            "Executor accepted changed arguments")
    refused(lambda: executor().call("read_sensor", raw_arguments, request_evidence, subject, call_1["response_id"]),
            "Executor accepted a changed tool name")
    refused(lambda: executor().call(tool_name, raw_arguments, "", subject, call_1["response_id"]),
            "Executor ran without model evidence")
    forged = present_function_call(model_call(call_1, other_key), call_id)
    refused(lambda: executor().call(tool_name, raw_arguments, forged, subject, call_1["response_id"]),
            "Executor accepted evidence under an unknown key")
    refused(lambda: present_function_call(issuance_1, "call-2"), "Presented a call that does not exist")

    # The same model evidence replayed to the same executor: one dispatch, the same statement.
    repeat = executor()
    first = repeat.call(tool_name, raw_arguments, request_evidence, subject, call_1["response_id"])
    second = repeat.call(tool_name, raw_arguments, request_evidence, subject, call_1["response_id"])
    require(first == second and repeat.dispatched == 1, "Replayed request dispatched twice")
    rejected += 1
    print(f"PASS: {rejected} requests refused by the executor or the client's presentation")

    # ---- The thread leaves with both kinds of evidence; the client keeps them. ----

    # ---- Phase 2: when the thread returns ------------------------------------

    config = {
        "model_key": proxy_public, "subject": subject,
        "previous_response_id": call_1["response_id"], "next_response_id": call_2["response_id"],
        "tool_issuers": {EXECUTOR: JWK.from_json(executor_key.export_public())},
        "model_schema": model_schema, "tool_schema": tool_schema,
    }

    def package(previous=request_evidence, nxt=next_evidence, tool=None, tool_result=result):
        """The record the client presents: both model calls, the statement and the full result."""
        return {"call_id": call_id, "previous_model": previous, "next_model": nxt,
                "tool_statement": present_tool_statement(tool_issuance) if tool is None else tool,
                "tool_result": tool_result}

    def reissue(claims, key=executor_key):
        """A statement with the same claims under another key, or changed claims."""
        return present_tool_statement(issue_tool_statement(claims, key, tool_schema))

    def expect(label, verdict, status, *failed):
        nonlocal rejected
        require(verdict["status"] == status and all(f in verdict["discrepancy"] for f in failed),
                f"{label}: {verdict['status']} {verdict['discrepancy']} {verdict['rejected']}")
        rejected += 1

    statement = verify_tool_statement(present_tool_statement(tool_issuance), config["tool_issuers"], tool_schema)
    verdict = admit_tool_record(package(), config)
    require(verdict["status"] == "Restored" and not verdict["rejected"], f"Expected Restored: {verdict}")
    require(verdict["tool"]["source_class"] == "computation", "Declared class not carried")
    print("PASS: the returned record verified and linked; status Restored")

    digests = argument_digests(raw_arguments)
    require(digests["raw_sha256"] == digests["jcs_sha256"], "Canonical fixture arguments differ")
    require(argument_digests('{ "cmd": "python export.py", "workdir": "/workspace" }')["jcs_sha256"]
            == digests["jcs_sha256"], "JCS digest changed with whitespace")
    print("PASS: raw and canonical argument digests as in section 3")

    # Result rewritten from exit 1 to exit 0 before the model saw it.
    error_result, error_issuance = executor({**handlers, "run_command": lambda args: deepcopy(failure)}).call(
        tool_name, raw_arguments, request_evidence, subject, call_1["response_id"])
    error_statement = present_tool_statement(error_issuance)
    require(verify_tool_statement(error_statement, config["tool_issuers"], tool_schema)["outcome"] == "errored",
            "Executor did not sign the error")
    require(model_input_for_mcp_result(error_result).startswith("MCP tool error: "), "Error prefix missing")
    verdict = admit_tool_record(package(tool=error_statement, tool_result=error_result), config)
    require(verdict["checks"]["tool_result"] is True and not verdict["rejected"], "Signatures should pass")
    expect("rewritten result", verdict, "Shown", "result")

    # A statement over different arguments.
    altered = {**statement, "arguments": argument_digests('{"cmd":"python other.py","workdir":"/workspace"}')}
    expect("changed arguments", admit_tool_record(package(tool=reissue(altered)), config), "Shown", "arguments")

    # Tool statement references a different model response.
    other_response = {**call_1, "response_id": "resp-0"}
    other_evidence = present_function_call(model_call(other_response), call_id)
    misreferenced = deepcopy(statement)
    misreferenced["model_call"]["issuer_jwt_sha256"] = signed_jwt_sha256(other_evidence)
    expect("wrong reference", admit_tool_record(package(tool=reissue(misreferenced)), config), "Shown", "reference")

    # Model link missing or not verifiable.
    unlinked = {name: value for name, value in statement.items() if name != "model_call"}
    expect("unlinked, no model evidence", admit_tool_record(
        package(previous=None, nxt=None, tool=reissue(unlinked)), config), "Produced")
    expect("unlinked, model evidence present", admit_tool_record(
        package(tool=reissue(unlinked)), config), "Shown", "reference")
    expect("forged model evidence", admit_tool_record(package(previous=forged), config), "Shown", "reference")

    # Tool statement from a different call_id.
    other_call = deepcopy(call_1)
    other_call["output"][0]["call_id"] = "call-9"
    _, other_statement = executor().call(tool_name, raw_arguments,
                                         present_function_call(model_call(other_call), "call-9"),
                                         subject, call_1["response_id"])
    expect("different call_id", admit_tool_record(package(tool=present_tool_statement(other_statement)), config),
           "Shown")

    # Full result changed; shown text differs; unsupported result shape.
    changed = deepcopy(result)
    changed["structuredContent"]["exitCode"] = 1
    expect("changed full result", admit_tool_record(package(tool_result=changed), config), "Shown", "tool_result")
    shown_differs = deepcopy(call_2)
    shown_differs["input"][2]["output"] = "Wrote export.csv (0 rows).\n"
    expect("shown text differs", admit_tool_record(
        package(nxt=present_items(model_call(shown_differs), for_receiver)), config), "Shown", "result")
    two_blocks = {"content": [{"type": "text", "text": "a"}, {"type": "text", "text": "b"}]}
    verdict = admit_tool_record(package(tool=reissue({**statement, "result": commitment(two_blocks)}),
                                        tool_result=two_blocks), config)
    require(verdict["checks"]["tool_result"] is True and verdict["checks"]["result"] is None, "Shape not detected")
    expect("unsupported result shape", verdict, "Shown", "result")

    # Statements from other issuers.
    refused(lambda: verify_tool_statement(reissue(statement, other_key), config["tool_issuers"], tool_schema),
            "Unknown issuer key accepted")
    two_issuers = {**config, "tool_issuers": {**config["tool_issuers"],
                                              OTHER_EXECUTOR: JWK.from_json(other_key.export_public())}}
    duplicate = deepcopy(statement)
    duplicate.update(iss=OTHER_EXECUTOR)
    separate = admit_tool_record(package(tool=reissue(duplicate, other_key)), two_issuers)
    require(separate["status"] == "Restored" and separate["tool"]["iss"] == OTHER_EXECUTOR
            and separate["tool"]["iss"] != statement["iss"], "Statements conflated")
    rejected += 1

    # No tool statement at all; no evidence at all.
    expect("no tool statement", admit_tool_record(package(tool=""), config), "Shown")
    expect("no evidence", admit_tool_record(package(previous=None, nxt=None, tool="", tool_result=None), config),
           "Supplied")

    # Source class: a sensor reading and a prediction of the same value.
    def classify(name):
        call = deepcopy(call_1)
        call["output"][0].update(name=name, arguments="{}")
        evidence = present_function_call(model_call(call), call_id)
        value, issuance = executor().call(name, "{}", evidence, subject, call["response_id"])
        nxt = deepcopy(call_2)
        nxt["input"][1].update(name=name, arguments="{}")
        nxt["input"][2]["output"] = model_input_for_mcp_result(value)
        return admit_tool_record(package(previous=evidence, nxt=present_items(model_call(nxt), for_receiver),
                                         tool=present_tool_statement(issuance), tool_result=value), config)

    def grounds_for_observation(verdict):
        return verdict["status"] == "Restored" and verdict["tool"]["source_class"] == "observer"

    sensor, prediction = classify("read_sensor"), classify("predict_temperature")
    require(sensor["status"] == "Restored" and prediction["status"] == "Restored", "Both records restore")
    require(grounds_for_observation(sensor) and not grounds_for_observation(prediction),
            "Policy did not distinguish the classes")
    rejected += 1
    print("PASS: identical results; the policy uses the declared source class, not the bytes")

    # Statement validation: mandatory claims, result, vct, enum values, type, timing.
    for label, change in (
        ("source_class removed", lambda c: c.pop("source_class")),
        ("result removed", lambda c: c.pop("result")),
        ("unknown source_class", lambda c: c.update(source_class="oracle")),
        ("unknown outcome", lambda c: c.update(outcome="maybe")),
        ("extra claim", lambda c: c.update(extra=1)),
        ("unknown vct", lambda c: c.update(vct=c["vct"].replace("v1", "v0"))),
    ):
        claims = deepcopy(statement)
        change(claims)
        refused(lambda: reissue(claims), f"Issued: {label}")
    future = {**statement, "iat": statement["iat"] + 3600}
    refused(lambda: verify_tool_statement(reissue(future), config["tool_issuers"], tool_schema), "Accepted future iat")
    refused(lambda: verify_tool_statement(present_tool_statement(tool_issuance, disclose=("arguments",)),
                                          config["tool_issuers"], tool_schema), "Accepted withheld result")
    head, disclosure, rest = present_tool_statement(tool_issuance).split("~", 2)
    refused(lambda: verify_tool_statement("~".join([head, disclosure[:-2] + "AA", rest]),
                                          config["tool_issuers"], tool_schema), "Accepted tampered disclosure")
    print(f"PASS: {rejected} rejection cases from the article's table")
    print("LIMIT: mock proxy, in-process executor and in-memory record of issued statements; no runtime export or re-import")


if __name__ == "__main__":
    main()
