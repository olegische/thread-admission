# Tool Admission: What a Service May Believe About a Tool Record It Did Not Witness

*A practical look at tool calls in saved agent histories and the evidence a receiving service can use to check them.*

Suppose you are building a service for an AI assistant where users keep their conversation histories in storage they control and return them to the service when they want to continue. They may also work on the same thread with a local agent before bringing it back. How can your service trust the history it receives?

In the [previous article](../thread_admission/context_admission.md), we used evidence from a proxy that observed model calls. The receiving service could check which responses the model returned and which messages were sent to it as user input. That gave the service a way to restore those parts of the conversation.

A thread also contains tool calls and their results. Suppose a record says the agent ran `python export.py`, the command exited with code `0`, and the output was `Wrote export.csv (128 rows).` The user now asks the assistant to continue working with that export.

The proxy's evidence can show what result was sent to the model. But the result could have changed before it reached the proxy. How can the service establish what the tool itself returned?

A related issue came up in an [MCP discussion](https://github.com/modelcontextprotocol/modelcontextprotocol/pull/2817#issuecomment-5390870362). A developer described an audit tool that counted executions observed by its runtime together with executions reported by another program. The summary lost the distinction between what the runtime saw and what it was told.

MCP proposals describe records a service can use: a [signed statement of what was requested](https://github.com/modelcontextprotocol/modelcontextprotocol/pull/2787) and a [record of what the executing side decided and returned](https://github.com/modelcontextprotocol/modelcontextprotocol/pull/2828).

We will examine how a receiving service can compare evidence from the model call and the tool executor: which call the result belongs to, what the executor reported and what the model received. When evidence is missing, the service still needs a rule for retaining and using the record. We call this decision tool admission. The executor is the party that processed the tool call and returned the result; the service's policy decides whether what has been established is sufficient for the next action.

## What a saved history can establish

### Continuing from a history

Durable execution systems use saved histories to resume workflows after interruptions. One such system is [Temporal](https://docs.temporal.io/workflow-execution/event). Its history contains events such as activity results, signals and timers. An activity is work a worker performs for the workflow: it might run tests and return an exit code. Temporal records the result in the history. During replay, the workflow code runs against the saved events and must produce matching commands; a mismatch raises a nondeterminism error. Completed activities are not run again: their recorded results are supplied to the workflow.

Temporal can also [import history from another cluster](https://github.com/temporalio/temporal/blob/235e89468e3338f2ced467406a9a87ec12e030b7/service/history/replication/eventhandler/event_importer.go). The importer checks the history branch and [the sequence of event IDs](https://github.com/temporalio/temporal/blob/235e89468e3338f2ced467406a9a87ec12e030b7/service/history/ndc/replication_task.go), then uses the events to reconstruct workflow state. In a deployment where the service and workers operate within one trust boundary, the operator controls which workers can return activity results. The workflow continues using the results recorded by that system. A person establishes that trust boundary by deciding which participants the deployment accepts.

Our service may receive a thread with results from tool executors it did not operate. It needs to decide what the records establish about earlier work automatically, without a person reviewing each returned thread. The service applies rules set in advance. That question also arose in the MCP discussions.

### When execution crosses a boundary

An agent can use MCP to call a tool operated by another party. When someone later reads the record of that call, they need to know why the client made the request, what it asked for and what the executing side returned. Three proposals from the MCP community describe records for these parts of the call:

- [SEP-2817](https://github.com/modelcontextprotocol/modelcontextprotocol/pull/2817) carries context supplied by the client, such as the reason for the call and the conversation turn it belongs to. It helps explain the call; it does not establish that the call was authorized or executed.
- [SEP-2787](https://github.com/modelcontextprotocol/modelcontextprotocol/pull/2787) proposes a signed attestation of the request: the tool, its arguments and the declared purpose. The attestation identifies what was requested; execution needs its own record.
- [SEP-2828](https://github.com/modelcontextprotocol/modelcontextprotocol/pull/2828) proposes records from the executing side: a decision before the operation and an outcome after it, linked to the request. A verifier can check the signatures and links without having been present at the call.

A signed outcome lets a receiving service check which issuer made a statement about a result and whether the statement has changed. The service still needs a reason to accept that issuer's statement. The [SEP-2828 verifier discussion](https://github.com/modelcontextprotocol/modelcontextprotocol/pull/2828) makes the issuer's key and the chain part of that decision.

### Building on existing formats

The records above need to identify who supplied each value, what call and result they describe, and which checks were performed. Existing formats provide mechanisms for these jobs:

- **Who supplied a value.** A client can explain why it requested a tool call; the executor can report what it returned. [SLSA Provenance](https://slsa.dev/spec/v1.0/provenance) makes a similar distinction for builds, separating parameters supplied by the invoker from those controlled by the builder.
- **Which data a statement describes.** A call ID helps find related records. To compare their contents, an [in-toto Statement](https://github.com/in-toto/attestation/blob/main/spec/v1/statement.md) identifies its subject by a digest. We will compare digests of the arguments and result to link an executor's statement to the returned thread.
- **Which checks ran.** A missing check and a check that allowed an operation have different meanings. [XACML](https://docs.oasis-open.org/xacml/3.0/xacml-3.0-core-spec-os-en.html) defines decision outcomes; a [SLSA Verification Summary Attestation](https://slsa.dev/spec/v1.0/verification_summary) records a verification result, its policy and input attestations.

The binding also needs to cover what the executor actually received and returned. Arguments can change between recording a request and running it. The discussion of SEP-2817 calls for recomputing the binding at execution; the receiving service relies on the executor's statement about what it covered.

### How the executor obtained the result

Two tools can sign the same result, `Tests passed`: one ran the tests, the other asked a language model to predict the outcome. To distinguish them, we add the method to the executor's statement: observation, computation or generation. The receiving service can use that claim in its policy. For example, a policy requiring an observed test result before deployment would not accept the model's prediction.

Authentication uses a similar arrangement. An identity provider can report the methods used to authenticate a user through the [`amr` claim](https://www.rfc-editor.org/rfc/rfc8176). The service receiving that claim decides whether those methods are sufficient for an action. [Vectors of Trust](https://www.rfc-editor.org/rfc/rfc8485) ties the interpretation of such values to a trust framework. Here the executor describes the method, and the receiving service decides how to use the result. It also decides whether it trusts the executor to make that claim.

### Receiving the thread

A thread may return with evidence from the executor and the model call, with only one of them, or with neither. The receiving service needs to compare the records and decide what status to assign to each result. When evidence is missing, it can retain the result as supplied context and apply its policy accordingly.

Different readers may also need different parts of a record. As in the first article, we use DSSE for a complete signed record and [SD-JWT](https://www.rfc-editor.org/rfc/rfc9901) when the issuer needs to disclose selected claims. The following sections build on these pieces to admit tool records from the returned thread.

## Two kinds of evidence

In the previous article, we used evidence from the proxy to check what the model received and returned. We now add **tool evidence**: a statement by the executor about the call it received and the result it returned. Related records are described in [SEP-2828](https://github.com/modelcontextprotocol/modelcontextprotocol/pull/2828) and the [Agent Execution Evidence draft](https://datatracker.ietf.org/doc/draft-thaha-scitt-agent-execution-evidence/01/).

### A statement about the export

For the `python export.py` call from the opening, the executor could issue a statement containing these claims:

```text
issuer:       the tool executor
call:         call-1
model call:   reference to the proxy's model-call evidence
execution:    exec-1
arguments:    hash of {"cmd":"python export.py","workdir":"/workspace"}
outcome:      executed
source class: computation
result:       hash of {"content":[{"type":"text","text":"Wrote export.csv (128 rows).\n"}],
                       "structuredContent":{"exitCode":0}}
```

The executor signs these claims and makes the statement available with the thread. The reference identifies the proxy's evidence presented with the request; the execution ID identifies the executor's attempt. In this example the executor declares that the output was computed; the receiving service decides whether to accept that claim. The [tool evidence profile](parts/06-tool-statement.md) specifies the full statement and its schema.

When the thread returns, the service checks signatures from issuers it accepts and compares the evidence: did the executor receive the arguments requested by the model, and was the result the executor reported sent to the model? A mismatch tells it that the values covered by the statements differ. We will work through these checks in the next section.

The executor can attest to what it observed; checking the work of its backends requires evidence from those parties. The `source_class` claim describes how the executor obtained the result. The service uses that claim in its policy and may set its own class for a tool.

Depending on the evidence available, the service reaches four outcomes:

- **Restored:** both statements are available and their links pass; the record is restored as prior history.
- **Produced:** the executor reported the result; whether the model saw it is unknown.
- **Shown:** the result was sent to the model; its producer is not established.
- **Supplied:** no evidence is available; the record remains supplied context.

Our experiment uses [SD-JWT](https://www.rfc-editor.org/rfc/rfc9901) for the tool statement, allowing the holder to disclose selected claims. Other issuers can use their own formats; each statement is checked according to its format.

## Checking the evidence

When the thread returns, the service verifies the model and tool statements, then compares what they say about the call. The model statement covers the arguments with which the model requested the tool and the result sent to its next call. The tool statement covers the arguments the executor received and the result it returned.

Suppose `python export.py` failed with a database connection error and exit code `1`. The executor recorded that result in its statement. Before the result reached the model, it was changed to a success message with exit code `0`. The model continued as if the export had succeeded.

When the service checks the thread, it finds different results in the statements:

```text
Executor returned:    exit code 1, database connection error
Model received:       exit code 0, Wrote export.csv (128 rows).
```

Both statements can pass signature verification: the executor signed the result it returned, and the proxy signed the result sent to the model. By comparing them, the service detects the mismatch.

The service also compares the arguments requested by the model with those received by the executor. Each issuer uses its own statement format; the service verifies both and compares the values they cover.

### Comparing arguments

Our tool profile records hashes of both the argument string and the parsed object in [JCS](https://www.rfc-editor.org/rfc/rfc8785) canonical form. For example:

```text
arguments:    {"cmd":"python export.py","workdir":"/workspace"}
raw_sha256:   f272be5ff717e09cbabf10f946c667892bd94b0f5bbe36cac5e491de0eea642f
jcs_sha256:   f272be5ff717e09cbabf10f946c667892bd94b0f5bbe36cac5e491de0eea642f
```

The string is already canonical, so the hashes match. Adding spaces changes the raw hash while the canonical hash stays the same:

```text
arguments:    { "cmd": "python export.py", "workdir": "/workspace" }
raw_sha256:   d311518038a03519783d990a9720c7865a4ee70287244ceaf49dd0b3dee2e556
jcs_sha256:   f272be5ff717e09cbabf10f946c667892bd94b0f5bbe36cac5e491de0eea642f
```

The raw hash lets the service check the original string; the canonical hash lets it compare parsed objects despite formatting differences. Our profile requires both, so an executor using it must receive the original string. An executor that receives only a parsed object can issue evidence in another format; the service then uses a comparison supported by that evidence.

Results also need a shared representation. If the runtime transforms the executor's result before sending it to the model, the service needs to account for that transformation. Section 5 shows how it can repeat a known rule and compare the resulting string with the model evidence.

### Identifying the execution

In our proposed profile, the client sends the proxy's evidence with the tool call, disclosing the tool name and arguments needed for the check. The executor verifies the evidence, checks the requested tool and arguments, and records a reference to the proxy's signed evidence and `call_id` in its own statement. It also assigns an ID to the execution.

```text
Proxy evidence:   call-1 and python export.py disclosed from the model call
Tool evidence:    reference to the proxy's evidence, call-1, execution exec-1
```

When the thread returns, the service verifies both statements, checks the reference and compares the covered values. The model-evidence issuer does not need to know about the tool statement. A similar link from an execution record to a request attestation was proposed in the [SEP-2817 discussion](https://github.com/modelcontextprotocol/modelcontextprotocol/pull/2817).

The executor handles repeated requests for the same model call under an explicit retry rule, so it does not silently dispatch multiple executions for that call. The reference records the executor's account of the request it processed. The result comparison establishes what was shown to the model; it cannot trace the physical path taken by identical bytes through the client.

The next section uses these checks to decide what the service can retain as history and how it can use the result.

## Continuing from the checked history

The checks give the service a status for each tool record. The runtime then builds the input for the next model call. Consider the export from the opening: the thread says `python export.py` returned `Wrote export.csv (128 rows).`

Here is one way a runtime could construct that input:

**Restored.** The service has accepted the evidence and the link between the model's request, the executor's result and what the model was shown. The runtime retains the original tool call and result, along with subsequent assistant messages that pass their own checks. If every record in the returned thread meets the service's restoration rules, the runtime sends the returned history in its original roles. If the agent needs `export.csv` now, it can check whether the file is still available.

**Shown.** Model evidence shows that the result was sent to the model; the executor has not been established. The runtime removes the call and result from the restored tool history. It places an account of them in a new `user` message: the earlier model saw a success message, and the execution is unconfirmed. Later assistant messages may have relied on that result; the runtime includes their checked text in the same account.

**Produced.** Accepted tool evidence reports the result, but the service does not know whether the previous model received it. The runtime places the executor's report in a new `user` message as information about prior work and states that the model's receipt is unknown. It includes later assistant messages as an account of the returned history, with that gap made clear.

**Supplied.** The result has no accepted model or tool evidence. The runtime places the call and result in a new `user` message as claims from the returned thread. It includes later assistant messages in the account with the missing evidence identified; it attributes their text to the model only if model evidence verifies it.

### When evidence conflicts

The service may have both statements but find no accepted link between them, or the covered results may differ. In the example from the previous section, the executor reported a failure and the model saw a success message. The runtime can include both facts and the discrepancy in the history account; its policy can require checking the export before working with the file.

A verified assistant response establishes what the model said. If it says the export succeeded after receiving an unverified result, the account retains that context. When the next action depends on a tool result, the service applies its policy, including any rules for the issuer and `source_class`.

## From the tool result to the model

An MCP tool can return text and structured data in one result. For example:

```json
{
  "content": [
    {"type": "text", "text": "{\"temperature\":22.5}"}
  ],
  "structuredContent": {"temperature": 22.5}
}
```

The executor signs a statement containing a hash of this complete result. The runtime might select the text block and send that text to the model:

```text
{"temperature":22.5}
```

The proxy's evidence covers the string sent to the model. To compare it with the result covered by the executor, the receiving service needs the full result and a rule for the conversion. In this example, the rule takes the text from the single `content` block. The service checks the full result against the executor's hash, applies the rule and compares its output with the string in the proxy's evidence. The executor's statement also covers `structuredContent`; this rule sends the text block to the model.

The service must know and accept the rule. A runtime can transform a result in many ways; a rule that produces a matching string still needs to be suitable for the service's policy. For example, the service must consider how a rule handles errors before accepting it. The same approach can cover truncation when the rule and the full result allow the service to reproduce the text shown to the model.

Our experiment defines one such rule for an MCP result with a single text block. For a tool error, the rule adds an explicit error prefix to the text. It checks the complete signed result and repeats the conversion. Other result shapes and conversions need their own accepted rules.

## The tool evidence profile

For our profile we use [SD-JWT](https://www.rfc-editor.org/rfc/rfc9901), so the holder can disclose selected claims. A complete statement can also be carried in a DSSE envelope when selective disclosure is not needed.

The [SD-JWT VC draft](https://datatracker.ietf.org/doc/draft-ietf-oauth-sd-jwt-vc/) defines `typ: dc+sd-jwt` and a `vct` claim that identifies the credential type. We use `…/tool-call/v1` for the tool statement. Type Metadata describes its claims, including which are required and which may be selectively disclosed. Model-call evidence keeps its own issuer and format; it does not need to use this type. Our profile requires the verifier to obtain and process the applicable metadata; `vct#integrity` can protect the referenced document.

The tool statement includes:

- **Issuer and call:** `iss`, `sub`, `iat`, `call_id` and `tool_id`. These identify the executor, the account on whose behalf it ran, the time, the call and the tool.
- **Origin and execution:** optional `model_call` references the proxy's signed model-call evidence and identifies the executor's execution. Optional `caller_id` records the client identity authenticated by the executor; `client_stated_purpose` records an explanation provided by that client.
- **Outcome and method:** `outcome`, `source_class` and `tool_kind`. The outcome is `executed`, `refused`, `errored` or `cancelled`; the tool kind is `read`, `write`, `think` or `generic`.
- **Arguments and result:** digests of the arguments and result, with the result's byte length. These can be selectively disclosed. The evidence-checking section explains why the arguments have two digests.

Claims such as `iss`, `sub` and `iat` have registered meanings. The tool-specific names, including `source_class`, `tool_id`, `call_id`, `outcome`, `arguments` and `result`, are defined by our profile and interpreted under the statement's `vct`. The schema can be extended with `txn` for a transaction identifier, `cnf` for holder key binding, `status` for revocation and `jti` for uniqueness. `call_id` remains the identifier relayed from the model. We do not use the registered names `amr`, `acr`, `vot`, `vtm`, `events` or `attest` for these values.

The `model_call` field is optional, so an executor can issue a statement without a model link. For Restored, the service needs that link, the model evidence and the result checks. `client_stated_purpose` carries the client's explanation, and `caller_id` is included when the executor has authenticated the client; authorization is decided separately.

The schema below is for full-result verification. It requires a digest and length for every terminal outcome, including refusal, error, confirmed cancellation and empty output. The executor attests to a cancellation it observed; the client records a timeout or cancellation request it observed. A presentation without result disclosure, for example for audit, needs separate validation rules. The profile's reference implementation has not yet been published.

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "type": "object",
  "required": ["vct", "iss", "sub", "iat", "call_id", "tool_id",
               "source_class", "tool_kind", "outcome", "arguments", "result"],
  "properties": {
    "vct": {"type": "string"},
    "iss": {"type": "string"},
    "sub": {"type": "string"},
    "iat": {"type": "integer", "minimum": 0},
    "call_id": {"type": "string"},
    "tool_id": {"type": "string"},
    "source_class": {"enum": ["observer", "computation", "generator"]},
    "tool_kind": {"enum": ["read", "write", "think", "generic"]},
    "outcome": {"enum": ["executed", "refused", "errored", "cancelled"]},
    "model_call": {
      "type": "object",
      "required": ["issuer_jwt_sha256", "execution_id"],
      "properties": {
        "issuer_jwt_sha256": {"type": "string", "pattern": "^[0-9a-f]{64}$"},
        "execution_id": {"type": "string", "minLength": 1}
      },
      "additionalProperties": false
    },
    "caller_id": {"type": "string", "minLength": 1},
    "client_stated_purpose": {"type": "string"},
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
        "length": {"type": "integer", "minimum": 0}
      },
      "additionalProperties": false
    }
  },
  "additionalProperties": false
}
```

The `result` field carries the digest and length of the complete result. The experiment must define the deterministic envelope used for each outcome before producing test vectors. `cnf` and `status` are omitted from this schema; they concern holder binding and revocation.

### Linking the model call and tool result

For the MCP example, `result.sha256` and `result.length` cover the UTF-8 bytes of the complete `CallToolResult` encoded in JCS, including `content` and `structuredContent` when present. The holder keeps the full result for the receiver to check. The statement travels separately; it and the JSON-RPC wrapper are outside the hashed object.

To link the execution to the model call, the client presents the proxy's evidence with the disclosures needed to verify that call. The reference is the SHA-256 digest of the exact UTF-8 bytes of the issuer-signed compact JWT, excluding disclosures and key binding, so it stays stable across different presentations. The signature and disclosed claims are verified separately.

For example, a client can send the evidence with an MCP request using an application-defined `_meta` key:

```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "tools/call",
  "params": {
    "name": "run_command",
    "arguments": {"cmd": "python export.py", "workdir": "/workspace"},
    "_meta": {
      "org.example/model_evidence": "<signed-jwt>~<tool-name-disclosure>~<arguments-disclosure>~"
    }
  }
}
```

After checking the evidence and processing the call, the executor includes a reference to the signed JWT in its own statement. This is the relevant part of its claims before signing:

```json
{
  "call_id": "call-1",
  "model_call": {
    "issuer_jwt_sha256": "<sha256-of-signed-jwt>",
    "execution_id": "exec-1"
  }
}
```

The client can later present the receiver with the same signed JWT and an additional disclosure:

```json
{
  "model_evidence": "<signed-jwt>~<tool-name-disclosure>~<arguments-disclosure>~<additional-disclosure>~",
  "tool_evidence": "<signed-tool-statement>"
}
```

The values in angle brackets stand for the encoded JWT, disclosures, hash and tool statement. The receiver hashes the signed JWT and compares it with `issuer_jwt_sha256`. Both presentations refer to the same signed JWT, so the additional disclosure does not change that hash. The `_meta` key and the receiver's JSON wrapper are example application choices.

The first article's example requires all fields to be disclosed; this use needs validation rules for a selective presentation. Its signed JWT still exposes metadata including issuer, subject, response ID, item types and call IDs. Other model-evidence formats need their own way to identify the signed statement.

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

## What tool evidence does not establish

Stated as a verifier would state them.

1. A tool statement attests the executor's observation, not the state of the world. A weather service attests the forecast it returned. A payment service attests that it submitted a transaction, or that it received a confirmation, whichever it saw. The record never says what the weather was or whether the money arrived.
2. An executor can sign what it did not do. The signature establishes who made the statement, not that the statement is true. Registering statements with a transparency log makes a false statement durable and attributable; it does not make it impossible.
3. The signed reference records the executor's account of which model request it processed. Matching results show that the covered values agree; they do not trace how identical bytes travelled through the client. The checks do not establish that the thread is complete or that no later call occurred.
4. The absence of a tool statement does not establish that no operation took place. It establishes nothing, and the admission rules treat it as the normal case rather than as a finding.
5. The source class is declared by the executor about itself. A server that declares `observer` while returning generated text is the second limit again, with a different field, and a control plane that keeps its own table of classes by tool identity is entitled to override the declaration.
6. The profile carries one record per call with an `outcome`. It does not separate a decision made before the effect from the outcome observed after it, so it cannot answer "was this allowed" as distinct from "did this run". The Internet-Draft that continued SEP-2828 does separate them; the composition section says how the two fit.
7. A statement carried inside the thread, in MCP's `_meta` or in a runtime's export, depends on every intermediary preserving it. A lost statement is lost evidence, not a verification failure, and the record it would have covered drops to Shown.

### Three questions this article does not answer

Readers of the MCP threads will bring three questions here that belong elsewhere, and it is better to say so than to let them look for answers in the admission rules.

Which issuers to trust is the verifier's configuration, exactly as the trusted public key was in the earlier article: an allow-list, the operator's own gateway, a federation. The profile consumes that decision and does not make it. A statement from an issuer the service does not accept is treated as no statement, and the record it covers is Shown or Supplied. A server offering tools for breaking into things, with a perfectly valid signature, gets nothing more than that.

Whether the content is safe is the job of the input safeguards, which run on everything that enters a model call whether or not it carries evidence. Tool evidence attests origin and integrity relative to an issuer; it never certifies content as acceptable or an issuer as acceptable. The output of an unfiltered model behind an MCP server enters the next model call as client-supplied content and is screened as such. The one place where evidence and safeguards meet is the case from the earlier article: when the executor is the service itself, its own safeguards ran at execution time, and restoring the record restores a result it has already screened. What ran through the service is restored; what ran past it is new input.

Which tools the agent may call is authority, not standing: tool allow-lists, call policies, mandates. A returned record of a call to a forbidden tool is a record; whether the agent could have made that call, and whether it may make the next one, is decided by the environment it is running in now. That layer is specified elsewhere and is not touched here.

## Where this fits

**Inference admission is the base.** The earlier article's model-call evidence and this article's tool-call evidence use independent issuers and formats. The executor can refer to existing model evidence in its own statement; the model issuer does not need to issue a tool statement or use the tool statement's `vct` type. A receiving service verifies both and checks the reference and covered data.

**Existing records can contribute evidence.** SEP-2787 describes a request attestation; SEP-2828 and its successor describe decisions and outcomes. Other proposals use in-toto statements for agent audit records. A receiving service can verify a supported format and use the claims it actually covers. Whether those claims identify an executor, a call, its arguments, result or source class depends on the record and issuer; missing claims cannot be assumed.

**Where standing meets authority.** Admission produces typed records and stops. What a control plane does with `source_class` is its policy: which actions may be grounded on a generated result, which tools of which class may be called in which context, whether its own table of classes overrides an executor's declaration. This article gives one illustration of such a policy, the rejection of a generator's output as grounds for an action that needs an observation, and marks it as the control plane's rule, not admission's. The authority layer, mandates, allow-lists, gates, is a separate specification. This is the one point where the two layers touch, and the article keeps it to one point.

**Two records in time.** The decision-before-effect and outcome-after-effect split of SEP-2828 and the Verification Summary Attestation answers a question this profile does not ask, whether an operation was allowed. Admitting a thread that carries both records, with the outcome pinning the decision's digest, is the next piece of work.

**Lineage across agents.** The model closes on itself. An agent's output handed to another agent is, for the receiver, an input artifact of the same kind as a tool result: produced by an executor it did not run. The first agent's operator can issue a statement of the same shape as tool evidence, its result the handoff artifact, its class `generator`, with references by digest to the statements it consumed, the weather tool's statement, its own model statements. In in-toto terms these are `materials` and `subject`; in PROV terms, `used` and `wasGeneratedBy`; the alternating chain of one thread is the special case with one issuer of each kind. The receiving agent applies the four-row table twice. To continue the first agent's text it needs only the first agent's statement. To act on the weather it follows the references to the weather tool's statement and verifies that itself, under its own issuer configuration, independent of the first agent's word. One invariant makes this safe and its absence makes it laundering: references do not raise the class. A statement that cites an observer's statement is still a generator's statement. An action that needs an observation needs a path to an observer-class leaf from an accepted issuer with passing link checks; generator nodes along the path may transform, they may not originate. Repackaging a record is not corroboration. Specifying this across several issuers is open work; the article names it and leaves it.

### Run the examples

The reference implementation, fixtures, schemas, Type Metadata documents and the check script that keeps the code and this text in agreement are being added to the [companion repository](../../README.md) alongside the earlier article's examples. Until the experiment section reports results, treat the profile as proposed and the rules as the author's claims.
