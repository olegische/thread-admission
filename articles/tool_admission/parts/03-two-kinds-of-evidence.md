## Two kinds of evidence

The earlier article defined one kind of evidence: a statement by the inference proxy about one completed model call, covering the ordered input the model received and the output it produced. Call it model evidence. Tool admission needs a second kind with a different issuer and a different coverage.

| | Model evidence | Tool evidence |
|---|---|---|
| Issuer | the inference proxy | the executor: an MCP server, a host-side tool handler, the owner of the domain |
| What it attests | this input was presented, this output was returned, for this `response_id` | this request was received, this operation ran, this result was returned |
| The tool result in it | an input item with the tool role: "the model was shown this" | the subject of the statement: "the tool produced this" |
| What it does not attest | that the result is genuine | that the model ever saw it |
| Binding | `call_id`, position in the input | `call_id`, digest of the arguments, digest of the result |
| Format | SD-JWT, the earlier article's profile | SD-JWT on the same scheme; DSSE where no selective disclosure is needed |

### The issuer is whoever executed

SEP-2828 argued that the server, not the client, must sign the execution record because the client does not own the logic that decided or the result that came back. Taken to the receiving side, the argument fixes the issuer of tool evidence: the party that executed is the only one that knows what executed. A transport carries the statement. It does not produce it.

Consider a composite MCP server that offers one tool and fulfils it by calling three backends of its own. The server signs what it observed: it received these arguments and returned this result. The backends sign nothing and are under no obligation to. If the server wishes, it may include digests of the backends' responses inside its own statement as references; nobody requires it. The server's statement establishes that the server returned this, not that any backend did anything. For the receiving service that is enough to assign standing at the level "a result of tool X", where X is this server and nothing behind it.

### The source class, and who reads it

A tool's statement carries a claim the executor makes about itself: `source_class`, one of `observer`, `computation` or `generator`. It says how the result was obtained: read from something outside the executor, computed by a procedure the executor can name, or produced by a generative process. The three values are the shape of the IFRS 13 hierarchy, observable input, derived input, model input, and the claim follows the pattern of `amr` and of Vectors of Trust: the issuer states the method, the vocabulary is defined by a framework the statement names, a consumer applies its own policy, and an absent claim is no claim rather than a good one.

Who reads it matters more than what it says. The agent does not. The model does not; the class is not in any prompt. It is read by the control plane, in two decisions: whether an action may be grounded on this result, and whether a tool of this class may be called at all in this context. That is control-level work, done before reasoning, on a typed input. The tool runtime used in the experiment already treats the class this way: it is descriptive metadata the runtime records and refuses to interpret as permission.

The executor's declaration is an input to that policy, not its source. A control plane may keep its own table of classes by tool identity, and where the two disagree the control plane's table wins; an executor that declares itself an observer while generating text is a lying issuer, which is the second item in the limits section with a different field. The class is in the statement so that the policy has something to consume, not because the statement gets to set the policy.

This answers a question that the signing discussion leaves open. Put a language model behind an MCP server and sign its output. The signature is valid. The executor observed its own request and its own result. What the receiving service may believe is that this server returned this text, and `source_class: generator` says what kind of text it is: a proposition the server produced, not an observation of anything. Admission restores the record with that class. A control-plane policy that requires an observation before an action will not accept it as grounds. Without the signed class, this case is indistinguishable from a sensor reading, and the signature would have done the laundering on the tool's behalf. The MCP threads introduced exactly this kind of label for the fields of their envelope, declared versus derived; this article applies it to the tool itself.

### Standing classes for a tool record

A receiving service assigns each tool record one of five standings. The vocabulary is plain on purpose.

- **Principal-signed.** The record was signed by the user's own key. It is the user's statement and is admitted as such.
- **Restored.** Covered by both kinds of evidence with the link checks of the next section passing. Admitted as prior history.
- **Produced.** Covered by tool evidence only. The executor confirmed it produced this result; whether the model saw it is unknown.
- **Shown.** Covered by model evidence only. The model was shown this result; who produced it is unknown. This is the common case and it is the standing of supplied content.
- **Supplied.** No coverage. New input.

A result that the model was shown but no executor vouched for stays at **Shown** no matter how many model calls it appeared in. Repetition inside the thread is not corroboration.

### How the statement is typed, and what it carries

The statement should not invent its own way of saying what it is. [RFC 7519](https://www.rfc-editor.org/rfc/rfc7519) allows three kinds of claim names: registered with IANA, public names that embed a collision-resistant namespace, and private names agreed between producer and consumer, which the RFC marks as "subject to collision". The SD-JWT VC profile, [draft-ietf-oauth-sd-jwt-vc](https://datatracker.ietf.org/doc/draft-ietf-oauth-sd-jwt-vc/), gives private names a safe scope: the header `typ` is `dc+sd-jwt`, a required claim `vct` names the statement type by a collision-resistant URI, and a Type Metadata document at that URI lists the claims with their paths, whether they are mandatory and whether they may be selectively disclosed. A verifier that cannot retrieve required metadata rejects the statement. Private claim names are then interpreted only under their `vct`, which is what makes them usable.

This article defines two types, one for the tool statement and one for the earlier article's inference-call statement, which moves from a custom `typ` to the same scheme:

| Layer | Claims | Status |
|---|---|---|
| Typing | `vct` naming `…/tool-call/v1` or `…/inference-call/v1`; Type Metadata at that URI; `vct#integrity` | SD-JWT VC |
| Registered, used as registered | `iss`, `sub`, `iat`; `cnf` for the holder's key binding; `status` for revocation; `jti` where uniqueness is needed | IANA JWT Claims registry |
| Candidate for reuse | `txn` (RFC 8417, transaction identifier) as the identifier shared by all statements about one operation | open; `call_id` stays separate as the model's relayed identifier |
| Private under `vct` | `source_class`, `tool_id`, `call_id`, `outcome`, `arguments`, `result`; for inference-call, `response_id`, `request`, `response` | not registered by anyone as of this writing; registration deferred |
| Not borrowed | `amr`, `acr`, `vot`, `vtm`, `events`, `attest` | registered with other meanings |

The open, signed claims of a tool statement: `iss` (the executor), `sub` (the account on whose behalf it ran), `iat`, `call_id`, `tool_id` (a stable identity such as `namespace.name@version`), `source_class`, `tool_kind` (`read`, `write`, `think` or `generic`), and `outcome`, one of `executed`, `refused` or `errored`. The selectively disclosable claims: the arguments as two digests (next section), and the result, at a granularity the executor chooses (section on granularity). The vocabulary of `source_class` is fixed by the JSON Schema the Type Metadata points to; a verifier rejects a value it does not know.

The schema below describes the claims after disclosure. It is a proposed profile; its reference implementation is the subject of the experiment section and is not yet published.

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "type": "object",
  "required": ["vct", "iss", "sub", "iat", "call_id", "tool_id",
               "source_class", "tool_kind", "outcome", "arguments"],
  "properties": {
    "vct": {"type": "string"},
    "iss": {"type": "string"},
    "sub": {"type": "string"},
    "iat": {"type": "integer", "minimum": 0},
    "call_id": {"type": "string"},
    "tool_id": {"type": "string"},
    "source_class": {"enum": ["observer", "computation", "generator"]},
    "tool_kind": {"enum": ["read", "write", "think", "generic"]},
    "outcome": {"enum": ["executed", "refused", "errored"]},
    "arguments": {
      "type": "object",
      "required": ["raw_sha256", "jcs_sha256"],
      "properties": {
        "raw_sha256": {"type": "string", "pattern": "^[0-9a-f]{64}$"},
        "jcs_sha256": {"type": "string", "pattern": "^[0-9a-f]{64}$"}
      },
      "additionalProperties": false
    },
    "result": {
      "type": "object",
      "required": ["sha256", "length"],
      "properties": {
        "sha256": {"type": "string", "pattern": "^[0-9a-f]{64}$"},
        "length": {"type": "integer", "minimum": 0},
        "parts": {"type": "object", "additionalProperties": {"type": "string"}}
      },
      "additionalProperties": false
    }
  },
  "additionalProperties": false
}
```

`result` is absent when `outcome` is `refused` or `errored` without a body; `parts` holds the executor's own disclosable subdivision of the result and is opaque to the profile. `cnf` and `status` are omitted from the schema because they belong to the holder and to revocation, which are not this article's subject; the profile uses them as registered.
