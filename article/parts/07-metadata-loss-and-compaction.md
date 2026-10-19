## Separate the thread from the model context

The previous examples assumed that the runtime retained API items in a comparable representation. Codex App Server exposes a different transcript. That difference reveals a distinction we also need when the formats agree: the runtime's thread and the input of a model call are separate objects.

### Name the objects before connecting them

Here, a **thread** is the conversation and execution history managed by an agent runtime. The runtime assigns its identity, groups work into turns, records messages and tool activity, and decides where to continue. Its **transcript** is a serialized view of that history, such as the App Server items in section 1. It need not contain every detail of the runtime's state.

The **model context** is what the runtime supplies for a particular inference request. In our client-managed example, we verify the request's ordered `input` items. Other request fields need their own coverage if they matter to the intended claim. The **response output** contains the items returned by that model call and is separate from its input.

The runtime builds a model request from its thread. It then incorporates the response into its history and may execute tools before making another request. An inference proxy observes those requests and responses; it does not thereby learn the runtime's thread identity.

Two threads can send identical input. One thread can send different input after compaction or context selection. An ordered array of API items therefore does not identify a thread, even when the runtime stores exactly those items. [Client-managed conversation state](https://developers.openai.com/api/docs/guides/conversation-state)

For a concrete format difference, the proxy can observe this output message:

```json
{
  "type": "message",
  "id": "msg-api-1",
  "role": "assistant",
  "status": "completed",
  "content": [
    {
      "type": "output_text",
      "text": "Created export.csv with 128 rows.",
      "annotations": []
    }
  ]
}
```

The runtime can export its answer as:

```json
{
  "type": "agentMessage",
  "id": "msg-2",
  "text": "Created export.csv with 128 rows."
}
```

Both contain the same answer text. Neither the common text nor the different IDs establishes which runtime thread contains it. The runtime knows that association; the receiver must verify the content it proposes to restore.

### One full call can cover the retained context

In the export-script example, the first call receives the user message and returns a function call. The second receives the user message, function call, and tool result, then returns the final answer. Evidence for the second call covers all four records in that example, across its input and output.

When a completed call's full input includes everything needed for continuation, its evidence can be sufficient. The response output must be covered too: the final answer is not already present in its own request.

This establishes what the client presented and what the proxy delivered for that call. An assistant item found only in the input remains authenticated as supplied context. Proving that it was generated in an earlier call requires evidence of that earlier output.

The same limit applies to compaction: a call containing a summary covers that summary, not the old records it replaced. Records added after the selected call are also outside its coverage. The worked path assumes full input at the proxy; a delta-only transport needs a separate way to establish the resolved context.

### Let the runtime connect the export to the call

The admission question is now concrete: **can evidence of an inference call support accepting a thread supplied by an external runtime?** A possible integration works as follows:

1. The proxy prepares evidence from the complete input and finalized output as each call completes. It identifies the call by the response ID exposed to the agent and scopes access to the authenticated API account.
2. When saving, the runtime fixes the exported revision and selects the completed call that corresponds to it. This association lives in the runtime, not in the proxy.
3. The runtime obtains that call's evidence and stores it with the transcript. A proposed retrieval interface can use the response ID; it is an extension to our proxy, not a standard Responses API evidence endpoint.
4. On return, the receiving service verifies the evidence and compares its covered values with values extracted from the submitted transcript. The runtime's claim that this is the right evidence is not sufficient on its own.
5. The service restores only what that comparison supports. Uncovered records require an explicit choice such as admission as supplied context or rejection.

A save or unsubscribe handler could trigger this process after the completed call and saved revision have been selected. The lifecycle event itself is not evidence. Retrieval must return material prepared from the observed call, rather than sign a newly uploaded transcript as though the proxy had seen it earlier.

### Choose what the evidence must preserve

A whole-item digest works when the saved API object survives. With a different runtime representation, we could retain a template of that object with its text removed, insert the returned text, and check the original digest. That works, but every verifier receiving the template also sees its retained metadata. IDs, annotations, and other fields can themselves be sensitive.

Instead, we can protect selected claims: message text and role, function name and arguments, or result content, bound to their position within the observed request or response. Each interface then extracts those claims, without reconstructing the original API object. Values removed or rewritten during export still cannot pass as the originals.

We need a portable format that authenticates those claims, allows sensitive values to remain with the user, and supports their later disclosure. Predictable values also need protection against guessing from a published digest. SD-JWT supplies a mechanism based on salted disclosures. The next section implements this call-level evidence with a ready-made library.
