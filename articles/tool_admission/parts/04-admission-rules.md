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
