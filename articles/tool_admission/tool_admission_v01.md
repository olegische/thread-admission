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
arguments:    hash of {"cmd":"python export.py","workdir":"/workspace"}
outcome:      executed
source class: computation
result:       hash of "Wrote export.csv (128 rows).\n"
```

The executor signs these claims and makes the statement available with the thread. In this example it declares that the output was computed; the receiving service decides whether to accept that claim. The [experiment](parts/06-experiment.md#tool-statement-for-the-experiment) specifies the full profile and its schema.

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

The service also compares the arguments requested by the model with those received by the executor. The issuers do not need to know about each other's statements: the service verifies each in its own format and compares the values they cover.

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

Results also need a shared representation. If the executor hashes the result string sent to the model, the service can compare it with the string covered by model evidence. If the runtime transforms or truncates the result, the comparison needs to account for that transformation. We return to truncation in the admission rules.

### Identifying the execution

The service can use `call_id` to find statements to compare. Matching arguments and results show that the covered values agree. To establish that the statements concern the same execution, the service also needs a binding it accepts between the model's request and that execution. Two separate calls can have the same ID, arguments and result, and a runtime can relay an ID. Our hashes alone do not establish that binding. How to establish it remains open for this profile.

The next section uses these checks to decide what the service can retain as history and how it can use the result.

## Admission rules for tool records

The service uses the evidence and comparison results to decide what a returned record establishes. We use four statuses:

- **Restored:** accepted model and tool evidence cover the call; the arguments and results agree, and the service has an accepted binding to the same execution. The record is restored as prior history.
- **Produced:** accepted tool evidence covers the result. The executor reports producing it; whether the model received it is unknown.
- **Shown:** model evidence covers the result sent to the model. The service can retain it as a result the model was shown.
- **Supplied:** neither kind of evidence establishes the result. The service retains it as supplied context.

These statuses describe what the service can establish from accepted evidence. In our proposed profile, matching values and a relayed `call_id` do not by themselves provide the execution binding needed for Restored. If both statements are available but that binding is missing, the service can retain the supported facts about what was Produced and what was Shown; it cannot conclude that they describe the same execution. How independent issuers can provide such a binding remains an open question for this profile.

If the covered arguments or results differ, the service records the mismatch and does not restore the linked record. In the export example, it can retain both the executor's reported failure and the success message shown to the model, along with the discrepancy. A valid signature on each does not make their contents agree.

### Using the result

Restoring a record lets the service continue from a history of the call. It does not run the command again or renew an earlier approval. The current environment decides what the agent may do next.

The service also considers how the executor obtained the result. For example, a tool backed by a model may sign a prediction and declare `source_class: generator`. Even if the record is Restored, a policy requiring an observed test result before deployment would not use that prediction as its basis. The service applies the class under its rules for the issuer, and may instead use a class it has configured for the tool.

A result that was Shown remains Shown when it appears in later model calls; repetition adds no evidence about who produced it. A tool statement with `outcome: refused` or `errored` records what the executor reported. Neither outcome alone establishes that no side effect occurred. If no tool statement is available, the service has no executor's account of what happened.

### Truncated output

A runtime may show the model only part of a long result. In our proposed rule, the tool statement covers the full result. If the service can obtain the full result, verify it against the statement and match the portion shown to the model under a known truncation convention, it records the comparison as `truncated`. If that comparison or the execution binding is unavailable, it retains only the facts supported by the evidence. If the compared content differs, it records a mismatch.

### A call without a result

The thread may contain a model's tool call without a corresponding result. Model evidence can establish that the model issued the call. The service keeps that fact and does not infer whether the tool ran. If the runtime needs an output item to continue, it can insert one as supplied content.

## Granularity belongs to the issuer

A model statement discloses message text, function names, arguments and tool outputs as units. A tool statement discloses a result, and a result is not one thing. A mail tool returns a message with a sender, a subject, a body and attachments. A payment tool returns an identifier, an amount, a fee and a status. Who decides what can be disclosed independently?

The executor does. It knows its domain; the profile does not. A mail server may issue the body as one disclosure or each paragraph as its own. A payment server may issue amount, fee and recipient separately so that a fee dispute can see the fee without the recipient. The profile fixes only how the subdivision is named: `result.sha256` and `result.length` commit to the whole, and `result.parts` carries the executor's own named disclosures, each a selectively disclosable claim, opaque to the profile and described by a schema the executor publishes under its `tool_id`.

The reason to do this with selective disclosure rather than a signed blob is that one result has several readers with different entitlements.

| Reader | What it needs from the record |
|---|---|
| The service continuing the task | the content the task needs |
| An auditor | who called, which operation, when, with what outcome |
| Another party in the process | one confirmed value: an amount, a status, an identifier |
| A fee review | the fee and the parameters it was computed from |

Sending the auditor the whole email to establish that a call was made is over-disclosure. A signature over the whole object forces a choice between disclosing everything and designing verifiable parts by hand. SD-JWT gives the parts ready-made, with their own salts, held by the client and presented on request. The earlier article's open question, whether verifiers really need different parts or whether whole-record signing would do, has its first concrete case here, and the experiment section tests it rather than assuming it.

What the executor can attest also depends on what it observes. For a payment, accepting the request, submitting the transaction and receiving its confirmation are three observations at three times, and an executor that only saw the first should issue a statement that says so. The executor signs what it saw. The profile's `outcome` field is deliberately coarse for this reason: `executed` means the executor's own operation completed, not that the world changed as intended.

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

## What tool evidence does not establish

Stated as a verifier would state them.

1. A tool statement attests the executor's observation, not the state of the world. A weather service attests the forecast it returned. A payment service attests that it submitted a transaction, or that it received a confirmation, whichever it saw. The record never says what the weather was or whether the money arrived.
2. An executor can sign what it did not do. The signature establishes who made the statement, not that the statement is true. Registering statements with a transparency log makes a false statement durable and attributable; it does not make it impossible.
3. Matching arguments and results show that the covered values agree. They do not by themselves establish that the statements describe the same execution, that the thread is complete, or that no later call occurred.
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

**Inference admission is the base.** The earlier article's model-call evidence and this article's tool-call evidence are issued independently. A receiving service verifies each in its own format and compares the covered data where it can. The model-evidence profile from the earlier article does not need to move to the tool statement's `vct` type.

**Existing records can contribute evidence.** SEP-2787 describes a request attestation; SEP-2828 and its successor describe decisions and outcomes. Other proposals use in-toto statements for agent audit records. A receiving service can verify a supported format and use the claims it actually covers. Whether those claims identify an executor, a call, its arguments, result or source class depends on the record and issuer; missing claims cannot be assumed.

**Where standing meets authority.** Admission produces typed records and stops. What a control plane does with `source_class` is its policy: which actions may be grounded on a generated result, which tools of which class may be called in which context, whether its own table of classes overrides an executor's declaration. This article gives one illustration of such a policy, the rejection of a generator's output as grounds for an action that needs an observation, and marks it as the control plane's rule, not admission's. The authority layer, mandates, allow-lists, gates, is a separate specification. This is the one point where the two layers touch, and the article keeps it to one point.

**Two records in time.** The decision-before-effect and outcome-after-effect split of SEP-2828 and the Verification Summary Attestation answers a question this profile does not ask, whether an operation was allowed. Admitting a thread that carries both records, with the outcome pinning the decision's digest, is the next piece of work.

**Lineage across agents.** The model closes on itself. An agent's output handed to another agent is, for the receiver, an input artifact of the same kind as a tool result: produced by an executor it did not run. The first agent's operator can issue a statement of the same shape as tool evidence, its result the handoff artifact, its class `generator`, with references by digest to the statements it consumed, the weather tool's statement, its own model statements. In in-toto terms these are `materials` and `subject`; in PROV terms, `used` and `wasGeneratedBy`; the alternating chain of one thread is the special case with one issuer of each kind. The receiving agent applies the four-row table twice. To continue the first agent's text it needs only the first agent's statement. To act on the weather it follows the references to the weather tool's statement and verifies that itself, under its own issuer configuration, independent of the first agent's word. One invariant makes this safe and its absence makes it laundering: references do not raise the class. A statement that cites an observer's statement is still a generator's statement. An action that needs an observation needs a path to an observer-class leaf from an accepted issuer with passing link checks; generator nodes along the path may transform, they may not originate. Repackaging a record is not corroboration. Specifying this across several issuers is open work; the article names it and leaves it.

### Run the examples

The reference implementation, fixtures, schemas, Type Metadata documents and the check script that keeps the code and this text in agreement are being added to the [companion repository](../../README.md) alongside the earlier article's examples. Until the experiment section reports results, treat the profile as proposed and the rules as the author's claims.
