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
