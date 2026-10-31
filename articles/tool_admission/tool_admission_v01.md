# Tool Admission: What a Service May Believe About a Tool Record It Did Not Witness

*This article is about the receiving side: what a service may restore from a tool record in a returned thread, and what it does when no evidence came with it.*

Suppose you are building a service for an AI assistant that lets users resume work from a saved conversation. A user may have continued that conversation in a local agent before returning it to your service. Alongside messages, the history contains tool calls and their results. Which of those results can your assistant rely on when continuing the task?

The [earlier article](../thread_admission/context_admission.md) used evidence issued by a proxy that observed model calls: the service can check that the returned content matches what the proxy received as input or delivered as output. For tool results, this leaves a gap. Evidence that a model received the text `Tests passed` does not establish that the tests produced it. A runtime or user could have changed the result before it reached the model, and the proxy would have witnessed the changed text.

This problem surfaced in the [MCP discussion on audit context for tool calls](https://github.com/modelcontextprotocol/modelcontextprotocol/pull/2817#issuecomment-5390870362). An implementer reported that a consumer had treated an outcome reported by the host in the same way as an outcome observed by the runtime. The distinction between how the records were obtained was lost when they were used.

The MCP proposals identify two separate things a service might receive: a [signed statement of what was requested](https://github.com/modelcontextprotocol/modelcontextprotocol/pull/2787) and a [record of what the executing side decided and returned](https://github.com/modelcontextprotocol/modelcontextprotocol/pull/2828).

A receiving service needs to establish who attests to the result, which call it belongs to, and whether it matches the result the model received. When evidence is missing, the service still needs a rule for retaining and using the record.

That decision is tool admission. The executor is the party that processed the tool call and returned the result. We will define its statement, the checks that link it to model evidence, and admission rules for records with different evidence coverage. These rules state what the service may accept as established. Its policy decides whether that is sufficient for the next action.

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

## The receiving side

All three layers live at the moment of the call, between a client and a server. Move the clock forward. The thread has been exported to the user's storage, continued on a laptop, perhaps converted from one runtime's format to another's, and now it comes back to a service that kept no copy. In it is a record like this one, shortened from the Codex App Server format used in the earlier article:

```json
{
  "type": "commandExecution",
  "id": "exec-1",
  "command": "python export.py",
  "cwd": "/workspace",
  "status": "completed",
  "aggregatedOutput": "Wrote export.csv (128 rows).\n",
  "exitCode": 0
}
```

This is text. The earlier article showed what evidence from the inference proxy can establish about it: the proxy signed the full input of the model call that followed, so a verifier can confirm that a tool result with this exit code and this output was in front of the model when it produced its answer. That is a real fact and it is worth having. It is not the fact the record claims. The record claims that a command ran and exited with zero. The proxy's evidence establishes that a string saying so was shown to the model. A result rewritten before it reached the model passes the proxy's check untouched.

That is the bug from SEP-2817 in one sentence. Merging the host's report of an outcome with the runtime's witnessed outcome is exactly treating a tool record as established because model evidence covers it. The channel conferred the status. Nothing in the record earned it.

### Why absence is the normal case

The threads concluded that the party that executed the operation must sign the record of it. The conclusion is logically right and economically empty. The executor pays; the consumer benefits. There is no reason for a weather API, a ticketing system or a payment backend to grow a signing endpoint so that someone else's agent service can later decide what to believe about a thread.

This is not a new situation. Every time a verifying technology has asked established systems to attest to what they did, the same five mechanisms decided whether it happened.

- A consumer with market power set a condition. Mail servers ignored DKIM for a decade; they adopted it when Gmail and Yahoo began rejecting unsigned bulk mail. Certificate authorities logged nothing until Chrome required Certificate Transparency proofs.
- A regulator compelled it. Open Banking under PSD2 forced banks to expose signed, consented APIs they had no commercial interest in.
- The cost of issuing dropped to zero because a layer the system already used did it. Sites did not become HTTPS-ready; Let's Encrypt and the load balancer did. Package authors do not write provenance; the CI platform emits SLSA provenance for every build.
- A witness stood in the path when the executor would not attest. Notaries, clearing houses, timestamp authorities and payment networks certify what they saw pass through them, which is weaker than what the executor did internally and available today.
- The executor gained from it. Signed webhooks from payment and code-hosting providers reduce the provider's own dispute load.

Where none of the five applied, the attestation did not spread. Message disposition notifications for email exist in a standard and are almost never honoured. HTTP message signatures are used where one consumer demands them and nowhere else.

Three consequences follow for a receiving service.

First, the admission rules must be written for a world in which most tool records carry no executor evidence and never will. A record without it is not an error; it is the baseline. It remains the user's account of what happened, it is retained, and the continuation proceeds with it at that standing. What changes is not whether the record is kept but what the control plane may do on its strength: before an action that depends on it, the control plane must require a fresh observation rather than treat the account as one.

Second, admission is itself the first mechanism. A published rule that records with executor evidence are restored as prior history and records without it are retained as supplied context is a condition set by the consumer. An executor whose results matter in continued threads has a reason to sign that it did not have before. The service does not ask backends to become AI-ready. It states what it admits and leaves the choice to them.

Third, for executors that do choose to sign, the cost should be the third mechanism's zero. The record should be emitted by the tool runtime at the point where the handler runs, not by the handler's author. The experiment in this article is built that way.

## Two kinds of evidence

The earlier article defined one kind of evidence: a statement by the inference proxy about one completed model call, covering the ordered input the model received and the output it produced. Call it model evidence. Tool admission needs a second kind with a different issuer and a different coverage.

| | Model evidence | Tool evidence |
|---|---|---|
| Issuer | the inference proxy | the executor: an MCP server, a host-side tool handler, the owner of the domain |
| What it attests | this input was presented, this output was returned, for this `response_id` | this request was received, this operation ran, this result was returned |
| The tool result in it | an input item with the tool role: "the model was shown this" | the subject of the statement: "the tool produced this" |
| What it does not attest | that the result is genuine | that the model ever saw it |
| Binding | `call_id`, position in the input | `call_id`, digest of the arguments, digest of the result |
| Format | SD-JWT, the earlier article's profile | SD-JWT on the same scheme; DSSE where no selective disclosure is needed |

### The issuer is whoever executed

SEP-2828 argued that the server, not the client, must sign the execution record because the client does not own the logic that decided or the result that came back. Taken to the receiving side, the argument fixes the issuer of tool evidence: the party that executed is the only one that knows what executed. A transport carries the statement. It does not produce it.

Consider a composite MCP server that offers one tool and fulfils it by calling three backends of its own. The server signs what it observed: it received these arguments and returned this result. The backends sign nothing and are under no obligation to. If the server wishes, it may include digests of the backends' responses inside its own statement as references; nobody requires it. The server's statement establishes that the server returned this, not that any backend did anything. For the receiving service that is enough to assign standing at the level "a result of tool X", where X is this server and nothing behind it.

### The source class, and who reads it

A tool's statement carries a claim the executor makes about itself: `source_class`, one of `observer`, `computation` or `generator`. It says how the result was obtained: read from something outside the executor, computed by a procedure the executor can name, or produced by a generative process. The three values are the shape of the IFRS 13 hierarchy, observable input, derived input, model input, and the claim follows the pattern of `amr` and of Vectors of Trust: the issuer states the method, the vocabulary is defined by a framework the statement names, a consumer applies its own policy, and an absent claim is no claim rather than a good one.

Who reads it matters more than what it says. The agent does not. The model does not; the class is not in any prompt. It is read by the control plane, in two decisions: whether an action may be grounded on this result, and whether a tool of this class may be called at all in this context. That is control-level work, done before reasoning, on a typed input. The tool runtime used in the experiment already treats the class this way: it is descriptive metadata the runtime records and refuses to interpret as permission.

The executor's declaration is an input to that policy, not its source. A control plane may keep its own table of classes by tool identity, and where the two disagree the control plane's table wins; an executor that declares itself an observer while generating text is a lying issuer, which is the second item in the limits section with a different field. The class is in the statement so that the policy has something to consume, not because the statement gets to set the policy.

This answers a question that the signing discussion leaves open. Put a language model behind an MCP server and sign its output. The signature is valid. The executor observed its own request and its own result. What the receiving service may believe is that this server returned this text, and `source_class: generator` says what kind of text it is: a proposition the server produced, not an observation of anything. Admission restores the record with that class. A control-plane policy that requires an observation before an action will not accept it as grounds. Without the signed class, this case is indistinguishable from a sensor reading, and the signature would have done the laundering on the tool's behalf. The MCP threads introduced exactly this kind of label for the fields of their envelope, declared versus derived; this article applies it to the tool itself.

### Standing classes for a tool record

A receiving service assigns each tool record one of five standings. The vocabulary is plain on purpose.

- **Principal-signed.** The record was signed by the user's own key. It is the user's statement and is admitted as such.
- **Restored.** Covered by both kinds of evidence with the link checks of the next section passing. Admitted as prior history.
- **Produced.** Covered by tool evidence only. The executor confirmed it produced this result; whether the model saw it is unknown.
- **Shown.** Covered by model evidence only. The model was shown this result; who produced it is unknown. This is the common case and it is the standing of supplied content.
- **Supplied.** No coverage. New input.

A result that the model was shown but no executor vouched for stays at **Shown** no matter how many model calls it appeared in. Repetition inside the thread is not corroboration.

### How the statement is typed, and what it carries

The statement should not invent its own way of saying what it is. [RFC 7519](https://www.rfc-editor.org/rfc/rfc7519) allows three kinds of claim names: registered with IANA, public names that embed a collision-resistant namespace, and private names agreed between producer and consumer, which the RFC marks as "subject to collision". The SD-JWT VC profile, [draft-ietf-oauth-sd-jwt-vc](https://datatracker.ietf.org/doc/draft-ietf-oauth-sd-jwt-vc/), gives private names a safe scope: the header `typ` is `dc+sd-jwt`, a required claim `vct` names the statement type by a collision-resistant URI, and a Type Metadata document at that URI lists the claims with their paths, whether they are mandatory and whether they may be selectively disclosed. A verifier that cannot retrieve required metadata rejects the statement. Private claim names are then interpreted only under their `vct`, which is what makes them usable.

This article defines two types, one for the tool statement and one for the earlier article's inference-call statement, which moves from a custom `typ` to the same scheme:

| Layer | Claims | Status |
|---|---|---|
| Typing | `vct` naming `…/tool-call/v1` or `…/inference-call/v1`; Type Metadata at that URI; `vct#integrity` | SD-JWT VC |
| Registered, used as registered | `iss`, `sub`, `iat`; `cnf` for the holder's key binding; `status` for revocation; `jti` where uniqueness is needed | IANA JWT Claims registry |
| Candidate for reuse | `txn` (RFC 8417, transaction identifier) as the identifier shared by all statements about one operation | open; `call_id` stays separate as the model's relayed identifier |
| Private under `vct` | `source_class`, `tool_id`, `call_id`, `outcome`, `arguments`, `result`; for inference-call, `response_id`, `request`, `response` | not registered by anyone as of this writing; registration deferred |
| Not borrowed | `amr`, `acr`, `vot`, `vtm`, `events`, `attest` | registered with other meanings |

The open, signed claims of a tool statement: `iss` (the executor), `sub` (the account on whose behalf it ran), `iat`, `call_id`, `tool_id` (a stable identity such as `namespace.name@version`), `source_class`, `tool_kind` (`read`, `write`, `think` or `generic`), and `outcome`, one of `executed`, `refused` or `errored`. The selectively disclosable claims: the arguments as two digests (next section), and the result, at a granularity the executor chooses (section on granularity). The vocabulary of `source_class` is fixed by the JSON Schema the Type Metadata points to; a verifier rejects a value it does not know.

The schema below describes the claims after disclosure. It is a proposed profile; its reference implementation is the subject of the experiment section and is not yet published.

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

`result` is absent when `outcome` is `refused` or `errored` without a body; `parts` holds the executor's own disclosable subdivision of the result and is opaque to the profile. `cnf` and `status` are omitted from the schema because they belong to the holder and to revocation, which are not this article's subject; the profile uses them as registered.

## A flat chain

With two kinds of evidence, a session is an alternation:

```text
tool evidence   (result R1 was produced)
  → model evidence (R1 was shown; function call F2 was issued)
  → tool evidence  (F2 was executed; result R2 was produced)
  → model evidence (R2 was shown; the answer was issued)
```

Each link covers its own half. The links are checked against their neighbours, not against a plan above them. Two checks connect a tool statement to the model statements on either side of it:

- the digest of the result in the tool statement equals the digest of the tool-role item in the input of the next model call;
- the arguments in the function call issued by the previous model call equal the arguments in the tool statement.

Without one of the two kinds, the chain is a set of unrelated signatures. With both, each link vouches for the other's edge. There is no envelope over the plan, no issuer above the planner, and no notary. The MCP threads needed a three-block envelope because in their design one issuer signs other parties' claims; when every party signs only what it observed, the blocks collapse.

### Observed and relayed

One distinction between fields survives the collapse. A statement carries what its signer observed, and it may carry identifiers it received from elsewhere: the `call_id` that the model assigned to the function call, a turn identifier from the runtime. Those are relayed, and a verifier treats a join on a relayed identifier as weak. A join on digests of arguments and results is strong. This is the same difference as between a trace header, which anyone can set, and a signed transaction token, which only its issuer could have made.

### Two digests of the arguments

The model emits `arguments` as a string. The executor receives an object. A tool statement therefore carries two digests: one of the raw string as the executor received it, one of the JCS canonical form of the parsed object. The first is the digest compared with model evidence. The second is the digest of what the executor actually used. For the example call,

```text
arguments as emitted:   {"cmd":"python export.py","workdir":"/workspace"}
raw_sha256:   f272be5ff717e09cbabf10f946c667892bd94b0f5bbe36cac5e491de0eea642f
jcs_sha256:   f272be5ff717e09cbabf10f946c667892bd94b0f5bbe36cac5e491de0eea642f
```

The two coincide because the model happened to emit canonical JSON. Insert one space after each colon and the raw digest becomes `a03adda5…`, while the JCS digest is unchanged. A verifier that compared only canonical forms would miss a runtime that rewrote the string; one that compared only raw strings would fail on an executor that re-serialized. Both digests, both comparisons. This is the problem SEP-2787 addressed with a three-way argument projection and in-toto addresses with a resource descriptor that carries a digest and, optionally, content. The rule here is the smallest one that works: the raw digest is the link, the canonical digest is the executor's commitment to what it ran.

In Python, with `rfc8785` for canonicalization:

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
    """Compare one tool statement with its neighbouring model statements."""
    call = next(item for item in previous_model["response"]
                if item["type"] == "function_call" and item["call_id"] == tool["call_id"])
    shown = next(item for item in next_model["request"]
                 if item["type"] == "function_call_output" and item["call_id"] == tool["call_id"])
    return {
        "arguments": sha256(call["arguments"].encode("utf-8")).hexdigest()
                     == tool["arguments"]["raw_sha256"],
        "result": sha256(shown["output"].encode("utf-8")).hexdigest()
                  == tool["result"]["sha256"],
    }
```

`previous_model` and `next_model` are the verified claim sets of the earlier article's profile; `tool` is the verified claim set of the schema above. The function returns two booleans and makes no decision; admission does that.

### Who links the links

The association between a call and its position in a thread lives in the runtime and is protected by nothing. The holder of the thread, the user's storage or the service that saves it, fixes the order when it saves. Issuers sign only their own link. This keeps the executor out of any obligation to know about threads, which it does not and should not.

### A rule for issuers, not for verifiers

The SEP-2817 discussion insisted that bound values be recomputed immediately before execution, because every field can be bound correctly while the record describes an action that never happened. That is a rule for the executor: the digests in a tool statement must be of the arguments it actually passed to its handler and the result the handler actually returned, computed at that moment. It is complete mediation restated for tool calls. The receiving service cannot enforce it and does not try; it relies on the executor's signature meaning what the executor says it means, which is the first limit in the limits section.

## Admission rules for tool records

A receiving service classifies each tool record by which evidence covers it and whether the link checks pass. Four cases cover the space.

| Model evidence | Tool evidence | What the service may hold | Admission |
|---|---|---|---|
| present, link passes | present, link passes | the executor produced this result and the model was shown it | **Restored** as prior history |
| present | absent | the model was shown this result; who produced it is unknown | **Shown**: supplied content, retained as the user's account. The normal case |
| absent | present | the executor produced this result; whether the model was shown it, or was shown something else, is unknown | **Produced**: the result stands, its role in the thread does not |
| absent | absent | nothing | **Supplied**: new input |

Two rules sit on top of the table. Import does not activate: a restored record of a command that ran does not run it again, and a restored approval does not approve anything now; the current environment decides what the agent may do next. And a record's standing never rises through repetition: a Shown result that appears in ten model calls is Shown.

### Counterexample one: the exit code

On August 24, 2026, XuebinMa [reported a verifier bug](https://github.com/modelcontextprotocol/modelcontextprotocol/pull/2817#issuecomment-5390870362): "a host-asserted `exit_code: 0` and a runtime-witnessed execution landed in the same total". The fix separated `ExecutionFinished` from `ExecutionReported`. The counterexample below applies that distinction to a returned thread whose tool result was changed.

The user's command failed. The runtime, or the user, rewrote the result before the model saw it. The model was shown a success and answered accordingly. The thread comes back with model evidence intact.

What the executor produced:

```text
Chunk ID: abc123
Wall time: 0.1000 seconds
Process exited with code 1
Output:
Traceback (most recent call last):
  File "export.py", line 12, in <module>
    rows = fetch()
ConnectionError: database unavailable
```

What the model was shown:

```text
Chunk ID: abc123
Wall time: 0.1000 seconds
Process exited with code 0
Output:
Wrote export.csv (128 rows).
```

The model statement's disclosed `output` for `call-1` hashes to `6b3f9753…`. Model evidence verifies: the proxy did see this string in the input, and it signed it. Without tool evidence the record is Shown, which is the correct standing: the service holds that the model was told the command succeeded, and nothing more.

With tool evidence the picture changes. The executor's statement carries `result.sha256` of `5501f22c…` for the failing output. The second link check compares `6b3f9753…` with `5501f22c…` and returns false. Both signatures are valid. Both statements are honest. The record is not Restored, because the two honest statements are about different results, and the service now knows that what the model was shown is not what the tool produced. The comparison detects the mismatch even though both signatures verify.

### Counterexample two: the model behind the server

A tool is an MCP server wrapping a language model. The model call it serves is itself attested by a proxy; the server signs its result; the receiving service's model evidence shows the result was presented. Every signature verifies, every link check passes, and the first row of the table is reached.

Two different actors now make two different decisions. Admission restores the record, with `source_class: generator` attached: the service holds that this server produced this text and that the model saw it. The control plane then applies its policy to the class. A policy that requires an observation before an action, a balance, a file's contents, a sensor's value, rejects this record as grounds, however many signatures it carries. The record stays in the history; it does not license the action. Admission did its job by typing the record; the policy did its job by reading the type. Neither inspects the text, because a custodian can put any text in any record. Without a signed class the two decisions collapse into one, the server's output and a database query's output are the same object with the same signatures, and the signatures have laundered a hypothesis into an observation.

### Two meanings of "unaccounted"

The SEP-2817 discussion found that a verifier status of `unaccounted` meant either "we established that nothing ran" or "the evidence stops here". Admission separates them by what it has in hand. A tool statement with `outcome` of `refused` or `errored` is positive evidence that the executor declined or failed: the executor said so, the service holds it, and a thread that claims the operation succeeded contradicts a signed statement. The refusal is not inert; a consumer reads it. The absence of any tool statement is the second meaning: the thread's account is retained as Shown or Supplied and nothing is established either way. A service that reports "no execution" when it means "no evidence" has made the merged-outcome error in the other direction.

### Honest truncation

Runtimes truncate long tool outputs before showing them to the model. The executor produced ten thousand lines; the model saw the first two hundred and a marker. The second link check, as written, fails. That would turn every long output into a mismatch.

The rule adopted here: the tool statement's `result` carries the digest and the byte length of the full result. If the shown output is shorter than that length and the digest of the full result cannot be compared directly, the verifier compares the shown output with the disclosed result's prefix of the same length and records the link as `truncated` rather than `mismatch` when the prefix matches. A record linked as `truncated` is Restored with that annotation. A shown output that is not a prefix of the produced result is a mismatch regardless of length. This makes the truncation convention explicit instead of leaving it to the runtime, and it depends on the executor disclosing the full result or enough of it, which the granularity section returns to.

### What a `function_call` without a result gets

A function call item with no corresponding output item in the thread is a call that was issued and, as far as the thread shows, never answered. It is covered by model evidence as a model output and is Restored as that: the model issued this call. It is not evidence that anything ran. Admission neither synthesizes an output for it nor treats its absence as a refusal; a runtime that needs an output in place for its own normalization inserts one as supplied content.

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

The issuer of tool evidence sits where the tool runs. The reference implementation uses a small open-source tool runtime whose single dispatch point validates arguments against a JSON Schema, calls the host's handler, and normalizes the result into a deterministic envelope. At that point the runtime assembles a call record: `call_id`, the two argument digests, the complete result envelope including failures, `tool_id`, the tool's declared `source_class` and `tool_kind`. A separate package signs the record as an SD-JWT under the `tool-call/v1` type with the executor's key. The handler's author writes nothing for this to happen; that is the zero-cost pattern from the receiving-side section, applied.

The issuer of model evidence is the earlier article's proxy example, unchanged except for the move to `vct` typing. The verifier and the admission rules live in the earlier article's repository, independent of both issuers, and import its model-evidence verifier rather than copying it.

The environment is a simulated tool-use benchmark with domain state held in a database file: hidden state, a real executor, an independent verifier beside it. The example thread of both articles is one of its fixtures.

### Negative cases

Each case fixes its expected outcome before it is run.

| Case | Expected |
|---|---|
| Result rewritten from exit 1 to exit 0 before the model saw it; model evidence intact | model link passes; tool link fails; record not Restored |
| Arguments in the issued function call differ from the arguments in the tool statement | argument link fails |
| Tool statement from a different `call_id` presented for this record | no link; record stays Shown |
| Shown output is a prefix of the produced result | link recorded as `truncated`; Restored with annotation |
| Shown output differs from the produced result and is not a prefix | mismatch |
| Tool statement from a different issuer under the same `call_id` and digests | verifies as a second statement; admission requires the issuer's `tool_id` to match the call's tool |
| Record with no tool statement in a thread whose message chain verifies | Shown; message matches unaffected |
| Model behind a server, class `generator`, all signatures valid | Restored as record; control-plane policy requiring an observation rejects it as grounds |
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
3. Two links that agree establish that these two statements are about the same result. They do not establish that the thread is complete, that no call is missing between them, or that the last link is the last call that happened.
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

**Inference admission is the base.** The earlier article's statement about one model call is the first kind of link; this article's statement about one tool call is the second; the alternation is the chain. The model-evidence profile does not change beyond the move to `vct` typing. A service that already verifies returned threads against proxy evidence adds a second verifier and the four-row table and gains tool admission without touching what it had.

**The MCP proposals are candidate issuers.** SEP-2787, SEP-2828 and the Internet-Draft that continues it are formats for the statement that this article consumes. So is any in-toto predicate for a tool call, and so is draft-gilda-wimse-agent-audit-record for the decision side. Admission does not depend on which of them is adopted. It depends on three properties that all of them can carry: the issuer is the executor, the statement is bound to the call by `call_id` and by digests of arguments and result, and the tool's source class is declared. A statement with those properties, in any of those envelopes, passes through the four-row table unchanged. That is an invitation, not a competing format: the receiving side was the piece those proposals said was missing, and it is agnostic about the rest.

**Where standing meets authority.** Admission produces typed records and stops. What a control plane does with `source_class` is its policy: which actions may be grounded on a generated result, which tools of which class may be called in which context, whether its own table of classes overrides an executor's declaration. This article gives one illustration of such a policy, the rejection of a generator's output as grounds for an action that needs an observation, and marks it as the control plane's rule, not admission's. The authority layer, mandates, allow-lists, gates, is a separate specification. This is the one point where the two layers touch, and the article keeps it to one point.

**Two records in time.** The decision-before-effect and outcome-after-effect split of SEP-2828 and the Verification Summary Attestation answers a question this profile does not ask, whether an operation was allowed. Admitting a thread that carries both records, with the outcome pinning the decision's digest, is the next piece of work.

**Lineage across agents.** The model closes on itself. An agent's output handed to another agent is, for the receiver, an input artifact of the same kind as a tool result: produced by an executor it did not run. The first agent's operator can issue a statement of the same shape as tool evidence, its result the handoff artifact, its class `generator`, with references by digest to the statements it consumed, the weather tool's statement, its own model statements. In in-toto terms these are `materials` and `subject`; in PROV terms, `used` and `wasGeneratedBy`; the alternating chain of one thread is the special case with one issuer of each kind. The receiving agent applies the four-row table twice. To continue the first agent's text it needs only the first agent's statement. To act on the weather it follows the references to the weather tool's statement and verifies that itself, under its own issuer configuration, independent of the first agent's word. One invariant makes this safe and its absence makes it laundering: references do not raise the class. A statement that cites an observer's statement is still a generator's statement. An action that needs an observation needs a path to an observer-class leaf from an accepted issuer with passing link checks; generator nodes along the path may transform, they may not originate. Repackaging a record is not corroboration. Specifying this across several issuers is open work; the article names it and leaves it.

### Run the examples

The reference implementation, fixtures, schemas, Type Metadata documents and the check script that keeps the code and this text in agreement are being added to the [companion repository](../../README.md) alongside the earlier article's examples. Until the experiment section reports results, treat the profile as proposed and the rules as the author's claims.
