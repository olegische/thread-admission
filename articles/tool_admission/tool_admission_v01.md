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
arguments:    hash of {"cmd":"python export.py","workdir":"/workspace"}
outcome:      executed
source class: computation
result:       hash of {"content":[{"type":"text","text":"Wrote export.csv (128 rows).\n"}],
                       "structuredContent":{"exitCode":0}}
```

The executor signs these claims and makes the statement available with the thread. The reference identifies the proxy's evidence presented with the request. In this example the executor declares that the output was computed; the receiving service decides whether to accept that claim. The [tool evidence profile](parts/06-tool-statement.md) specifies the full statement and its schema.

When the thread returns, the service checks signatures from issuers it accepts and compares the evidence: did the executor receive the arguments requested by the model, and was the result the executor reported sent to the model? A mismatch tells it that the values covered by the statements differ. We will work through these checks in the next section.

The executor can attest to what it observed; checking the work of its backends requires evidence from those parties. The `source_class` claim describes how the executor obtained the result. The service uses that claim in its policy and may set its own class for a tool.

Depending on the evidence available, the service reaches four outcomes:

- **Restored:** both statements are available and their links pass; the record is restored as prior history.
- **Produced:** the executor reported the result; whether the model saw it is unknown.
- **Shown:** the result was sent to the model; its producer is not established.
- **Supplied:** no evidence is available; the record remains supplied context.

Our example uses [SD-JWT](https://www.rfc-editor.org/rfc/rfc9901) for the tool statement, allowing the holder to disclose selected claims. Other issuers can use their own formats; each statement is checked according to its format.

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

In our proposed profile, the client sends the proxy's evidence with the tool call, disclosing the tool name and arguments needed for the check. The executor verifies the evidence, checks the requested tool and arguments, and records a reference to the proxy's signed evidence and `call_id` in its own statement.

```text
Proxy evidence:   call-1 and python export.py disclosed from the model call
Tool evidence:    reference to the proxy's evidence, call-1
```

When the thread returns, the service verifies both statements, checks the reference and compares the covered values. The model-evidence issuer does not need to know about the tool statement. A similar link from an execution record to a request attestation was proposed in the [SEP-2817 discussion](https://github.com/modelcontextprotocol/modelcontextprotocol/pull/2817).

Once an executor has issued a statement for a model call, presenting the same evidence and `call_id` again returns that statement without executing the call again. A new tool call in the runtime has a new `call_id` and receives its own statement. The reference records the executor's account of the request it processed. The result comparison establishes what was shown to the model; it cannot trace the physical path taken by identical bytes through the client.

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

The runnable example in sections 7 and 8 uses this rule for an MCP result with one text block. It verifies the full result and compares the converted text with the proxy's evidence. Other result shapes and conversions need their own accepted rules.

## The tool evidence profile

For our profile we use [SD-JWT](https://www.rfc-editor.org/rfc/rfc9901), so the holder can disclose selected claims. A complete statement can also be carried in a DSSE envelope when selective disclosure is not needed.

The [SD-JWT VC draft](https://datatracker.ietf.org/doc/draft-ietf-oauth-sd-jwt-vc/) defines `typ: dc+sd-jwt` and a `vct` claim that identifies the credential type. Our example uses `https://thread-admission.example/tool-call/v1` for the tool statement and checks this value against a constant. The profile provides for Type Metadata to describe its claims, including which are required and which may be selectively disclosed; `vct#integrity` can protect the referenced document. Model-call evidence keeps its own issuer and format.

The tool statement includes:

- **Issuer and call:** `iss`, `sub`, `iat`, `call_id` and `tool_id`. These identify the executor, the account on whose behalf it ran, the time, the call and the tool.
- **Origin and execution:** optional `model_call` references the proxy's signed model-call evidence. Optional `caller_id` records the client identity authenticated by the executor; `client_stated_purpose` records an explanation provided by that client.
- **Outcome and method:** `outcome` and `source_class`. The outcome is `executed`, `refused`, `errored` or `cancelled`.
- **Arguments and result:** digests of the arguments and result, with the result's byte length. These can be selectively disclosed. The evidence-checking section explains why the arguments have two digests.

Claims such as `iss`, `sub` and `iat` have registered meanings. The tool-specific names, including `source_class`, `tool_id`, `call_id`, `outcome`, `arguments` and `result`, are defined by our profile and interpreted under the statement's `vct`. For a linked call, the issuer, model-evidence digest and `call_id` identify the execution under the replay rule. The schema can be extended with `txn` for a transaction identifier, `cnf` for holder key binding, `status` for revocation and `jti` to identify the statement. `call_id` remains the identifier relayed from the model. We do not use the registered names `amr`, `acr`, `vot`, `vtm`, `events` or `attest` for these values.

The `model_call` field is optional, so an executor can issue a statement without a model link. For Restored, the service needs that link, the model evidence and the result checks. `client_stated_purpose` carries the client's explanation, and `caller_id` is included when the executor has authenticated the client; authorization is decided separately.

The schema below is for full-result verification. It requires a digest and length for every terminal outcome, including refusal, error, confirmed cancellation and empty output. The executor attests to a cancellation it observed; the client records a timeout or cancellation request it observed. A presentation without result disclosure, for example for audit, needs separate validation rules. The [example implementation](../../examples/run_tool.py) is in the companion repository.

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "type": "object",
  "required": ["vct", "iss", "sub", "iat", "call_id", "tool_id",
               "source_class", "outcome", "arguments", "result"],
  "properties": {
    "vct": {"type": "string"},
    "iss": {"type": "string"},
    "sub": {"type": "string"},
    "iat": {"type": "integer", "minimum": 0},
    "call_id": {"type": "string"},
    "tool_id": {"type": "string"},
    "source_class": {"enum": ["observer", "computation", "generator"]},
    "outcome": {"enum": ["executed", "refused", "errored", "cancelled"]},
    "model_call": {
      "type": "object",
      "required": ["issuer_jwt_sha256"],
      "properties": {
        "issuer_jwt_sha256": {"type": "string", "pattern": "^[0-9a-f]{64}$"}
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

The `result` field carries the digest and length of the complete `CallToolResult` encoded in JCS. A tool error carries `isError` in that result. The example issues statements for successful results and errors. `cnf` and `status` are omitted from this schema; they concern holder binding and revocation.

### Linking the model call and tool result

For the MCP example, `result.sha256` and `result.length` cover the UTF-8 bytes of the complete `CallToolResult` encoded in JCS, including `content` and `structuredContent` when present. The holder keeps the full result for the receiver to check. The statement travels separately; it and the JSON-RPC wrapper are outside the hashed object.

To link the execution to the model call, the client presents the proxy's evidence, disclosing the tool name and arguments from one `function_call`. The verifier in the first article required every field to be disclosed. Here the selective presentation is checked against a schema in which selectively disclosable fields are optional; the executor separately requires the tool name and arguments so it can compare them with the request.

The reference is the SHA-256 digest of the exact UTF-8 bytes of the issuer-signed compact JWT, excluding disclosures and key binding, so it stays stable across different presentations. For another evidence format, the profile needs to define which signed bytes to hash. The signature and disclosed claims are verified separately.

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
    "issuer_jwt_sha256": "<sha256-of-signed-jwt>"
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

The values in angle brackets stand for the encoded JWT, disclosures, hash and tool statement. The receiver hashes the signed JWT and compares it with `issuer_jwt_sha256`. Both presentations refer to the same signed JWT, so the additional disclosure does not change that hash. The `_meta` key and the receiver's JSON wrapper illustrate application choices; the code example does not exercise them.

## During the conversation

The example runs the conversation and the later return in one process. A mock proxy uses the first article's code to sign prepared model-call data.

The proxy signs a model response requesting `run_command`. The client discloses that tool's name and arguments to the executor. The executor verifies the evidence, requires one disclosed function call and checks its name and arguments against the request. It runs the handler and signs a statement with the result and a reference to the proxy's signed JWT. In this example, the handler returns a prepared MCP result from `fixtures/tool/`.

The runtime converts the result to the string in the next model-call fixture, which the proxy also signs. The client now has both kinds of evidence.

The executor in [`examples/tool_evidence.py`](../../examples/tool_evidence.py) checks the request and keys its issued statements by the model-evidence digest and `call_id`:

```python
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
        # 1. The model evidence must verify under the proxy's key, for this subject
        #    and response. Only the claims the client disclosed come back.
        claims = verify_selected(model_evidence, self.model_key, subject, response_id, self.model_schema)
        # 2. The client must have disclosed exactly one function call, and the request
        #    must repeat its name and raw argument string byte for byte.
        disclosed = [item for item in claims["response"]
                     if item.get("type") == "function_call" and "name" in item]
        if len(disclosed) != 1:
            raise ValueError("Expected exactly one disclosed function call")
        call = disclosed[0]
        if call["name"] != tool_name or call["arguments"] != raw_arguments:
            raise ValueError("Request differs from the disclosed model call")
        if tool_name not in self.catalog:
            raise ValueError("Unknown tool")
        # 3. Replay rule: one execution per (digest of the signed model JWT, call_id).
        #    The same evidence presented again returns the statement already issued.
        key = (sdjwt.signed_jwt_sha256(model_evidence), call["call_id"])
        if key not in self.executions:
            result = self.handlers[tool_name](json.loads(raw_arguments))
            self.dispatched += 1
            tool = self.catalog[tool_name]
            # 4. The statement covers what the executor received and returned:
            #    the reference to the model evidence, both argument digests and the
            #    digest and length of the full MCP result. The call_id is the model's.
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
```

The example also checks how the executor and client handle incorrect requests and replayed evidence:

- **Changed arguments:** the executor rejects a request whose arguments differ from the model's signed call.
- **Changed tool:** the executor rejects a request naming a different tool.
- **Missing evidence:** the executor rejects the request without model evidence.
- **Unknown key:** the executor rejects model evidence signed by a key it does not accept.
- **Unknown `call_id`:** the client cannot prepare a presentation for a call absent from the signed model response.
- **Replayed evidence:** the same executor receives the evidence twice, runs the handler once and returns the same statement.

The record of issued statements is held in memory and checked within one process. An executor operating across restarts or in parallel must durably store the model-evidence digest and `call_id` and coordinate access. If a failure occurs between execution and recording, the executor may not know whether the operation ran; it must retain that uncertainty rather than execute again.

After the conversation, the client can keep the thread with the model and tool evidence. The example passes the record in memory to simulate its return.

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

The code runs the matching case and 30 rejection and boundary checks: six before the record returns and 24 in the receiving phase. The [results note](notes/executed-checks.md) records the run and its versions. Among the receiving-side cases:

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

## What tool evidence does not establish

Stated as a verifier would state them.

1. A tool statement attests the executor's observation, not the state of the world. A weather service attests the forecast it returned. A payment service attests that it submitted a transaction, or that it received a confirmation, whichever it saw. The record never says what the weather was or whether the money arrived.
2. An executor can sign what it did not do. The signature establishes who made the statement, not that the statement is true. Registering statements with a transparency log makes a false statement durable and attributable; it does not make it impossible.
3. The signed reference records the executor's account of which model request it processed. Matching results show that the covered values agree; they do not trace how identical bytes travelled through the client. The checks do not establish that the thread is complete or that no later call occurred.
4. The absence of a tool statement does not establish that no operation took place. It establishes nothing, and the admission rules treat it as the normal case rather than as a finding.
5. The source class is declared by the executor about itself. A server that declares `observer` while returning generated text is the second limit again, with a different field, and a control plane that keeps its own table of classes by tool identity is entitled to override the declaration.
6. The profile carries one record per call with an `outcome`. It does not separate a decision made before the effect from the outcome observed after it, so it cannot answer "was this allowed" as distinct from "did this run". The Internet-Draft that continued SEP-2828 does separate them; the composition section says how the two fit.
7. A statement carried inside the thread, in MCP's `_meta` or in a runtime's export, depends on every intermediary preserving it. A lost statement is lost evidence, not a verification failure, and the record it would have covered drops to Shown.
8. Replay protection applies within one executor. Another executor that receives the same model evidence can issue its own statement, so the receiving service needs to handle multiple statements for one `call_id`.
9. Selective disclosure hides selected values in the model evidence. The signed JWT still exposes metadata including issuer, subject, response ID, item types and call IDs, which the executor can see when the evidence is presented.

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

**Lineage across agents.** The model closes on itself. An agent's output handed to another agent is, for the receiver, an input artifact of the same kind as a tool result: produced by an executor it did not run. The first agent's operator can issue a statement of the same shape as tool evidence, its result the handoff artifact, its class `generator`, with references by digest to the statements it consumed, the weather tool's statement, its own model statements. In in-toto terms these are `materials` and `subject`; in PROV terms, `used` and `wasGeneratedBy`; the alternating chain of one thread is the special case with one issuer of each kind. The receiving agent applies the four statuses twice. To continue the first agent's text it needs only the first agent's statement. To act on the weather it follows the references to the weather tool's statement and verifies that itself, under its own issuer configuration, independent of the first agent's word. One invariant makes this safe and its absence makes it laundering: references do not raise the class. A statement that cites an observer's statement is still a generator's statement. An action that needs an observation needs a path to an observer-class leaf from an accepted issuer with passing link checks; generator nodes along the path may transform, they may not originate. Repackaging a record is not corroboration. Specifying this across several issuers is open work; the article names it and leaves it.

### Run the examples

The example implementation, fixtures, schemas and the check script that keeps the code and this text in agreement are in the [companion repository](../../README.md) alongside the earlier article's examples. The [executed-checks note](notes/executed-checks.md) records the results and limits. The profile has been checked on fixtures and remains a proposal for use with a real runtime.
