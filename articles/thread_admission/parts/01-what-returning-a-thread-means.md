## First, separate a conversation from a record of execution

A thread usually mixes several kinds of information: user requests, generated answers, tool invocations, tool results, and references to files. They share a container, but they do not establish the same things.

For a concrete example, Codex App Server represents a turn's history as typed `ThreadItem` records. Below is a shortened `items` array for a request to run an export script. The types and field names come from Codex's protocol; the command and output are illustrative. Optional metadata is omitted.

```json
[
  {
    "type": "userMessage",
    "id": "msg-1",
    "content": [
      {"type": "text", "text": "Run export.py to create the customer export."}
    ]
  },
  {
    "type": "commandExecution",
    "id": "exec-1",
    "command": "python export.py",
    "cwd": "/workspace",
    "source": "agent",
    "status": "completed",
    "commandActions": [
      {"type": "unknown", "command": "python export.py"}
    ],
    "aggregatedOutput": "Wrote export.csv (128 rows).\n",
    "exitCode": 0
  },
  {
    "type": "agentMessage",
    "id": "msg-2",
    "text": "Created export.csv with 128 rows."
  }
]
```

In the original session these records arrived through different interfaces. When the application sends the saved thread back, all of these records arrive from client-controlled storage. Someone editing that history can change `exitCode`, replace the assistant's answer, or insert another command result. Valid `ThreadItem` syntax does not tell the receiver whether this is the history it saved.

The scope here is the history itself: its records, order, roles, and call/result links. We do not trace the assistant's claims back to documents, citations, or transformations of source data. Checking that a saved answer is unchanged does not check whether the answer is correct.

### Import should not activate the history

Use two steps in the backend:

- **Import** parses and stores the submitted history. Records of executed commands remain records; permissions for new actions are determined by the current execution environment.
- **Admission** decides whether to resume from the returned history, accept only a verified portion, use the submission as new context, or reject it.

Loading the `commandExecution` item above never reruns `python export.py`. If the agent needs to run it again, the receiving environment applies its current execution policy. Its permissions, approval decisions, and audit log belong to that environment.

Four return paths exercise different parts of this contract:

- **The original saved revision.** The receiver checks that its records match the saved revision.
- **That revision plus local work.** The receiver identifies where the verified history ends and whether the additions have separate verification coverage.
- **A conversion to another format.** The receiver establishes which content and relationships the conversion preserved.
- **A summary.** The receiver decides whether to accept it as new context and establishes which original records remain available.

None requires assuming the user is malicious. A runtime can regenerate IDs, omit a field it does not understand, or replace a long tool result with a summary. Treating these as supported transformations means specifying their effects, rather than deciding that similar-looking text is probably the same history.

The backend's question is therefore quite concrete: **which parts of the returned history can be restored as prior history, and which must enter as new input?** A single `trusted: true` flag on the entire conversation cannot answer it.

### Approvals and audit belong to the execution environment

An audit trail records who requested or approved an operation, when, what was executed, and the outcome. These records are separate from the conversation. In the Codex implementation examined here, approval decisions are emitted as `codex.tool_decision` events through OpenTelemetry logs when log export is configured; trace export alone does not export them. App Server handles approvals through separate RPC requests and responses. Returned thread items contain neither that audit trail nor references to its records.

Audit collection, protection, retention, and subsequent verification remain outside this article's scope. They belong to established log-management and audit practices, described in NIST SP 800-92 and the Audit and Accountability controls of SP 800-53. Thread transfer does not restore approvals or permissions. [NIST SP 800-92](https://csrc.nist.gov/pubs/sp/800/92/final), [NIST SP 800-53, AU controls](https://csrc.nist.gov/CSRC/media/Projects/risk-management/800-53%20Downloads/800-53r5/SP_800-53_v5_1-derived-OSCAL.pdf)
