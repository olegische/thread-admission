"""Executable example from article/parts/08-sd-jwt-component-evidence.md."""

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


def present(issuance):
    holder = SDJWTHolder(issuance)
    selected = {"text": True, "name": True, "arguments": True, "output": True}
    holder.create_presentation({
        group: [selected for _ in holder.sd_jwt_payload[group]]
        for group in ("request", "response")
    })
    return holder.sd_jwt_presentation


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
