# Tool admission — article working directory

- [Assembled draft v01 (EN)](tool_admission_v01.md)
- `parts/` — one file per section, `00-`…`08-`, in build order
- `build.py` — assembly; `--check` verifies that the assembled file is up to date

```sh
python3 build.py
python3 build.py --check
```

## Status of v01 (2026-10-26)

Complete draft. Added: the "why" for the receiving side (§0), precedents for evidence and Temporal (§1), `source_class` instead of `epistemic_class`, the consumer of the class (§2), an example profile typed through `vct` (§6), counterexample 2 for different actors (§4), three distinctions (§7), standing / authority and lineage between agents (§8). Written from the problem, not from code: the experiment (§6) is specified and marked in the text as not run; no results are claimed. The tool statement schema in §6 and the two Python functions in §3 are a proposed profile; no reference implementation is published, and the text says so.

The digests in §3–§4 are real: computed with `rfc8785` + SHA-256 over the thread-admission fixtures (`fixtures/api-call.json`) and over a result variant with exit code 1.

## Editorial norms

Tone toward the MCP community: acknowledge what has been done, without tallying failures. Edits are grounded in the principal's statements.

Tone and manner of presentation as in the first article: a concrete situation, the receiving service's problem, then its solution. MCP discussions serve as a source of real problems and references; the opening explains these problems through an accessible example, without a retrospective survey or terms that require familiarity with the original discussions.

## To verify before publication (CHECK)

1. Quotes from MCP participants against the primary pages: "the refusal record is inert", "unaccounted" in two senses (XuebinMa, 2026-09-13); "later stages must not silently inherit trust from earlier metadata" (ozereray, 2026-09-15); "defaults are unknown, not clean", "a gate that ran and allowed from one that never ran" (damoclais, 2026-09-14 / 09-28); "recompute immediately before execution" (XuebinMa, 2817); "proves the request, not the outcome" (text of SEP-2787); "explicitly not authorization evidence" (text of SEP-2817). The host-reported / runtime-witnessed bug was checked against the primary source on 2026-10-26: XuebinMa (agent-guard), 2026-08-24, https://github.com/modelcontextprotocol/modelcontextprotocol/pull/2817#issuecomment-5390870362. A real incident in their verifier, not a hypothesis. Verbatim: "Until last week both emitted the same audit record type"; "Our verifier reduced the record to a counter"; "a host-asserted `exit_code: 0` and a runtime-witnessed execution landed in the same total"; "The distinction was representable, attributed, documented, and gone by the time anyone read a summary". Record types after the fix: `ExecutionFinished` (witnessed) and `ExecutionReported` ("transcribed rather than witnessed"). In §0 the retelling links to the specific comment; the verbatim quote about `exit_code: 0`, the author, the date and the record types appear next to the counterexample in §4.
2. Dates and statuses: #2704 2026-05-09; SEP-2787 2026-05-25 → 2026-09-22; SEP-2817 2026-05-29, open; SEP-2828 2026-05-31 → 2026-07-18; draft-sirkkavaara-vaara-receipt-14 2026-10-15; #2789 closed 2026-06-30.
3. Field names against the specifications: SLSA Provenance v1 (`runDetails.builder`, `buildDefinition.externalParameters` / `internalParameters` / `resolvedDependencies`), VSA (`verifier.id`, `timeVerified`, `policy`, `inputAttestations`, `verificationResult`, `slsaVersion`), in-toto `ResourceDescriptor`, EAT `profile`, XACML decisions. The links in §1 point to slsa.dev and OASIS; verify the versions.
4. `draft-gilda-wimse-agent-audit-record`: confirm that it uses an in-toto Statement + DSSE + JCS (taken from the `chatgpt-01.txt` dialogue, not from the primary source).
5. §6: before publication, either replace "specified and not yet run" with results and versions, or leave it as is and publish that way. The second is honest but weaker than the thread article.

## Deliberately left out

OpenAI's rules for intermediaries; policy and routing evidence; the wallet as a product; XACML and RATS as subjects; SCITT profiles for agent receipts; the epistemic record; a composite executor's internal calls to its backends.
