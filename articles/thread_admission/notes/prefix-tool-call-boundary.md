# Tool-call boundary at a prefix checkpoint

Editorial verification, not publication text. Checked 2026-10-18 against local amcode HEAD `431f5aa78fd007ec45d591452cfb37ad12c61c15`. No amcode files modified.

## Source evidence

- `codex-rs/core/src/context_manager/normalize.rs:21`: `ensure_call_outputs_present` first collects matching outputs from the entire supplied array. Missing FunctionCall outputs get `aborted`; insertion is immediately after each call, in reverse index order. A result mentioned inside summary text is not a structured output.
- `normalize.rs:158`: synthetic IDs are stable for repeated prompt projections; synthetic outputs need not be persisted.
- `context_manager/history.rs:603`: `for_prompt` consumes a history snapshot and normalizes it; `normalize_history` uses `Arc::make_mut`.
- `session/turn.rs:554`: the ordinary sampling request uses `sess.clone_history().await.for_prompt(...)`.
- `compact.rs:277,301`: local compaction likewise uses a cloned history and a normalized prompt. `compact.rs:407` builds replacement history from user messages and summary. This is not our proposed tail-only compaction workflow.
- `context_manager/history_tests.rs:2645`: existing test `for_prompt_assigns_stable_id_to_synthetic_output_without_reordering_history` asserts call, synthetic output, later user message. Inspected, not executed as part of the Codex suite.
- `normalize.rs:92,120` and `util.rs:86`: missing custom/local-shell outputs can invoke `error_or_panic` unless marked inherited; debug behavior differs from the ordinary FunctionCall case. Do not generalize the FunctionCall result to every item type/build.

## Executed check

Ran the unchanged `ensure_call_outputs_present` function extracted from this checkout in a standalone Rust harness, with minimal envelope/item type scaffolding. Calls had no item IDs, so the synthetic-ID stub follows the production None case. This checks the function's insertion logic, not the complete runtime, API acceptance, model behavior, or actual summarization.

Four assertions passed:

1. 99 ordinary items + FunctionCall at position 100 + summary: first 100 remain identical, synthetic `aborted` occupies position 101, summary becomes position 102.
2. If a previous mock at 101 is compacted away, normalization recreates exactly one mock. No accumulation.
3. An open call at 99 inserts the mock at 100, shifting subsequent prompt positions. This matters if someone hashes the normalized request instead of the saved records.
4. A matching structured result retained in the array prevents synthesis.

## Editorial conclusion

No evidence for a necessary failure at the 100/101 boundary. Prefix verification and runtime prompt normalization are different operations. Keeping call/result pairs together preserves structured detail; it is not a cryptographic requirement. If a real result is summarized, later normalization may represent the call as aborted even though the summary describes its actual result. This is a change in model-visible representation, not proof of a failed request or a changed saved prefix.
