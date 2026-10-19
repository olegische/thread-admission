# API items and App Server items

Editorial source note, not part of the published article. Checked 2026-10-18 against local amcode HEAD `431f5aa78fd007ec45d591452cfb37ad12c61c15`.

## Sources

- `codex-rs/app-server-protocol/src/protocol/v2/item.rs:291`: CommandExecution fields. At line 923 onward, conversion from CoreTurnItem uses CommandExecutionPresentation, structured command metadata, aggregated output and exit code. This is not a serialization of two model-API items.
- `codex-rs/protocol/src/models.rs:1107,1156`: FunctionCall and FunctionCallOutput. Function arguments are a JSON string; paired output uses call_id.
- `codex-rs/core/src/tools/handlers/shell_spec.rs:41,96`: workdir parameter and exec_command tool name.
- `codex-rs/core/src/tools/context.rs:524`: unified-exec response header contains optional chunk ID, wall time, exit code or process ID, optional token count, and Output. The model-facing string differs from aggregatedOutput in App Server.
- `codex-rs/app-server-protocol/src/protocol/item_builders.rs:54,145`: the top-level command is a shell-formatted presentation; command actions come from parsed commands. Both may redact recognizable secrets. These shell-specific fields do not reconstruct a complete generic function-call item.
- `codex-rs/shell-command/src/parse_command.rs:54,74`: unknown-command presentation can retain the shell script after removing the shell invocation. This supports the simple `python export.py` example, not arbitrary inverse reconstruction of shell syntax.
- `codex-rs/app-server-protocol/src/protocol/v2/item.rs:337`: McpToolCall is a distinct App Server item with server, tool, arbitrary JSON arguments, result, error and status. It does not require shell arguments or an exit code.
- `codex-rs/app-server-protocol/src/protocol/thread_history.rs:831,3309`: the completion handler combines invocation and result into one mcpToolCall. The restoration test supplies the docs/lookup example used for the article's abbreviated illustration.
- `codex-rs/core/src/tools/context.rs:157,184`: McpToolOutput becomes function_call_output, adds a wall-time/output header and applies model-context truncation.
- `codex-rs/protocol/src/models.rs:2436`: MCP result conversion normally uses non-null structuredContent as serialized JSON; otherwise it converts content blocks. Encrypted content has a separate branch. The App Server result and the model-facing output are not universally identical.
- `codex-rs/codex-mcp/src/tools.rs:58`: model-visible tool identities can differ from raw MCP server/tool identities. Their mapping cannot be inferred by blindly concatenating exported names.
- https://developers.openai.com/api/docs/guides/function-calling : Responses function-call item and function-call-output item, distinct from Chat Completions assistant.tool_calls and role=tool messages.
- https://developers.openai.com/codex/app-server/ : official items documentation confirms commandExecution, mcpToolCall, dynamicToolCall and the two message representations. Searched and fetched the items section on 2026-10-18.

The published JSON examples are illustrative values in these formats, not a captured live call. Verification observes the proxy's agent-facing Responses representation, not an unspecified internal or provider-native representation.

## Current verification design

Updated 2026-10-20. Sections 5–6 cover one completed model call's whole input/output items. The proxy's scope is the authenticated API account and agent-facing response ID. It does not infer thread identity, maintain a global history cursor, or deduplicate repeated context across requests.

Section 7 defines thread (runtime-managed conversation and execution history), transcript (its serialized view), model context (what is supplied for a particular call), and response output. The runtime selects the call corresponding to its saved revision. A single full-input call can cover the retained context, but an input item is not thereby proved to be an earlier generated output. Compaction, context selection, and unobserved later work limit coverage.

Section 8 uses per-call SD-JWT component claims. The proxy extracts its own text, function name, argument string and result string without interpreting shell or MCP implementations. The client preserves disclosures and salts. The runtime adapter proposes matching message claims; the verifier returns the request/response group and array-local index along with the matched role and text.

The executed adapter does not cover commandExecution contents, MCP fields, runtime IDs, or positions relative to tool records. The source findings above do not support treating aggregatedOutput as universally identical to model-facing output.

Additional source checks at the same local commit:

- `codex-rs/core/src/context_manager/history.rs:600`: `for_prompt` normalizes history and drops unsuitable items; retained tool outputs can already be truncated before a model request.
- `codex-rs/core/src/client_common.rs:59`: request input is derived from `Prompt` items, including image normalization.
- `codex-rs/core/src/client.rs:2137`: WebSocket continuation can send incremental items with previous_response_id. The article's worked path explicitly assumes full input, not this delta transport.

See [SD-JWT example](sd-jwt-example.md) for versions, commands, executed mutations and the known reference-library gap. No live Codex/proxy round trip is claimed.
