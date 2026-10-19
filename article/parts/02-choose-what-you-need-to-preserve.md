## Before adding signatures, decide what you need to recover

Sometimes the cheapest useful answer is to resume from a summary and inspect the work again.

For a coding task, the receiving agent may be able to retrieve the exact repository revision, read the diff, and run a fresh check. The summary tells it where to start. The repository supplies the code. The new execution supplies a current result.

This has a real product analogue: Claude Code Desktop documents moving a local session to the cloud with the conversation carried as a summary. Its transfer dialog separately describes whether files move. That establishes a supported transfer format; it does not document the security policy used to admit the summary. [Claude Code Desktop documentation](https://code.claude.com/docs/en/desktop#continue-in-another-surface)

Whether this is enough for your service depends on the work being resumed:

| What is available after transfer? | A practical continuation strategy |
|---|---|
| Exact artifacts, with cheap and repeatable checks | Load the artifacts, treat the summary as guidance, and check again. |
| Some original records are needed to continue | Retain and verify those records alongside the summary. |
| Only the thread, without access to the original artifacts | Preserve the history needed for continuation and verify what came back. |

Git helps with the first row. It can identify the code being examined. It does not reconstruct a tool response from a database that has since changed or a local file that was never committed. Running a query today establishes today's result. If the earlier response is needed as context, keep that record and its call ID through the transfer.

Our target architecture includes the third row. The service may lack access to the user's original documents, local files, or connector accounts. In that case, losing a particular record can mean losing the ability to continue a task as intended. Asking the model to reconstruct it supplies new text, not the missing record.

### Three ways to continue

An unchanged snapshot is the easy baseline: compare it with a hash saved by the service and restore the matching revision. There are three useful continuation strategies:

| Approach | What enters the next session | What you need |
|---|---|---|
| Summarize the history | A summary supplied as new user context | A compaction step and normal input controls |
| Verify a prefix, summarize the tail | The saved records before the saved offset, followed by a summary of the additions | A protected offset and prefix hash, plus compaction |
| Compare returned content with model-call evidence | Records or claims whose content and supported relationships match an observed call | Verification data for the call's ordered input and output |

The second approach combines snapshot recognition with compaction. It preserves the history the service can recognize without requiring a signature for every new message. The third uses observations of model calls as its reference. A call whose full input and output cover the retained context may be sufficient; other material needs separate coverage or a fallback policy.

For that third approach, an operator can keep an index of API requests and responses or issue portable signed statements. These are implementation choices within the approach, not additional stages every service must adopt.

The timing matters. A catalog entry made at export covers that revision. Digests recorded during a model call can cover its request and response. Hashing an upload for the first time at import establishes neither its earlier occurrence nor its place in a sequence.

Historical TLS session tickets offer a precedent for the baseline: clients hold server-protected state for later resumption. A readable thread needs its own format and rules, but client custody does not itself prevent integrity protection. [RFC 5077](https://www.rfc-editor.org/rfc/rfc5077.html)
