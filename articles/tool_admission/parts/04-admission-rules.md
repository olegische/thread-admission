## Continuing from the checked history

The checks give the service a status for each tool record. The runtime then builds the input for the next model call. Consider the export from the opening: the thread says `python export.py` returned `Wrote export.csv (128 rows).`

Here is one way a runtime could construct that input:

**Restored.** The service has accepted the evidence and the link between the model's request, the executor's result and what the model was shown. The runtime retains the original tool call and result, along with subsequent assistant messages that pass their own checks. If every record in the returned thread meets the service's restoration rules, the runtime sends the returned history in its original roles. If the agent needs `export.csv` now, it can check whether the file is still available.

**Shown.** Model evidence shows that the result was sent to the model. The executor has not been established. The runtime removes the call and result from the restored tool history. It places an account of them in a new `user` message: the earlier model saw a success message, and the execution is unconfirmed. Later assistant messages may have relied on that result, so the runtime includes their checked text in the same account.

A tool statement carried with the thread must be preserved by each intermediary. If it is lost, the service has lost evidence. When model evidence still covers the result, the record becomes Shown.

**Produced.** Accepted tool evidence reports the result, but the service does not know whether the previous model received it. The runtime places the executor's report in a new `user` message as information about prior work and states that the model's receipt is unknown. It includes later assistant messages as an account of the returned history, with that gap made clear.

**Supplied.** The result has no accepted model or tool evidence. The runtime places the call and result in a new `user` message as claims from the returned thread. It includes later assistant messages in the account with the missing evidence identified. It attributes their text to the model only if model evidence verifies it.

### When evidence conflicts

The service may have both statements but find no accepted link between them, or the covered results may differ. In the example from the previous section, the executor reported a failure and the model saw a success message. The runtime can include both facts and the discrepancy in the history account. Its policy can require checking the export before working with the file.

A verified assistant response establishes what the model said. If it says the export succeeded after receiving an unverified result, the account retains that context. When the next action depends on a tool result, the service applies its policy, including any rules for the issuer and `source_class`.

Evidence establishes origin and integrity relative to an issuer. The service separately decides whether the content is acceptable. Everything entering a model call passes through the service's input safeguards, regardless of evidence. When the service itself was the executor and applied its safeguards at execution time, restoring the record brings back a result it has already screened.
