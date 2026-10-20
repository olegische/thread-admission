## Conclusion

Keeping history with the user allows work to continue without a server-side copy of the conversation. When the thread returns, however, the service must determine which records match the earlier work and which were added or changed outside it.

- **For an unchanged history, a saved hash is sufficient.** The receiving service compares the returned history against it. If new records were added after saving, the earlier portion can be verified and the additions handled separately.
- **Replacing local work with a summary allows the conversation to continue but loses detail.** If only the summary is retained, the original messages, tool calls, and results are no longer part of that history.
- **Evidence of content can be collected as the agent exchanges requests and responses with the model.** The agent application constructs model requests and receives the responses. An intermediary service on that path, the inference proxy, records each call's input and output and issues signed evidence. The application saves that evidence alongside the history in the user's storage.
- **We use SD-JWT to compare the history with that evidence.** The inference proxy signs selected values from model requests and responses. When the history returns, the receiving service verifies the signature and compares those values with the thread's records. The example checks message text and roles this way, even when the application stores them in a different format.

The history thus stays with the user, while the service gains a basis for restoring it. The service continues with verified content and separately decides how to handle additions for which no evidence is available.
