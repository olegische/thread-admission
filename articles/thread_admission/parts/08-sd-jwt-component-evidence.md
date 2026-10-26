## Issue and disclose model-call evidence with SD-JWT

The previous section identified the evidence we need: one completed call's input and output, accessible by response ID and comparable with selected values in a runtime export. SD-JWT, Selective Disclosure for JSON Web Tokens, supplies a signed format with salted disclosures. The thread-to-call association remains the runtime's responsibility. [RFC 9901](https://www.rfc-editor.org/rfc/rfc9901.html#section-3.1)

### Choose the claims and their disclosure policy

This application profile records the issuer (`iss`), authenticated API account (`sub`), issuance time (`iat`), response ID, and ordered `request` and `response` arrays. The arrays represent the complete input and completed output of that call. They do not contain only new items: the second call repeats the user message and function call in its input.

Keep that call context and the item types, roles, and call IDs open and signed. Make message `text`, function `name` and `arguments`, and result `output` disclosable. The example uses an opaque API-account reference. Sensitive bindings can also be made disclosable if required before their corresponding checks. These are application choices; SD-JWT defines the protection and disclosure format.

A role in `request` describes context submitted by the client. It does not assert that the proxy generated that historical item. Array position and request/response membership remain protected by the containing signed structure. The runtime's thread identity is outside this evidence.

The following JSON Schema describes the required claims after disclosure. Arguments and results remain opaque API strings; the proxy does not interpret individual tools.

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "type": "object",
  "required": [
    "iss",
    "sub",
    "iat",
    "response_id",
    "request",
    "response"
  ],
  "properties": {
    "iss": {
      "type": "string"
    },
    "sub": {
      "type": "string"
    },
    "iat": {
      "type": "integer",
      "minimum": 0
    },
    "response_id": {
      "type": "string"
    },
    "request": {
      "type": "array",
      "items": {
        "$ref": "#/$defs/observation"
      }
    },
    "response": {
      "type": "array",
      "minItems": 1,
      "items": {
        "$ref": "#/$defs/observation"
      }
    }
  },
  "additionalProperties": false,
  "$defs": {
    "observation": {
      "oneOf": [
        {
          "type": "object",
          "required": [
            "type",
            "role",
            "text"
          ],
          "properties": {
            "type": {
              "const": "message"
            },
            "role": {
              "enum": [
                "user",
                "assistant"
              ]
            },
            "text": {
              "type": "string"
            }
          },
          "additionalProperties": false
        },
        {
          "type": "object",
          "required": [
            "type",
            "call_id",
            "name",
            "arguments"
          ],
          "properties": {
            "type": {
              "const": "function_call"
            },
            "call_id": {
              "type": "string"
            },
            "name": {
              "type": "string"
            },
            "arguments": {
              "type": "string"
            }
          },
          "additionalProperties": false
        },
        {
          "type": "object",
          "required": [
            "type",
            "call_id",
            "output"
          ],
          "properties": {
            "type": {
              "const": "function_call_output"
            },
            "call_id": {
              "type": "string"
            },
            "output": {
              "type": "string"
            }
          },
          "additionalProperties": false
        }
      ]
    }
  }
}
```

### Let the library construct and verify disclosures

For each selected object property, the issuer generates a random salt and base64url-encodes the UTF-8 JSON `[salt, claim_name, claim_value]`. The digest of that encoded string goes in the containing object's `_sd` array, replacing the clear property. The issuer signs the resulting JWT and gives the client the JWT and disclosures. The client can later present selected disclosures; the verifier checks the signature and their signed digests and recovers the claims. [RFC 9901, disclosures](https://www.rfc-editor.org/rfc/rfc9901.html#section-4.2)

Use OpenWallet Foundation's reference API rather than implementing disclosure encoding or hashing. This executable example pins `sd-jwt==0.10.4` and uses `jwcrypto` for keys and `jsonschema` for the application schema. The reference release predates the final RFC and has verification limitations described below. This variant uses JWS directly, rather than nesting inside section 6's DSSE envelope. [Python implementation](https://github.com/openwallet-foundation-labs/sd-jwt-python), [pinned release](https://pypi.org/project/sd-jwt/0.10.4/)

### Extract claims at the proxy and issue the package

Install `sd-jwt==0.10.4` and `jsonschema`. `SDObj` marks a property for disclosure. The adapter below extracts selected claims from the proxy's own API contract and leaves API IDs, status, and annotations outside this profile. It supports one text block per message and the two function-related item kinds used in our example.

```python
from time import time
from jwcrypto.jwk import JWK
from sd_jwt.common import SDObj
from sd_jwt.issuer import SDJWTIssuer
from sd_jwt.holder import SDJWTHolder
from sd_jwt.verifier import SDJWTVerifier
from jsonschema import validate

ISSUER = "https://proxy.example"
TOKEN_TYPE = "inference-call-v1+sd-jwt"  # Our application profile.


def observation(item):
    kind = item["type"]
    if kind == "message":
        block, = item["content"]  # This example supports one text block.
        if block["type"] not in ("input_text", "output_text"):
            raise ValueError("Unsupported content block")
        return {"type": kind, "role": item["role"],
                SDObj("text"): block["text"]}
    if kind == "function_call":
        return {"type": kind, "call_id": item["call_id"],
                SDObj("name"): item["name"],
                SDObj("arguments"): item["arguments"]}
    if kind == "function_call_output":
        return {"type": kind, "call_id": item["call_id"],
                SDObj("output"): item["output"]}
    raise ValueError("Unsupported API item")


def issue_call(input_items, output_items, key, subject, response_id):
    claims = {
        "iss": ISSUER, "sub": subject, "iat": int(time()),
        "response_id": response_id,
        "request": [observation(item) for item in input_items],
        "response": [observation(item) for item in output_items],
    }
    issued = SDJWTIssuer(
        claims, key, sign_alg="ES256",
        extra_header_parameters={"typ": TOKEN_TYPE},
    )
    return issued.sd_jwt_issuance
```

Let `user`, `call`, `result`, and `answer` be the same API items used in the earlier example. The call and result are shown in section 5; the answer is shown in section 7. The second call's full input is `[user, call, result]`, and its output is `[answer]`:

```python
key = JWK.generate(kty="EC", crv="P-256")  # Demo; reuse the operator's key.
public_key = JWK.from_json(key.export_public())

client_package = issue_call([user, call, result], [answer], key,
                            "api-account-1", "resp-2")
```

The subject comes from the proxy's authenticated request context, and the response ID is the one exposed to the agent. Input is captured when received; output is assembled from the stream. Issue this completed-call package only after successful completion. Hashing individual deltas is unnecessary.

### Keep disclosures and salts with the client

The package contains the signed JWT and encoded disclosures. **The salt is inside each disclosure.** The client saves the package alongside the thread in storage that survives runtime export.

After delivery, the proxy can discard content and disclosures, including salts. A retained signed JWT contains digests and open context without the hidden values or salts. Keeping salts away from that retained copy prevents offline guessing of short undisclosed values from the digests. The proxy still sees the values during processing. [RFC 9901, salt requirements](https://www.rfc-editor.org/rfc/rfc9901.html#section-9.3)

If retrieval is delayed until the runtime saves its thread, the proxy must retain the ready package until it is retrieved or expires. That package contains the disclosed content. A strict no-content-retention design instead delivers it at call completion and relies on client storage; it cannot later regenerate discarded disclosures from a digest.

For this import, disclose all components required by the example's schema. The holder API preserves the original disclosures and salts:

```python
def present(issuance):
    holder = SDJWTHolder(issuance)
    selected = {"text": True, "name": True, "arguments": True, "output": True}
    holder.create_presentation({
        group: [selected for _ in holder.sd_jwt_payload[group]]
        for group in ("request", "response")
    })
    return holder.sd_jwt_presentation


presentation = present(client_package)
```

Omitting a required disclosure cannot produce successful claim validation. The original complete package can also be returned directly. There is no key-binding JWT here; the receiving service authenticates the caller separately. Possession of evidence does not grant access to another API account's records.

### Verify one call, then extract the returned claims

Pass the schema above as `schema`. The verifier uses a configured trusted key, checks the profile, subject, response ID, and issuance time, and obtains the disclosed claims. No thread identity or cross-call order is inferred:

```python
def verify_call_evidence(presentation, public_key, subject, response_id, schema):
    def issuer_key(issuer, header):
        if (issuer != ISSUER or header.get("alg") != "ES256"
                or header.get("typ") != TOKEN_TYPE):
            raise ValueError("Unaccepted issuer, algorithm, or profile")
        return public_key

    if not presentation.endswith("~"):
        raise ValueError("Expected SD-JWT without key binding")
    verifier = SDJWTVerifier(presentation, issuer_key)
    claims = verifier.get_verified_payload()
    validate(claims, schema)
    if (claims["sub"], claims["response_id"]) != (subject, response_id):
        raise ValueError("Wrong API subject or response")
    if claims["iat"] > time() + 60:
        raise ValueError("Issuance time is in the future")
    return claims
```

The pinned reference release leaves time checks to the application and accepts unreferenced disclosures, which RFC 9901 requires rejecting. This example checks `iat` and the required application claims; it issues no `exp` or `nbf`. These checks do not make the release a fully conforming production verifier. [Python implementation](https://github.com/openwallet-foundation-labs/sd-jwt-python), [RFC 9901, verification](https://www.rfc-editor.org/rfc/rfc9901.html#section-7.1)

Use the App Server transcript from section 1 as `returned`. Its adapter proposes message claims. Compare all such messages with the selected call's authenticated message claims in their order, retaining whether each was observed in request or response:

```python
def returned_message_claims(item):
    if item["type"] == "userMessage":
        block, = item["content"]
        if block["type"] != "text":
            raise ValueError("Unsupported user content")
        return {"type": "message", "role": "user", "text": block["text"]}
    if item["type"] == "agentMessage":
        return {"type": "message", "role": "assistant", "text": item["text"]}
    if item["type"] == "commandExecution":
        return None  # This example compares message claims only.
    raise ValueError("Runtime item outside this example")


def match_text_messages(returned, evidence):
    expected = [
        (group, index, item)
        for group in ("request", "response")
        for index, item in enumerate(evidence[group])
        if item["type"] == "message"
    ]
    actual = []
    for index, item in enumerate(returned):
        candidate = returned_message_claims(item)
        if candidate is not None:
            actual.append((index, candidate))
    if len(actual) != len(expected):
        raise ValueError("Message sequence differs")
    matches = []
    for (group, item_index, authenticated), (index, candidate) in zip(expected, actual):
        if candidate != authenticated:
            raise ValueError("Returned claims differ from the signed claims")
        matches.append({
            "runtime_index": index, "message_type": group, "item_index": item_index,
            "role": authenticated["role"], "text": authenticated["text"],
        })
    return matches


evidence = verify_call_evidence(presentation, public_key,
                               "api-account-1", "resp-2", schema)
matched_messages = match_text_messages(returned, evidence)
```

The matches identify the user message as part of `resp-2`'s request and the final assistant answer as part of its response. Positions refer to those arrays, not a proxy-maintained thread. Returned runtime IDs and other fields are outside this text comparison.

The bundle also authenticates the original function name, arguments, and result as call content. Comparing them with `commandExecution` or MCP records needs an adapter that can extract the selected values from that export. This example leaves the returned tool record uncovered. A neighboring message match cannot cover it; even a tool-result match would not prove execution on the device.

A match supports admission of the covered claims. It does not establish that the chosen call was the latest in an external thread, recover records replaced by a summary, or cover work added afterward. Those are separate conditions of the receiving service's continuation policy.
