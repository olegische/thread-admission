## Keep the verification record with the user

Instead of retaining the per-call record only in its index, the proxy can sign it and deliver it to the client. A receiver that trusts the signing key can verify the input and output later without querying that index.

The signature protects the expected hashes when they travel alongside client-held content. DSSE, the Dead Simple Signing Envelope, authenticates a serialized payload and its application-specific type. Our payload describes one observed model call. [DSSE protocol](https://github.com/secure-systems-lab/dsse/blob/master/protocol.md)

### Sign one completed call

Use the record from section 5: API subject, response identifier, ordered hashes of the complete request input, and ordered hashes of the completed output. The subject comes from the proxy's authentication context. It identifies the API account, not ownership of an agent thread.

For `resp-2`, `request` has three hashes: user message, function call, and tool result. `response` has one: the final assistant answer. The hashes preserve positions within each array.

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "type": "object",
  "required": ["sub", "response_id", "request", "response"],
  "properties": {
    "sub": {"type": "string"},
    "response_id": {"type": "string"},
    "request": {"type": "array", "items": {"$ref": "#/$defs/sha256"}},
    "response": {"type": "array", "minItems": 1, "items": {"$ref": "#/$defs/sha256"}}
  },
  "$defs": {
    "sha256": {"type": "string", "pattern": "^[0-9a-f]{64}$"}
  },
  "additionalProperties": false
}
```

These fields are an illustrative application schema, not a DSSE-defined inference protocol. The payload type identifies that schema and the agreed whole-item encoding. Each statement stands on its own. Selecting evidence from several calls does not automatically prove that they belong to one runtime thread.

### Issue and verify the envelope

For a single-signature Ed25519 example, the keys below are objects from Python's `cryptography` package. The receiver gets the trusted public key from configuration.

```python
from base64 import b64decode, b64encode

PAYLOAD_TYPE = "https://example.com/inference-call/v1-json"


def pae(body, payload_type=PAYLOAD_TYPE):
    kind = payload_type.encode("utf-8")
    return b"DSSEv1 %d %s %d %s" % (len(kind), kind, len(body), body)


def sign_dsse(body, signing_key, payload_type=PAYLOAD_TYPE):
    return {
        "payloadType": payload_type,
        "payload": b64encode(body).decode("ascii"),
        "signatures": [{"sig": b64encode(signing_key.sign(pae(body, payload_type))).decode("ascii")}],
    }


def verified_dsse_payload(envelope, trusted_key, payload_type=PAYLOAD_TYPE):
    if envelope["payloadType"] != payload_type:
        raise ValueError("Unsupported statement type")
    body = b64decode(envelope["payload"], altchars=b"-_", validate=True)
    signature = b64decode(envelope["signatures"][0]["sig"], altchars=b"-_", validate=True)
    trusted_key.verify(signature, pae(body, payload_type))
    return body
```

Serialize `record_call(...)` with JCS and pass the bytes to `sign_dsse`. Store the envelope with the represented items. On return, verify its type and signature, parse the exact verified bytes with duplicate-key rejection, and validate the JSON Schema above. Then use `verify_call` from section 5 to compare the submitted arrays with the signed record.

Changing the tool output fails its item hash. Reordering input items fails the ordered-array comparison. Replacing the response identifier or either hash array inside the envelope fails its signature. A valid record for `resp-1` cannot substitute for `resp-2` when the caller requires the latter. Choosing an older valid call does not establish that it was the latest call in an external thread.

The envelope can be issued at response completion and delivered immediately, or retained for authorized retrieval by response ID. This is a proposed proxy capability. It is not a built-in Responses API evidence endpoint.

The next question concerns the object returned by the agent: its own thread transcript may no longer contain the API items in this representation.
