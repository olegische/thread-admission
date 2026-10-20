# The User Stores the Agent Thread. What Happens When It Comes Back?

*A practical look at saved conversations, integrity checks, local execution, and the limits of resume.*

Suppose you are building a cloud service for an AI assistant. You want users to keep their conversation history in storage they control. Your service processes a thread during a session, then returns it without keeping a complete transcript between sessions.

The user comes back tomorrow, uploads the saved thread, and clicks **Continue**.

What should your backend do with it?

The obvious implementation parses the messages and sends them to the model. It restores `user`, `assistant`, and `tool` records, reconstructs call IDs, and resumes the loop. That gets the conversation moving. It also lets the uploaded file tell the service who said what, which tools ran, and what results they returned.

All of those fields are now supplied by the client. Even if the user changed nothing, the service needs a way to distinguish its own earlier records from a convincing replacement.

The problem becomes more visible when the user continues locally before returning:

```text
cloud service → saved thread → local agent → saved thread → cloud service
```

The local agent might use the same protocol. It might even call the same model provider. That still leaves several questions: which records match earlier API requests and responses, which were added on the device, and what survived export or compaction?

This article works through that engineering problem. We will compare three ways to continue: summarize the returned history, restore a verified prefix and summarize the rest, or verify the history against records collected during model calls as the thread runs. A snapshot and a small server-side catalog give us the starting point. {==The structures below are proposed examples, not a report of a deployed system or benchmark.==}{>>Unnecessary caveat. We do not need defensive wording.<<>>}

The operating condition matters: the receiving service may have neither the original transcript nor access to the files and external systems used during earlier work. We cannot assume a shared repository will let it reconstruct everything.
