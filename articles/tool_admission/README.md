# Tool admission — article working directory

- [Assembled draft v01 (EN)](tool_admission_v01.md)
- `parts/` — one file per section, `00-`…`09-`, in build order
- `notes/` — working notes outside the article text: [executed checks](notes/executed-checks.md) and a [draft on lineage across agents](notes/agent-lineage.md) for future work
- `build.py` — assembly; `--check` verifies that the assembled file is up to date

```sh
python3 build.py
python3 build.py --check
```

## Status of v01 (2026-11-10)

Draft in progress, ten sections.

| Section | Content |
|---|---|
| 0 | The opening case and the question for the receiving service. |
| 1 | What a saved history can establish, with precedents and the MCP proposals. |
| 2–3 | The two kinds of evidence and the checks that compare them. |
| 4 | The four statuses and what the service continues from. |
| 5 | Comparing a signed MCP result with the transformed model input. |
| 6 | The proposed tool evidence profile and its schema. |
| 7 | The example during the conversation: the executor's code and six refused requests. |
| 8 | The example when the thread returns: the service's code and 24 cases. |
| 9 | Conclusion and how to run the examples. |

Companion code in the shared `examples/` package implements the fixture-based example. `scripts/check.py` keeps the code blocks in §§7–8 identical to the modules and the schema in §6 identical to `schemas/tool-call.schema.json`. It recomputes the argument digests printed in §3 and checks the fixtures against the request example in §6. The run was last executed on 2026-11-10. Results, versions and limits are in [notes/executed-checks.md](notes/executed-checks.md).

## Editorial norms

Tone toward the MCP community: acknowledge what has been done, without tallying failures. Edits are grounded in the principal's statements.

Tone and manner of presentation as in the first article: a concrete situation, the receiving service's problem, then its solution. MCP discussions serve as a source of real problems and references. The opening explains these problems through an accessible example, without a retrospective survey or terms that require familiarity with the original discussions.

One running example, the `python export.py` call, carries the whole article. A new point is shown inside that example, not with a new one.

No semicolons in prose. Split into sentences, join with a conjunction, or use a colon when the second half explains the first.

Limits are stated where they arise. The article has no separate list of what the evidence does not establish, and the conclusion follows the first article's form: the problem, what was established, open questions, how to run the examples.

## To verify before publication (CHECK)

1. MCP references against the primary pages. §0 retells one comment in the SEP-2817 thread without quoting it: XuebinMa (agent-guard), 2026-08-24, https://github.com/modelcontextprotocol/modelcontextprotocol/pull/2817#issuecomment-5390870362. The retelling was checked against the primary source on 2026-10-26. §1 and §3 describe SEP-2787, SEP-2817 and SEP-2828 in one sentence each, and §9 refers to the work following SEP-2828. Reread those pages and confirm the descriptions still hold. The article states no dates or statuses for them.
2. Standards cited by link: SLSA Provenance v1.0 and Verification Summary v1.0, the in-toto Statement v1, XACML 3.0, RFC 8176, RFC 8485, RFC 8785, RFC 9901. Confirm each link supports the sentence it is attached to.
3. Drafts that can change: the SD-JWT VC draft must still define `typ: dc+sd-jwt`, `vct`, Type Metadata and `vct#integrity` as §6 uses them. `draft-thaha-scitt-agent-execution-evidence` is linked at revision 01 in §2. Check for a newer revision.
4. §6 says the profile does not use the registered names `amr`, `acr`, `vot`, `vtm`, `events` or `attest`. Confirm these against the IANA JWT claims registry.
5. Temporal in §1: the documentation link and the two source links pinned to commit `235e894`. Confirm they show what the text says about history events and importing history from another cluster.
6. §§7–8: before publication, rerun the example and update [notes/executed-checks.md](notes/executed-checks.md) if results or versions change.

## Deliberately left out

OpenAI's rules for intermediaries; policy and routing evidence; the wallet as a product; XACML and RATS as subjects; SCITT profiles for agent receipts; the epistemic record; a composite executor's internal calls to its backends.

Left for future work and named in the conclusion: separate records of a decision before an operation and its outcome, and chains of evidence passed between agents. The second has a draft in [notes/agent-lineage.md](notes/agent-lineage.md).
