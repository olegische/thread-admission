# Tool admission — article working directory

- [Assembled draft v01 (EN)](tool_admission_v01.md)
- `parts/` — one file per section, `00-`…`10-`, in build order
- `build.py` — assembly; `--check` verifies that the assembled file is up to date

```sh
python3 build.py
python3 build.py --check
```

## Status of v01 (2026-11-08)

Draft in progress. Sections 0–4 cover the receiving service, precedents, evidence, checks and possible runtime responses. Section 5 describes how to compare a signed MCP result with a transformed model input. Section 6 defines a proposed tool evidence profile; sections 7 and 8 describe the example during the conversation and when the thread returns.

The argument digests in §3 were computed using `rfc8785` and SHA-256. The comparison code in §8 verifies the complete MCP result before applying an accepted conversion rule.

Companion code in the shared `examples/` package implements the fixture-based example. The code blocks in §§7–8 are checked against the modules. The run was executed on 2026-11-08; results, versions and limits are in [notes/executed-checks.md](notes/executed-checks.md).

## Editorial norms

Tone toward the MCP community: acknowledge what has been done, without tallying failures. Edits are grounded in the principal's statements.

Tone and manner of presentation as in the first article: a concrete situation, the receiving service's problem, then its solution. MCP discussions serve as a source of real problems and references; the opening explains these problems through an accessible example, without a retrospective survey or terms that require familiarity with the original discussions.

## To verify before publication (CHECK)

1. Quotes from MCP participants against the primary pages: "the refusal record is inert", "unaccounted" in two senses (XuebinMa, 2026-09-13); "later stages must not silently inherit trust from earlier metadata" (ozereray, 2026-09-15); "defaults are unknown, not clean", "a gate that ran and allowed from one that never ran" (damoclais, 2026-09-14 / 09-28); "recompute immediately before execution" (XuebinMa, 2817); "proves the request, not the outcome" (text of SEP-2787); "explicitly not authorization evidence" (text of SEP-2817). The host-reported / runtime-witnessed bug was checked against the primary source on 2026-10-26: XuebinMa (agent-guard), 2026-08-24, https://github.com/modelcontextprotocol/modelcontextprotocol/pull/2817#issuecomment-5390870362. A real incident in their verifier, not a hypothesis. Verbatim: "Until last week both emitted the same audit record type"; "Our verifier reduced the record to a counter"; "a host-asserted `exit_code: 0` and a runtime-witnessed execution landed in the same total"; "The distinction was representable, attributed, documented, and gone by the time anyone read a summary". Record types after the fix: `ExecutionFinished` (witnessed) and `ExecutionReported` ("transcribed rather than witnessed"). In §0 the retelling links to the specific comment; the verbatim quote about `exit_code: 0`, the author, the date and the record types appear next to the counterexample in §4.
2. Dates and statuses: #2704 2026-05-09; SEP-2787 2026-05-25 → 2026-09-22; SEP-2817 2026-05-29, open; SEP-2828 2026-05-31 → 2026-07-18; draft-sirkkavaara-vaara-receipt-14 2026-10-15; #2789 closed 2026-06-30.
3. Field names against the specifications: SLSA Provenance v1 (`runDetails.builder`, `buildDefinition.externalParameters` / `internalParameters` / `resolvedDependencies`), VSA (`verifier.id`, `timeVerified`, `policy`, `inputAttestations`, `verificationResult`, `slsaVersion`), in-toto `ResourceDescriptor`, EAT `profile`, XACML decisions. The links in §1 point to slsa.dev and OASIS; verify the versions.
4. `draft-gilda-wimse-agent-audit-record`: confirm that it uses an in-toto Statement + DSSE + JCS (taken from the `chatgpt-01.txt` dialogue, not from the primary source).
5. §§7–8: before publication, rerun the example and update [notes/executed-checks.md](notes/executed-checks.md) if results or versions change.

## Deliberately left out

OpenAI's rules for intermediaries; policy and routing evidence; the wallet as a product; XACML and RATS as subjects; SCITT profiles for agent receipts; the epistemic record; a composite executor's internal calls to its backends.
