"""Executable example from article/parts/05-verify-api-requests-and-responses.md."""

from hashlib import sha256


import rfc8785


def item_hash(item):
    return sha256(rfc8785.dumps(item)).hexdigest()


def record_call(subject, response_id, input_items, output_items):
    return {
        "sub": subject,
        "response_id": response_id,
        "request": [item_hash(item) for item in input_items],
        "response": [item_hash(item) for item in output_items],
    }


def verify_call(input_items, output_items, evidence, subject, response_id):
    if (evidence["sub"], evidence["response_id"]) != (subject, response_id):
        raise ValueError("Wrong API subject or response")
    candidate = record_call(subject, response_id, input_items, output_items)
    if candidate != evidence:
        raise ValueError("Input or output differs from the observed call")
    return {"request": input_items, "response": output_items}
