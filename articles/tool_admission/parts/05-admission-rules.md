## Admission rules for tool records

A receiving service classifies each tool record by which evidence covers it and whether the link checks pass. Four cases cover the space.

| Model evidence | Tool evidence | What the service may hold | Admission |
|---|---|---|---|
| present, link passes | present, link passes | the executor produced this result and the model was shown it | **Restored** as prior history |
| present | absent | the model was shown this result; who produced it is unknown | **Shown**: supplied content, retained as the user's account. The normal case |
| absent | present | the executor produced this result; whether the model was shown it, or was shown something else, is unknown | **Produced**: the result stands, its role in the thread does not |
| absent | absent | nothing | **Supplied**: new input |

Two rules sit on top of the table. Import does not activate: a restored record of a command that ran does not run it again, and a restored approval does not approve anything now; the current environment decides what the agent may do next. And a record's standing never rises through repetition: a Shown result that appears in ten model calls is Shown.

### Counterexample one: the exit code

On August 24, 2026, XuebinMa [reported a verifier bug](https://github.com/modelcontextprotocol/modelcontextprotocol/pull/2817#issuecomment-5390870362): "a host-asserted `exit_code: 0` and a runtime-witnessed execution landed in the same total". The fix separated `ExecutionFinished` from `ExecutionReported`. The counterexample below applies that distinction to a returned thread whose tool result was changed.

The user's command failed. The runtime, or the user, rewrote the result before the model saw it. The model was shown a success and answered accordingly. The thread comes back with model evidence intact.

What the executor produced:

```text
Chunk ID: abc123
Wall time: 0.1000 seconds
Process exited with code 1
Output:
Traceback (most recent call last):
  File "export.py", line 12, in <module>
    rows = fetch()
ConnectionError: database unavailable
```

What the model was shown:

```text
Chunk ID: abc123
Wall time: 0.1000 seconds
Process exited with code 0
Output:
Wrote export.csv (128 rows).
```

The model statement's disclosed `output` for `call-1` hashes to `6b3f9753…`. Model evidence verifies: the proxy did see this string in the input, and it signed it. Without tool evidence the record is Shown, which is the correct standing: the service holds that the model was told the command succeeded, and nothing more.

With tool evidence the picture changes. The executor's statement carries `result.sha256` of `5501f22c…` for the failing output. The second link check compares `6b3f9753…` with `5501f22c…` and returns false. Both signatures are valid. Both statements are honest. The record is not Restored, because the two honest statements are about different results, and the service now knows that what the model was shown is not what the tool produced. The comparison detects the mismatch even though both signatures verify.

### Counterexample two: the model behind the server

A tool is an MCP server wrapping a language model. The model call it serves is itself attested by a proxy; the server signs its result; the receiving service's model evidence shows the result was presented. Every signature verifies, every link check passes, and the first row of the table is reached.

Two different actors now make two different decisions. Admission restores the record, with `source_class: generator` attached: the service holds that this server produced this text and that the model saw it. The control plane then applies its policy to the class. A policy that requires an observation before an action, a balance, a file's contents, a sensor's value, rejects this record as grounds, however many signatures it carries. The record stays in the history; it does not license the action. Admission did its job by typing the record; the policy did its job by reading the type. Neither inspects the text, because a custodian can put any text in any record. Without a signed class the two decisions collapse into one, the server's output and a database query's output are the same object with the same signatures, and the signatures have laundered a hypothesis into an observation.

### Two meanings of "unaccounted"

The SEP-2817 discussion found that a verifier status of `unaccounted` meant either "we established that nothing ran" or "the evidence stops here". Admission separates them by what it has in hand. A tool statement with `outcome` of `refused` or `errored` is positive evidence that the executor declined or failed: the executor said so, the service holds it, and a thread that claims the operation succeeded contradicts a signed statement. The refusal is not inert; a consumer reads it. The absence of any tool statement is the second meaning: the thread's account is retained as Shown or Supplied and nothing is established either way. A service that reports "no execution" when it means "no evidence" has made the merged-outcome error in the other direction.

### Honest truncation

Runtimes truncate long tool outputs before showing them to the model. The executor produced ten thousand lines; the model saw the first two hundred and a marker. The second link check, as written, fails. That would turn every long output into a mismatch.

The rule adopted here: the tool statement's `result` carries the digest and the byte length of the full result. If the shown output is shorter than that length and the digest of the full result cannot be compared directly, the verifier compares the shown output with the disclosed result's prefix of the same length and records the link as `truncated` rather than `mismatch` when the prefix matches. A record linked as `truncated` is Restored with that annotation. A shown output that is not a prefix of the produced result is a mismatch regardless of length. This makes the truncation convention explicit instead of leaving it to the runtime, and it depends on the executor disclosing the full result or enough of it, which the granularity section returns to.

### What a `function_call` without a result gets

A function call item with no corresponding output item in the thread is a call that was issued and, as far as the thread shows, never answered. It is covered by model evidence as a model output and is Restored as that: the model issued this call. It is not evidence that anything ran. Admission neither synthesizes an output for it nor treats its absence as a refusal; a runtime that needs an output in place for its own normalization inserts one as supplied content.
