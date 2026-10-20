## Before adding signatures, decide what you need to recover

Sometimes the cheapest useful answer is to resume from a summary and inspect the work again.

For a coding task, the receiving agent may be able to retrieve the exact repository revision, read the diff, and run a fresh check. The summary tells it where to start. The repository supplies the code. The new execution supplies a current result.

This has a real product analogue: Claude Code Desktop documents moving a local session to the cloud with the conversation carried as a summary. Its transfer dialog separately describes whether files move. That establishes a supported transfer format; it does not document the security policy used to admit the summary. [Claude Code Desktop documentation](https://code.claude.com/docs/en/desktop#continue-in-another-surface)

Whether this is enough for your service depends on the work being resumed:

- **Exact artifacts are available, with cheap and repeatable checks.** Load the artifacts, treat the summary as guidance, and check again.
- **Some original records are needed to continue.** Retain and verify those records alongside the summary.
- **Only the thread is available, without access to the original artifacts.** Preserve the history needed for continuation and verify what came back.

Git helps when the original artifacts are available. It can identify the code being examined. It does not reconstruct a tool response from a database that has since changed or a local file that was never committed. Running a query today establishes today's result. If the earlier response is needed as context, keep that record and its call ID through the transfer.

Our target architecture includes continuation from the thread alone. The service may lack access to the user's original documents, local files, or connector accounts. In that case, losing a particular record can mean losing the ability to continue a task as intended. Asking the model to reconstruct it supplies new text, not the missing record.

### Three ways to continue

An unchanged snapshot is the easy baseline: compare it with a hash saved by the service and restore the matching revision. There are three useful continuation strategies:

1. **Summarize the history.** The next session receives a summary as new user context. This requires a compaction step and normal input controls.
2. **Verify a prefix, summarize the tail.** The next session receives the saved records before the saved offset, followed by a summary of the additions. This requires a protected offset and prefix hash, plus compaction.
3. **Compare returned content with model-call evidence.** The next session receives records or claims whose content and supported relationships match an observed call. This requires verification data for the call's ordered input and output.

For the third approach, one completed model call may be enough if its full input and output cover the context needed to continue. Material outside that call needs separate evidence or an explicit decision about whether to use it as new context.

The operator can retain the call's verification data in a server-side index or give the client a portable signed statement to return with the thread. The following sections work through both options.

Historical TLS session tickets offer a precedent for the baseline: clients hold server-protected state for later resumption. A readable thread needs its own format and rules, but client custody does not itself prevent integrity protection. [RFC 5077](https://www.rfc-editor.org/rfc/rfc5077.html)
