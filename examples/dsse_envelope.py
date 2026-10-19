"""Executable example from article/parts/06-portable-verification.md."""

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
