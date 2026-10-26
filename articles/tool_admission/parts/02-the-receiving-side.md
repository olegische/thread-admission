## The receiving side

All three layers live at the moment of the call, between a client and a server. Move the clock forward. The thread has been exported to the user's storage, continued on a laptop, perhaps converted from one runtime's format to another's, and now it comes back to a service that kept no copy. In it is a record like this one, shortened from the Codex App Server format used in the earlier article:

```json
{
  "type": "commandExecution",
  "id": "exec-1",
  "command": "python export.py",
  "cwd": "/workspace",
  "status": "completed",
  "aggregatedOutput": "Wrote export.csv (128 rows).\n",
  "exitCode": 0
}
```

This is text. The earlier article showed what evidence from the inference proxy can establish about it: the proxy signed the full input of the model call that followed, so a verifier can confirm that a tool result with this exit code and this output was in front of the model when it produced its answer. That is a real fact and it is worth having. It is not the fact the record claims. The record claims that a command ran and exited with zero. The proxy's evidence establishes that a string saying so was shown to the model. A result rewritten before it reached the model passes the proxy's check untouched.

That is the bug from SEP-2817 in one sentence. Merging the host's report of an outcome with the runtime's witnessed outcome is exactly treating a tool record as established because model evidence covers it. The channel conferred the status. Nothing in the record earned it.

### Why absence is the normal case

The threads concluded that the party that executed the operation must sign the record of it. The conclusion is logically right and economically empty. The executor pays; the consumer benefits. There is no reason for a weather API, a ticketing system or a payment backend to grow a signing endpoint so that someone else's agent service can later decide what to believe about a thread.

This is not a new situation. Every time a verifying technology has asked established systems to attest to what they did, the same five mechanisms decided whether it happened.

- A consumer with market power set a condition. Mail servers ignored DKIM for a decade; they adopted it when Gmail and Yahoo began rejecting unsigned bulk mail. Certificate authorities logged nothing until Chrome required Certificate Transparency proofs.
- A regulator compelled it. Open Banking under PSD2 forced banks to expose signed, consented APIs they had no commercial interest in.
- The cost of issuing dropped to zero because a layer the system already used did it. Sites did not become HTTPS-ready; Let's Encrypt and the load balancer did. Package authors do not write provenance; the CI platform emits SLSA provenance for every build.
- A witness stood in the path when the executor would not attest. Notaries, clearing houses, timestamp authorities and payment networks certify what they saw pass through them, which is weaker than what the executor did internally and available today.
- The executor gained from it. Signed webhooks from payment and code-hosting providers reduce the provider's own dispute load.

Where none of the five applied, the attestation did not spread. Message disposition notifications for email exist in a standard and are almost never honoured. HTTP message signatures are used where one consumer demands them and nowhere else.

Three consequences follow for a receiving service.

First, the admission rules must be written for a world in which most tool records carry no executor evidence and never will. A record without it is not an error; it is the baseline. It remains the user's account of what happened, it is retained, and the continuation proceeds with it at that standing. What changes is not whether the record is kept but what the control plane may do on its strength: before an action that depends on it, the control plane must require a fresh observation rather than treat the account as one.

Second, admission is itself the first mechanism. A published rule that records with executor evidence are restored as prior history and records without it are retained as supplied context is a condition set by the consumer. An executor whose results matter in continued threads has a reason to sign that it did not have before. The service does not ask backends to become AI-ready. It states what it admits and leaves the choice to them.

Third, for executors that do choose to sign, the cost should be the third mechanism's zero. The record should be emitted by the tool runtime at the point where the handler runs, not by the handler's author. The experiment in this article is built that way.
