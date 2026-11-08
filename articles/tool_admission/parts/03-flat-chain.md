## Checking the evidence

When the thread returns, the service verifies the model and tool statements, then compares what they say about the call. The model statement covers the arguments with which the model requested the tool and the result sent to its next call. The tool statement covers the arguments the executor received and the result it returned.

Suppose `python export.py` failed with a database connection error and exit code `1`. The executor recorded that result in its statement. Before the result reached the model, it was changed to a success message with exit code `0`. The model continued as if the export had succeeded.

When the service checks the thread, it finds different results in the statements:

```text
Executor returned:    exit code 1, database connection error
Model received:       exit code 0, Wrote export.csv (128 rows).
```

Both statements can pass signature verification: the executor signed the result it returned, and the proxy signed the result sent to the model. By comparing them, the service detects the mismatch.

The service also compares the arguments requested by the model with those received by the executor. The issuers do not need to know about each other's statements: the service verifies each in its own format and compares the values they cover.

### Comparing arguments

Our tool profile records hashes of both the argument string and the parsed object in [JCS](https://www.rfc-editor.org/rfc/rfc8785) canonical form. For example:

```text
arguments:    {"cmd":"python export.py","workdir":"/workspace"}
raw_sha256:   f272be5ff717e09cbabf10f946c667892bd94b0f5bbe36cac5e491de0eea642f
jcs_sha256:   f272be5ff717e09cbabf10f946c667892bd94b0f5bbe36cac5e491de0eea642f
```

The string is already canonical, so the hashes match. Adding spaces changes the raw hash while the canonical hash stays the same:

```text
arguments:    { "cmd": "python export.py", "workdir": "/workspace" }
raw_sha256:   d311518038a03519783d990a9720c7865a4ee70287244ceaf49dd0b3dee2e556
jcs_sha256:   f272be5ff717e09cbabf10f946c667892bd94b0f5bbe36cac5e491de0eea642f
```

The raw hash lets the service check the original string; the canonical hash lets it compare parsed objects despite formatting differences. Our profile requires both, so an executor using it must receive the original string. An executor that receives only a parsed object can issue evidence in another format; the service then uses a comparison supported by that evidence.

Results also need a shared representation. If the executor hashes the result string sent to the model, the service can compare it with the string covered by model evidence. If the runtime transforms or truncates the result, the comparison needs to account for that transformation. We return to truncation in the admission rules.

### Identifying the execution

The service can use `call_id` to find statements to compare. Matching arguments and results show that the covered values agree. To establish that the statements concern the same execution, the service also needs a binding it accepts between the model's request and that execution. Two separate calls can have the same ID, arguments and result, and a runtime can relay an ID. Our hashes alone do not establish that binding. How to establish it remains open for this profile.

The next section uses these checks to decide what the service can retain as history and how it can use the result.
