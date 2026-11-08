# Tool Admission: What a Service May Believe About a Tool Record It Did Not Witness

*A practical look at tool calls in saved agent histories and the evidence a receiving service can use to check them.*

Suppose you are building a service for an AI assistant where users keep their conversation histories in storage they control and return them to the service when they want to continue. They may also work on the same thread with a local agent before bringing it back. How can your service trust the history it receives?

In the [previous article](../../thread_admission/context_admission.md), we used evidence from a proxy that observed model calls. The receiving service could check which responses the model returned and which messages were sent to it as user input. That gave the service a way to restore those parts of the conversation.

A thread also contains tool calls and their results. Suppose a record says the agent ran `python export.py`, the command exited with code `0`, and the output was `Wrote export.csv (128 rows).` The user now asks the assistant to continue working with that export.

The proxy's evidence can show what result was sent to the model. But the result could have changed before it reached the proxy. How can the service establish what the tool itself returned?

A related issue came up in an [MCP discussion](https://github.com/modelcontextprotocol/modelcontextprotocol/pull/2817#issuecomment-5390870362). A developer described an audit tool that counted executions observed by its runtime together with executions reported by another program. The summary lost the distinction between what the runtime saw and what it was told.

MCP proposals describe records a service can use: a [signed statement of what was requested](https://github.com/modelcontextprotocol/modelcontextprotocol/pull/2787) and a [record of what the executing side decided and returned](https://github.com/modelcontextprotocol/modelcontextprotocol/pull/2828).

We will examine how a receiving service can compare evidence from the model call and the tool executor: which call the result belongs to, what the executor reported and what the model received. When evidence is missing, the service still needs a rule for retaining and using the record. We call this decision tool admission. The executor is the party that processed the tool call and returned the result; the service's policy decides whether what has been established is sufficient for the next action.
