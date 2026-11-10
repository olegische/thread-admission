## Checking the evidence

When the thread returns, the service verifies the model and tool statements, then compares what they say about the call. The model statement covers the arguments with which the model requested the tool and the result sent to its next call. The tool statement covers the arguments the executor received and the result it returned.

Suppose `python export.py` failed with a database connection error and exit code `1`. The executor recorded that result in its statement. Before the result reached the model, it was changed to a success message with exit code `0`. The model continued as if the export had succeeded.

When the service checks the thread, it finds different results in the statements:

```text
Executor returned:    exit code 1, database connection error
Model received:       exit code 0, Wrote export.csv (128 rows).
```

Both statements can pass signature verification: the executor signed the result it returned, and the proxy signed the result sent to the model. By comparing them, the service detects the mismatch.

The service also compares the arguments requested by the model with those received by the executor. Each issuer uses its own statement format. The service verifies both and compares the values they cover.

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

The raw hash lets the service check the original string, and the canonical hash lets it compare parsed objects despite formatting differences. Our profile requires both, so an executor using it must receive the original string. An executor that receives only a parsed object can issue evidence in another format. The service then uses a comparison supported by that evidence.

Results also need a shared representation. If the runtime transforms the executor's result before sending it to the model, the service needs to account for that transformation. Section 5 shows how it can repeat a known rule and compare the resulting string with the model evidence.

### Identifying the execution

In our proposed profile, the client sends the proxy's evidence with the tool call, disclosing the tool name and arguments needed for the check. The executor verifies the evidence, checks the requested tool and arguments, and records a reference to the proxy's signed evidence and `call_id` in its own statement.

```text
Proxy evidence:   call-1 and python export.py disclosed from the model call
Tool evidence:    reference to the proxy's evidence, call-1
```

When the thread returns, the service verifies both statements, checks the reference and compares the covered values. The model-evidence issuer does not need to know about the tool statement. A similar link from an execution record to a request attestation was proposed in the [SEP-2817 discussion](https://github.com/modelcontextprotocol/modelcontextprotocol/pull/2817).

Once an executor has issued a statement for a model call, presenting the same evidence and `call_id` again returns that statement without executing the call again. A new tool call in the runtime has a new `call_id` and receives its own statement. The reference records the executor's account of the request it processed. The result comparison establishes what was shown to the model. It cannot trace the physical path taken by identical bytes through the client.

The next section uses these checks to decide what the service can retain as history and how it can use the result.
