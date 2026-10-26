# Checking the Codex example in section 1

Editorial source note, not part of the published article.

Checked on 2026-10-17 against the local checkout at `/Users/olegromanchuk/Projects/_amnezia/repos/amcode`, HEAD `431f5aa78fd007ec45d591452cfb37ad12c61c15`. No amcode files were modified.

## Choice of representation

The example shows an abbreviated **App Server** `items` array for one turn: a user request, a command record containing its result, and an assistant answer. It is not a complete thread-read response, a rollout file, or a Responses API array. Type names and fields come from `ThreadItem`. The `python export.py` scenario, names, and output are illustrative; they are not a captured session or the result of executing that command during editorial work.

The example distinguishes a record's type, its source, and what it establishes. Approval RPCs and the environment's audit log are outside the portable transcript considered by the article. The receiving environment determines permissions for new actions.

## Source evidence

- `codex-rs/app-server-protocol/src/protocol/v2/item.rs`: `ThreadItem`, `camelCase` serialization, the `UserMessage`, `CommandExecution`, and `AgentMessage` variants, and the definitions of `CommandExecutionRequestApprovalParams` and `CommandExecutionRequestApprovalResponse`.
- `codex-rs/app-server-protocol/schema/typescript/v2/ThreadItem.ts`, `UserInput.ts`, `CommandAction.ts`, `CommandExecutionStatus.ts`: checks of field names and shapes.
- `codex-rs/app-server-protocol/schema/json/v2/ThreadReadResponse.json`: the `definitions.ThreadItem` schema. The example is checked as an array of these objects, not as a complete `ThreadReadResponse`. Omitted fields are permitted by the JSON Schema and Rust deserialization; this is an abbreviated representation, not a complete serializer output.
- `codex-rs/app-server-protocol/src/protocol/common.rs`: the `item/commandExecution/requestApproval` RPC associates request parameters with a decision response.
- `codex-rs/app-server-protocol/schema/json/CommandExecutionRequestApprovalParams.json`, `CommandExecutionRequestApprovalResponse.json`, `JSONRPCResponse.json`: required request fields, the `accept` value, and the response transport envelope `{id, result}`.
- `codex-rs/app-server/tests/suite/v2/config_requirements_exec_tests.rs`: an integration example that receives an approval request, checks its `itemId` association, and sends `CommandExecutionApprovalDecision::Accept`.
- `codex-rs/app-server/tests/common/test_app_server.rs`: `send_response` wraps the result in `JSONRPCResponse { id, result }`. This transport representation differs from the internal `ServerResponse` representation with `method` and `response` fields.
- `codex-rs/app-server-protocol/src/protocol/v2/thread.rs`: `ThreadReadParams` and `ThreadReadResponse`. For paginated history, the source recommends `thread/turns/list` and `thread/items/list` instead of loading all turns with `includeTurns`.
- `codex-rs/app-server-protocol/src/protocol/thread_history_projection.rs`: conversion of persisted `ItemCompleted(TurnItem)` events into `ThreadItem` records for the paginated history interface.
- `codex-rs/rollout/src/policy.rs`, `persisted_event_msg`: `ExecApprovalRequest` and `ApplyPatchApprovalRequest` belong to the `Transient, non-durable events` group, which returns `None`. This directly supports distinguishing a live approval request from saved history.
- `codex-rs/app-server/src/outgoing_message.rs`, `notify_client_response`: a response retrieves a pending callback, may be passed to `track_server_response`, and is sent to the waiting handler. `codex-rs/analytics/src/client.rs` defines separate `ServerRequest` and `ServerResponse` records. This path does not imply that approvals appear in the thread-history API.
- `codex-rs/protocol/src/models.rs`: the separate model-facing `ResponseItem` layer, including `FunctionCall` and `FunctionCallOutput`. Function arguments are serialized as a JSON string; output is a string or an array of content items.

## Limits of the findings

A `commandExecution` item records a command and its result; it is not itself portable cryptographic evidence. Even an authentically recorded exit code and stdout do not authenticate the contents of a file described by the process. This is the example's central distinction.

In the checked version, approval requests are excluded from durable rollout storage, and there is no separate `ThreadItem` carrying the decision. A completed command item does not establish explicit user approval. That is not itself a transfer defect: ordinary continuation does not require restoring a past permission to run a command. Auditing that permission requires a separate capture or an accessible audit record. A separate analytics path does not make those records available through the history interface; this note does not claim that approval records exist nowhere.

The current article leaves tool-execution evidence, business approvals, and audit-event transfer outside its verification contract. The receiving environment applies its current execution policy to new actions after resumption. These source findings do not establish the behavior of arbitrary other Codex versions.

The published article contains no local paths, internal ADRs, or private-product details. The checkout reference is retained here for repeatable editorial review.
