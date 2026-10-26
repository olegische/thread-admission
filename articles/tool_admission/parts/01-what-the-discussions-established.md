## What the discussions established, and where it already existed

The three proposals occupy three layers. Each layer makes a claim and disclaims the rest.

| Layer | Proposal | Status | Who asserts | What it establishes | What it does not |
|---|---|---|---|---|---|
| Audit context | [#2704](https://github.com/modelcontextprotocol/modelcontextprotocol/discussions/2704) → [SEP-2817](https://github.com/modelcontextprotocol/modelcontextprotocol/pull/2817) | Discussion opened 2026-05-09; SEP opened 2026-05-29; open, no sponsor recorded | client or host | why the tool was invoked, which model, which turn | authorization, truth, execution |
| Request attestation | [SEP-2787](https://github.com/modelcontextprotocol/modelcontextprotocol/pull/2787) | Opened 2026-05-25; closed 2026-09-22; closure note directs new proposals to a working group | an issuer upstream of the planner | what was requested: tool, argument commitment, intent as presented | outcome, execution, truth of the intent |
| Execution record | [SEP-2828](https://github.com/modelcontextprotocol/modelcontextprotocol/pull/2828), the Internet-Draft | Opened 2026-05-31; withdrawn 2026-07-18; continued as an [independent Internet-Draft](https://datatracker.ietf.org/doc/draft-sirkkavaara-vaara-receipt/) | the enforcement point | a decision before the effect, an outcome after it, bound to the request | truth of the result about the world |

The disclaimers are the valuable part. SEP-2787 groups the envelope's fields by their source: `issuerAsserted` for identity and timing, `plannerDeclared` for intent and correlation handles, `payloadDerived` for digests computed from the call. The text says the issuer attests that declared values were presented at signing time, not that they are true. SEP-2828 separates the decision record, written before the side effect with its verdict and basis, from the outcome record, written after execution with a commitment over the result, and pairs them by a back link to the request. The discussion of SEP-2817 added rules for the verifier: a step reports a positive result only when its inputs were stated at that step ("defaults are unknown, not clean"); a reader must be able to tell a gate that ran and allowed from one that never ran; records carry a rule version and a verifier refuses an unknown one; bound values must be recomputed immediately before execution, because every field can be correct while the record describes an action that never happened.

These are the right distinctions. They are also, almost without exception, distinctions that supply-chain security made for software builds several years ago and published as standards. The table below is not a complaint. It is the map that lets the rest of this article use existing vocabulary rather than invent one.

| Construction in the MCP threads | Where it already exists |
|---|---|
| Envelope grouped by source: issuer-asserted, planner-declared, payload-derived | [SLSA Provenance v1](https://slsa.dev/spec/v1.0/provenance), an in-toto predicate: `runDetails.builder` is the issuer; `buildDefinition.externalParameters` are under the invoker's control and not verified by the builder; `internalParameters` are under the builder's control; `resolvedDependencies` are derived. The same three blocks |
| Decision record before the effect, with policy and basis | [SLSA Verification Summary Attestation](https://slsa.dev/spec/v1.0/verification_summary): `verifier.id`, `timeVerified`, `policy` with a digest, `inputAttestations`, `verificationResult` of `PASSED` or `FAILED` |
| Outcome record after the effect, with a commitment over the result | in-toto link and provenance: `materials`, `products`, `subject` entries by digest |
| Back link by digest of the request's bytes; outcome pins the decision's digest | in-toto `subject`: a statement about an artifact names it by digest, and a statement is itself an artifact |
| Arguments as reference with digest, inline projection, or redacted projection, with a three-way match | in-toto `ResourceDescriptor`: `uri`, `digest`, `content`, `annotations` in one object |
| Three states: pass, fail, not performed | [XACML 3.0](https://docs.oasis-open.org/xacml/3.0/xacml-3.0-core-spec-os-en.html) decisions `Permit`, `Deny`, `Indeterminate`, `NotApplicable`; RATS attestation results with an explicit `none` |
| Rule version in the record; unknown version is refused | VSA `policy.digest` and `slsaVersion`; an unknown in-toto `predicateType` is rejected; the EAT `profile` claim |
| Nonce and lifetime against replay | JWT `jti`, `iat`, `exp` in [RFC 7519](https://www.rfc-editor.org/rfc/rfc7519); CWT in RFC 8392 |
| Strong and weak joins between records | Weak: [W3C Trace Context](https://www.w3.org/TR/trace-context/), unauthenticated. Strong: OAuth transaction tokens and the `act` chain of [RFC 8693](https://www.rfc-editor.org/rfc/rfc8693) |
| Order of gates | in-toto layouts with ordered steps; SCITT registration order |
| Intermediaries forward the metadata key unmodified | end-to-end versus hop-by-hop fields in RFC 9110; integrity is under the signature anyway |
| Time anchors, non-retraction | RFC 3161 timestamps; [SCITT](https://www.rfc-editor.org/rfc/rfc9943); Certificate Transparency |
| Issuer, holder, verifier | EUDI architecture, W3C Verifiable Credentials, SD-JWT VC |
| Recompute immediately before execution | complete mediation, Saltzer and Schroeder, 1975; freshness in RATS; proof of possession at time of use |
| Do not widen a fallback projection to make a failed binding pass | explicit match rules in in-toto layouts; a fixed appraisal policy in RATS |

An agent-specific profile on this stack also exists: [draft-gilda-wimse-agent-audit-record](https://datatracker.ietf.org/doc/draft-gilda-wimse-agent-audit-record/) records authorization decisions as in-toto Statements in DSSE envelopes with JCS canonicalization.

### A class for the source of a result

One construction this article needs is not in the MCP threads at all: a signed statement by the executor about how its result was obtained, observed, computed or generated, consumed by a policy that decides what the result may ground. That too has precedents, in identity systems, in attestation, in accounting and in law, and the article borrows the pattern rather than the names.

| Precedent | What is standardized | What this article takes |
|---|---|---|
| OpenID Connect `amr` and `acr`, values in [RFC 8176](https://www.rfc-editor.org/rfc/rfc8176) | the identity provider signs how authentication was performed; the relying party applies step-up policy | the pattern: issuer states the method, consumer decides |
| [RFC 8485](https://www.rfc-editor.org/rfc/rfc8485) Vectors of Trust | a vector in a signed token whose values have meaning only within a trust framework named by URL; a higher value is not assumed better; an omitted component makes no claim | the three interpretation rules and the framework by reference |
| NIST SP 800-63-3 identity, authenticator and federation assurance levels | assurance level as a class of evidence consumed by relying-party policy | the same construction in a government standard |
| RATS Attestation Results for Secure Interactions, category `sourced-data` | integrity of data the attester obtained from outside; tiers none, affirming, warning, contraindicated; `none` must be treated as no claim | "defaults are unknown, not clean" as a standard |
| XACML `AttributeDesignator` with `Issuer` | a policy decision conditioned on who asserted the attribute | provenance of an input as a condition of the decision |
| IFRS 13 fair value hierarchy | Level 1 quoted prices, Level 2 other observable inputs, Level 3 unobservable model inputs; maximize observable inputs; disclose the level | the three values themselves: observed, computed, generated |
| Rules of evidence: hearsay and the business-records exception | admissibility of a record for a purpose depends on how it was produced | the word admission and its meaning |
| NATO STANAG 2511 | reliability of the source graded separately from credibility of the information | two axes, not one |
| IEC 62304, software of unknown provenance | a formal class for a component whose origin is not controlled, with process consequences | a class as an input to policy |

None of these systems asks whether the input is true. Each asks how it was obtained and lets a policy decide what it may support. That is the shape this article gives the executor's class claim.

### The closest engineering precedent for consuming a history

Durable execution engines have been admitting histories into code for a decade. In [Temporal](https://github.com/temporalio/temporal), a workflow's history is a typed sequence of events: an activity's result, a side-effect marker, a signal from outside, a timer. The server holds the history as the source of truth. A worker replaying a workflow must emit the same commands the history records, or the replay fails with a non-determinism error: the prefix is verified by re-execution. Importing a history from another cluster checks its version lineage and the continuity of event identifiers, not its content; the server code rejects an import whose version history does not match. Admission as a structural check plus a consistency check is established practice.

Temporal has no class for the source of an activity's result, and it does not need one. Every activity is executed by a worker in the same trust domain as the server; there is nothing to type. The receiving service in this article has several issuers it did not run, which is why it needs the class, and why the class is taken from the standards above, where the issuers are several too.

### What the threads added, and what nobody covers

What the MCP threads contributed that is their own is narrower than the volume of text suggests, and it is real: a predicate schema for "a tool call was executed", which in-toto was designed to accept, and the verifier practices above, restated for tool calls with working code and test vectors behind them. This article takes the practices and says where they came from.

Two things are covered by none of the standards in the tables. The first is the consumer. In-toto, XACML and SCITT say what a record means and how to verify it; none says what a receiving service does with the record after a thread returns, what standing it assigns, how it downgrades, what it does when the record has no evidence at all. The closest analogue is an in-toto layout, which verifies a supply chain at the point of consumption, but it has no notion of admitting a record at reduced standing. The second is selective disclosure. In-toto, DSSE and VSA are all-or-nothing; none of the three MCP proposals uses SD-JWT. A record that several verifiers must read with different entitlements is covered only by [RFC 9901](https://www.rfc-editor.org/rfc/rfc9901). Both gaps are this article's subject, and the earlier article's stack, DSSE for whole records and SD-JWT for disclosed claims, already fills the second.
