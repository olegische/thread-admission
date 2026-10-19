"""Run the article's examples without reading or executing Markdown."""
from copy import deepcopy
from hashlib import sha256

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from jsonschema import validate
from jwcrypto.jwk import JWK
import rfc8785

from call_index import record_call, verify_call
from data import load_json, read_json
from dsse_envelope import sign_dsse, verified_dsse_payload
from prefix import make_checkpoint, split_verified_prefix
from runtime_adapter import match_text_messages
from sdjwt_evidence import issue_call, present, verify_call_evidence
from snapshot import matches_saved_snapshot


def require(condition, message):
    if not condition:
        raise AssertionError(message)


def rejects(action):
    try:
        action()
    except ValueError:
        return
    raise AssertionError("Changed content was accepted")


def main():
    call = load_json("fixtures/api-call.json")
    returned = load_json("fixtures/app-server-transcript.json")
    subject, response_id = call["sub"], call["response_id"]
    input_items, output_items = call["input"], call["output"]

    # Snapshot: recognize saved bytes through the protected catalog.
    saved = rfc8785.dumps(returned)
    entry = {"owner_id": "owner-1", "thread_id": "thread-1", "revision": "r1",
             "sha256": sha256(saved).hexdigest()}
    validate(entry, load_json("schemas/catalog-entry.schema.json"))
    key = (entry["owner_id"], entry["thread_id"], entry["revision"])
    catalog = {key: entry}
    require(matches_saved_snapshot(catalog, *key, saved), "Snapshot did not match")
    require(not matches_saved_snapshot(catalog, *key, saved + b" "), "Changed bytes accepted")
    require(not matches_saved_snapshot(catalog, "other-owner", *key[1:], saved), "Wrong owner accepted")
    print("PASS: snapshot recognition; changed bytes and wrong owner rejected")

    # Prefix: keep original records, return the unverified tail separately.
    checkpoint = make_checkpoint(returned)
    validate(checkpoint, load_json("schemas/checkpoint.schema.json"))
    extra = {"type": "userMessage", "id": "msg-3", "content": [
        {"type": "text", "text": "Continue on the laptop."}]}
    prefix, tail = split_verified_prefix([*returned, extra], checkpoint)
    require(prefix == returned and tail == [extra], "Wrong split")
    changed = deepcopy(returned)
    changed[-1]["text"] = "Changed answer"
    rejects(lambda: split_verified_prefix(changed, checkpoint))
    rejects(lambda: split_verified_prefix(returned[:-1], checkpoint))
    print("PASS: verified prefix; tail remains unverified (no model compaction simulated)")

    # Whole-item evidence: one completed call, not a proxy-managed thread.
    record = record_call(subject, response_id, input_items, output_items)
    schema = load_json("schemas/whole-call.schema.json")
    validate(record, schema)
    verify_call(input_items, output_items, record, subject, response_id)
    rejects(lambda: verify_call(input_items[::-1], output_items, record, subject, response_id))
    print("PASS: complete per-call input/output index; reordered input rejected")

    # Portable whole-item evidence with a real, ephemeral Ed25519 demo key.
    signing_key = Ed25519PrivateKey.generate()
    envelope = sign_dsse(rfc8785.dumps(record), signing_key)
    verified_record = read_json(verified_dsse_payload(envelope, signing_key.public_key()))
    validate(verified_record, schema)
    verify_call(input_items, output_items, verified_record, subject, response_id)
    print("PASS: DSSE signature and whole-item comparison")

    # Selected claims across representations, using the reference SD-JWT API.
    issuer_key = JWK.generate(kty="EC", crv="P-256")
    trusted_key = JWK.from_json(issuer_key.export_public())
    client_package = issue_call(input_items, output_items, issuer_key, subject, response_id)
    presentation = present(client_package)
    evidence = verify_call_evidence(presentation, trusted_key, subject, response_id,
                                    load_json("schemas/component-call.schema.json"))
    matches = match_text_messages(returned, evidence)
    require([(x["runtime_index"], x["message_type"]) for x in matches] == [
        (0, "request"), (2, "response")], "Unexpected message matches")
    changed = deepcopy(returned)
    changed[-1]["text"] += " changed"
    rejects(lambda: match_text_messages(changed, evidence))
    print("PASS: SD-JWT issuance, presentation, verification and runtime message matching")
    print("LIMIT: tool record uncovered; no runtime-thread completeness or latest-call proof")
    print("KNOWN LIBRARY GAP: sd-jwt 0.10.4 accepts unreferenced disclosures")


if __name__ == "__main__":
    main()
