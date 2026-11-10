## The tool evidence profile

For our profile we use [SD-JWT](https://www.rfc-editor.org/rfc/rfc9901), so the holder can disclose selected claims. A complete statement can also be carried in a DSSE envelope when selective disclosure is not needed.

The [SD-JWT VC draft](https://datatracker.ietf.org/doc/draft-ietf-oauth-sd-jwt-vc/) defines `typ: dc+sd-jwt` and a `vct` claim that identifies the credential type. Our example uses `https://thread-admission.example/tool-call/v1` for the tool statement and checks this value against a constant. The profile provides for Type Metadata to describe its claims, including which are required and which may be selectively disclosed; `vct#integrity` can protect the referenced document. Model-call evidence keeps its own issuer and format.

The tool statement includes:

- **Issuer and call:** `iss`, `sub`, `iat`, `call_id` and `tool_id`. These identify the executor, the account on whose behalf it ran, the time, the call and the tool.
- **Origin and execution:** optional `model_call` references the proxy's signed model-call evidence. Optional `caller_id` records the client identity authenticated by the executor; `client_stated_purpose` records an explanation provided by that client.
- **Outcome and method:** `outcome` and `source_class`. The outcome is `executed`, `refused`, `errored` or `cancelled`.
- **Arguments and result:** digests of the arguments and result, with the result's byte length. These can be selectively disclosed. The evidence-checking section explains why the arguments have two digests.

Claims such as `iss`, `sub` and `iat` have registered meanings. The tool-specific names, including `source_class`, `tool_id`, `call_id`, `outcome`, `arguments` and `result`, are defined by our profile and interpreted under the statement's `vct`. For a linked call, the issuer, model-evidence digest and `call_id` identify the execution under the replay rule. The schema can be extended with `txn` for a transaction identifier, `cnf` for holder key binding, `status` for revocation and `jti` to identify the statement. `call_id` remains the identifier relayed from the model. We do not use the registered names `amr`, `acr`, `vot`, `vtm`, `events` or `attest` for these values.

The `model_call` field is optional, so an executor can issue a statement without a model link. For Restored, the service needs that link, the model evidence and the result checks. `client_stated_purpose` carries the client's explanation, and `caller_id` is included when the executor has authenticated the client; authorization is decided separately.

The schema below is for full-result verification. It requires a digest and length for every terminal outcome, including refusal, error, confirmed cancellation and empty output. The executor attests to a cancellation it observed; the client records a timeout or cancellation request it observed. A presentation without result disclosure, for example for audit, needs separate validation rules. The [example implementation](../../../examples/run_tool.py) is in the companion repository.

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "type": "object",
  "required": ["vct", "iss", "sub", "iat", "call_id", "tool_id",
               "source_class", "outcome", "arguments", "result"],
  "properties": {
    "vct": {"type": "string"},
    "iss": {"type": "string"},
    "sub": {"type": "string"},
    "iat": {"type": "integer", "minimum": 0},
    "call_id": {"type": "string"},
    "tool_id": {"type": "string"},
    "source_class": {"enum": ["observer", "computation", "generator"]},
    "outcome": {"enum": ["executed", "refused", "errored", "cancelled"]},
    "model_call": {
      "type": "object",
      "required": ["issuer_jwt_sha256"],
      "properties": {
        "issuer_jwt_sha256": {"type": "string", "pattern": "^[0-9a-f]{64}$"}
      },
      "additionalProperties": false
    },
    "caller_id": {"type": "string", "minLength": 1},
    "client_stated_purpose": {"type": "string"},
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
        "length": {"type": "integer", "minimum": 0}
      },
      "additionalProperties": false
    }
  },
  "additionalProperties": false
}
```

The `result` field carries the digest and length of the complete `CallToolResult` encoded in JCS. A tool error carries `isError` in that result. The example issues statements for successful results and errors. `cnf` and `status` are omitted from this schema; they concern holder binding and revocation.

### Linking the model call and tool result

For the MCP example, `result.sha256` and `result.length` cover the UTF-8 bytes of the complete `CallToolResult` encoded in JCS, including `content` and `structuredContent` when present. The holder keeps the full result for the receiver to check. The statement travels separately; it and the JSON-RPC wrapper are outside the hashed object.

To link the execution to the model call, the client presents the proxy's evidence, disclosing the tool name and arguments from one `function_call`. The verifier in the first article required every field to be disclosed. Here the selective presentation is checked against a schema in which selectively disclosable fields are optional; the executor separately requires the tool name and arguments so it can compare them with the request.

The signed JWT still exposes metadata to the executor, including the issuer, subject, response ID, item types and call IDs.

The reference is the SHA-256 digest of the exact UTF-8 bytes of the issuer-signed compact JWT, excluding disclosures and key binding, so it stays stable across different presentations. For another evidence format, the profile needs to define which signed bytes to hash. The signature and disclosed claims are verified separately.

For example, a client can send the evidence with an MCP request using an application-defined `_meta` key:

```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "tools/call",
  "params": {
    "name": "run_command",
    "arguments": {"cmd": "python export.py", "workdir": "/workspace"},
    "_meta": {
      "org.example/model_evidence": "<signed-jwt>~<tool-name-disclosure>~<arguments-disclosure>~"
    }
  }
}
```

After checking the evidence and processing the call, the executor includes a reference to the signed JWT in its own statement. This is the relevant part of its claims before signing:

```json
{
  "call_id": "call-1",
  "model_call": {
    "issuer_jwt_sha256": "<sha256-of-signed-jwt>"
  }
}
```

The client can later present the receiver with the same signed JWT and an additional disclosure:

```json
{
  "model_evidence": "<signed-jwt>~<tool-name-disclosure>~<arguments-disclosure>~<additional-disclosure>~",
  "tool_evidence": "<signed-tool-statement>"
}
```

The values in angle brackets stand for the encoded JWT, disclosures, hash and tool statement. The receiver hashes the signed JWT and compares it with `issuer_jwt_sha256`. Both presentations refer to the same signed JWT, so the additional disclosure does not change that hash. The `_meta` key and the receiver's JSON wrapper illustrate application choices; the code example does not exercise them.
