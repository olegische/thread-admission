## Two kinds of evidence

In the previous article, we used evidence from the proxy to check what the model received and returned. We now add **tool evidence**: a statement by the executor about the call it received and the result it returned. Related records are described in [SEP-2828](https://github.com/modelcontextprotocol/modelcontextprotocol/pull/2828) and the [Agent Execution Evidence draft](https://datatracker.ietf.org/doc/draft-thaha-scitt-agent-execution-evidence/01/).

### A statement about the export

For the `python export.py` call from the opening, the executor could issue a statement containing these claims:

```text
issuer:       the tool executor
call:         call-1
model call:   reference to the proxy's model-call evidence
arguments:    hash of {"cmd":"python export.py","workdir":"/workspace"}
outcome:      executed
source class: computation
result:       hash of {"content":[{"type":"text","text":"Wrote export.csv (128 rows).\n"}],
                       "structuredContent":{"exitCode":0}}
```

The executor signs these claims and makes the statement available with the thread. The reference identifies the proxy's evidence presented with the request. In this example the executor declares that the output was computed, and the receiving service decides whether to accept that claim. A signature identifies the issuer, who can also sign a false account. A transparency log makes that statement durable and attributable. The [tool evidence profile](06-tool-statement.md) specifies the full statement and its schema.

When the thread returns, the service checks signatures from issuers it accepts and compares the evidence: did the executor receive the arguments requested by the model, and was the result the executor reported sent to the model? A mismatch tells it that the values covered by the statements differ. We will work through these checks in the next section.

The executor can attest to what it observed. Checking the work of its backends requires evidence from those parties. The `source_class` claim describes how the executor obtained the result. The service uses that claim in its policy and may set its own class for a tool.

Depending on the evidence available, the service reaches four outcomes:

- **Restored:** both statements are available and their links pass, so the record is restored as prior history.
- **Produced:** the executor reported the result, and whether the model saw it is unknown.
- **Shown:** the result was sent to the model, and its producer is not established.
- **Supplied:** no evidence is available, so the record remains supplied context.

Our example uses [SD-JWT](https://www.rfc-editor.org/rfc/rfc9901) for the tool statement, allowing the holder to disclose selected claims. Other issuers can use their own formats. Each statement is checked according to its format.
