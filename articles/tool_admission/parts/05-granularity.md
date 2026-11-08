## From the tool result to the model

An MCP tool can return text and structured data in one result. For example:

```json
{
  "content": [
    {"type": "text", "text": "{\"temperature\":22.5}"}
  ],
  "structuredContent": {"temperature": 22.5}
}
```

The executor signs a statement containing a hash of this complete result. The runtime might select the text block and send that text to the model:

```text
{"temperature":22.5}
```

The proxy's evidence covers the string sent to the model. To compare it with the result covered by the executor, the receiving service needs the full result and a rule for the conversion. In this example, the rule takes the text from the single `content` block. The service checks the full result against the executor's hash, applies the rule and compares its output with the string in the proxy's evidence. The executor's statement also covers `structuredContent`; this rule sends the text block to the model.

The service must know and accept the rule. A runtime can transform a result in many ways; a rule that produces a matching string still needs to be suitable for the service's policy. For example, the service must consider how a rule handles errors before accepting it. The same approach can cover truncation when the rule and the full result allow the service to reproduce the text shown to the model.

Our experiment defines one such rule for an MCP result with a single text block. For a tool error, the rule adds an explicit error prefix to the text. It checks the complete signed result and repeats the conversion. Other result shapes and conversions need their own accepted rules.
