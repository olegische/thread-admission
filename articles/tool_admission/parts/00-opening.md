# Tool Admission: What a Service May Believe About a Tool Record It Did Not Witness

*This article is about the receiving side: what a service may restore from a tool record in a returned thread, and what it does when no evidence came with it.*

Suppose you are building a service for an AI assistant that lets users resume work from a saved conversation. A user may have continued that conversation in a local agent before returning it to your service. Alongside messages, the history contains tool calls and their results. Which of those results can your assistant rely on when continuing the task?

The [earlier article](../../thread_admission/context_admission.md) used evidence issued by a proxy that observed model calls: the service can check that the returned content matches what the proxy received as input or delivered as output. For tool results, this leaves a gap. Evidence that a model received the text `Tests passed` does not establish that the tests produced it. A runtime or user could have changed the result before it reached the model, and the proxy would have witnessed the changed text.

This problem surfaced in the [MCP discussion on audit context for tool calls](https://github.com/modelcontextprotocol/modelcontextprotocol/pull/2817#issuecomment-5390870362). An implementer reported that a consumer had treated an outcome reported by the host in the same way as an outcome observed by the runtime. The distinction between how the records were obtained was lost when they were used.

The MCP proposals identify two separate things a service might receive: a [signed statement of what was requested](https://github.com/modelcontextprotocol/modelcontextprotocol/pull/2787) and a [record of what the executing side decided and returned](https://github.com/modelcontextprotocol/modelcontextprotocol/pull/2828).

A receiving service needs to establish who attests to the result, which call it belongs to, and whether it matches the result the model received. When evidence is missing, the service still needs a rule for retaining and using the record.

That decision is tool admission. The executor is the party that processed the tool call and returned the result. We will define its statement, the checks that link it to model evidence, and admission rules for records with different evidence coverage. These rules state what the service may accept as established. Its policy decides whether that is sufficient for the next action.
