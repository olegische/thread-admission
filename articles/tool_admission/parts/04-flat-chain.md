## A flat chain

With two kinds of evidence, a session is an alternation:

```text
tool evidence   (result R1 was produced)
  → model evidence (R1 was shown; function call F2 was issued)
  → tool evidence  (F2 was executed; result R2 was produced)
  → model evidence (R2 was shown; the answer was issued)
```

Each link covers its own half. The links are checked against their neighbours, not against a plan above them. Two checks connect a tool statement to the model statements on either side of it:

- the digest of the result in the tool statement equals the digest of the tool-role item in the input of the next model call;
- the arguments in the function call issued by the previous model call equal the arguments in the tool statement.

Without one of the two kinds, the chain is a set of unrelated signatures. With both, each link vouches for the other's edge. There is no envelope over the plan, no issuer above the planner, and no notary. The MCP threads needed a three-block envelope because in their design one issuer signs other parties' claims; when every party signs only what it observed, the blocks collapse.

### Observed and relayed

One distinction between fields survives the collapse. A statement carries what its signer observed, and it may carry identifiers it received from elsewhere: the `call_id` that the model assigned to the function call, a turn identifier from the runtime. Those are relayed, and a verifier treats a join on a relayed identifier as weak. A join on digests of arguments and results is strong. This is the same difference as between a trace header, which anyone can set, and a signed transaction token, which only its issuer could have made.

### Two digests of the arguments

The model emits `arguments` as a string. The executor receives an object. A tool statement therefore carries two digests: one of the raw string as the executor received it, one of the JCS canonical form of the parsed object. The first is the digest compared with model evidence. The second is the digest of what the executor actually used. For the example call,

```text
arguments as emitted:   {"cmd":"python export.py","workdir":"/workspace"}
raw_sha256:   f272be5ff717e09cbabf10f946c667892bd94b0f5bbe36cac5e491de0eea642f
jcs_sha256:   f272be5ff717e09cbabf10f946c667892bd94b0f5bbe36cac5e491de0eea642f
```

The two coincide because the model happened to emit canonical JSON. Insert one space after each colon and the raw digest becomes `a03adda5…`, while the JCS digest is unchanged. A verifier that compared only canonical forms would miss a runtime that rewrote the string; one that compared only raw strings would fail on an executor that re-serialized. Both digests, both comparisons. This is the problem SEP-2787 addressed with a three-way argument projection and in-toto addresses with a resource descriptor that carries a digest and, optionally, content. The rule here is the smallest one that works: the raw digest is the link, the canonical digest is the executor's commitment to what it ran.

In Python, with `rfc8785` for canonicalization:

```python
from hashlib import sha256
import json
import rfc8785


def argument_digests(raw_arguments):
    parsed = json.loads(raw_arguments)
    return {
        "raw_sha256": sha256(raw_arguments.encode("utf-8")).hexdigest(),
        "jcs_sha256": sha256(rfc8785.dumps(parsed)).hexdigest(),
    }


def link_checks(previous_model, tool, next_model):
    """Compare one tool statement with its neighbouring model statements."""
    call = next(item for item in previous_model["response"]
                if item["type"] == "function_call" and item["call_id"] == tool["call_id"])
    shown = next(item for item in next_model["request"]
                 if item["type"] == "function_call_output" and item["call_id"] == tool["call_id"])
    return {
        "arguments": sha256(call["arguments"].encode("utf-8")).hexdigest()
                     == tool["arguments"]["raw_sha256"],
        "result": sha256(shown["output"].encode("utf-8")).hexdigest()
                  == tool["result"]["sha256"],
    }
```

`previous_model` and `next_model` are the verified claim sets of the earlier article's profile; `tool` is the verified claim set of the schema above. The function returns two booleans and makes no decision; admission does that.

### Who links the links

The association between a call and its position in a thread lives in the runtime and is protected by nothing. The holder of the thread, the user's storage or the service that saves it, fixes the order when it saves. Issuers sign only their own link. This keeps the executor out of any obligation to know about threads, which it does not and should not.

### A rule for issuers, not for verifiers

The SEP-2817 discussion insisted that bound values be recomputed immediately before execution, because every field can be bound correctly while the record describes an action that never happened. That is a rule for the executor: the digests in a tool statement must be of the arguments it actually passed to its handler and the result the handler actually returned, computed at that moment. It is complete mediation restated for tool calls. The receiving service cannot enforce it and does not try; it relies on the executor's signature meaning what the executor says it means, which is the first limit in the limits section.
