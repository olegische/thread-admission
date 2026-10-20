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

The answer text survives export, but its surrounding object changes. A digest of the original API item cannot be checked directly against the exported `agentMessage`. The receiver needs a way to compare the retained content across these representations.

### Let the runtime connect the export to the call

The admission question is now concrete: **can evidence of an inference call support accepting a thread supplied by an external runtime?** A possible integration works as follows:

1. The proxy prepares evidence from the complete input and finalized output as each call completes. It identifies the call by the response ID exposed to the agent and scopes access to the authenticated API account.
2. When saving, the runtime fixes the exported revision and selects a completed call covering the content to restore. A call containing a summary covers that summary; records added afterward need separate evidence. The association between the exported revision and the selected call lives in the runtime, not in the proxy.
3. The runtime obtains that call's evidence and stores it with the transcript. A proposed retrieval interface can use the response ID; it is an extension to our proxy, not a standard Responses API evidence endpoint.
4. On return, the receiving service verifies the evidence and compares its covered values with values extracted from the submitted transcript.
5. The service restores only what that comparison supports. Uncovered records require an explicit choice such as admission as supplied context or rejection.

When saving or unsubscribing from a thread, the runtime can retrieve the prepared evidence for the selected call and store it with the transcript.

### Choose what the evidence must preserve

A whole-item digest works when the saved API object survives. With a different runtime representation, one option is a **template with a hole**: retain the original object with a placeholder for its text, fill that placeholder with the returned text, and verify the reconstructed object's digest. The template also exposes the retained metadata to the verifier, including potentially sensitive IDs, annotations, and other fields.

Instead, we can protect selected claims: message text and role, function name and arguments, or result content, bound to their position within the observed request or response. Each interface then extracts those claims, without reconstructing the original API object. Values removed or rewritten during export still cannot pass as the originals.

We need a portable format that authenticates those claims, allows sensitive values to remain with the user, and supports their later disclosure. Predictable values also need protection against guessing from a published digest. SD-JWT supplies a mechanism based on salted disclosures. The next section implements this call-level evidence with a ready-made library.
