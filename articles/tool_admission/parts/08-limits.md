## What tool evidence does not establish

Stated as a verifier would state them.

1. A tool statement attests the executor's observation, not the state of the world. A weather service attests the forecast it returned. A payment service attests that it submitted a transaction, or that it received a confirmation, whichever it saw. The record never says what the weather was or whether the money arrived.
2. An executor can sign what it did not do. The signature establishes who made the statement, not that the statement is true. Registering statements with a transparency log makes a false statement durable and attributable; it does not make it impossible.
3. The signed reference records the executor's account of which model request it processed. Matching results show that the covered values agree; they do not trace how identical bytes travelled through the client. The checks do not establish that the thread is complete or that no later call occurred.
4. The absence of a tool statement does not establish that no operation took place. It establishes nothing, and the admission rules treat it as the normal case rather than as a finding.
5. The source class is declared by the executor about itself. A server that declares `observer` while returning generated text is the second limit again, with a different field, and a control plane that keeps its own table of classes by tool identity is entitled to override the declaration.
6. The profile carries one record per call with an `outcome`. It does not separate a decision made before the effect from the outcome observed after it, so it cannot answer "was this allowed" as distinct from "did this run". The Internet-Draft that continued SEP-2828 does separate them; the composition section says how the two fit.
7. A statement carried inside the thread, in MCP's `_meta` or in a runtime's export, depends on every intermediary preserving it. A lost statement is lost evidence, not a verification failure, and the record it would have covered drops to Shown.

### Three questions this article does not answer

Readers of the MCP threads will bring three questions here that belong elsewhere, and it is better to say so than to let them look for answers in the admission rules.

Which issuers to trust is the verifier's configuration, exactly as the trusted public key was in the earlier article: an allow-list, the operator's own gateway, a federation. The profile consumes that decision and does not make it. A statement from an issuer the service does not accept is treated as no statement, and the record it covers is Shown or Supplied. A server offering tools for breaking into things, with a perfectly valid signature, gets nothing more than that.

Whether the content is safe is the job of the input safeguards, which run on everything that enters a model call whether or not it carries evidence. Tool evidence attests origin and integrity relative to an issuer; it never certifies content as acceptable or an issuer as acceptable. The output of an unfiltered model behind an MCP server enters the next model call as client-supplied content and is screened as such. The one place where evidence and safeguards meet is the case from the earlier article: when the executor is the service itself, its own safeguards ran at execution time, and restoring the record restores a result it has already screened. What ran through the service is restored; what ran past it is new input.

Which tools the agent may call is authority, not standing: tool allow-lists, call policies, mandates. A returned record of a call to a forbidden tool is a record; whether the agent could have made that call, and whether it may make the next one, is decided by the environment it is running in now. That layer is specified elsewhere and is not touched here.
