"""Execute published per-call evidence examples, including their coverage limits.

Dependencies: sd-jwt==0.10.4, jsonschema, rfc8785.
This is not a full RFC 9901 conformance or live runtime round-trip test.
"""
import ast
from base64 import urlsafe_b64decode, urlsafe_b64encode
from copy import deepcopy
from importlib.metadata import version
import json
from pathlib import Path
import re

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from jwcrypto.jws import JWS
from jsonschema import validate

ROOT = Path(__file__).resolve().parents[1]
PARTS = ROOT / 'parts'


def unique_keys(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError('Duplicate JSON key')
        result[key] = value
    return result


def read_json(text):
    return json.loads(text, object_pairs_hook=unique_keys)


def blocks(name, language):
    return re.findall(rf'```{language}\n(.*?)```', (PARTS / name).read_text(), re.S)


for part in PARTS.glob('*.md'):
    for code in blocks(part.name, 'python'):
        ast.parse(code, filename=str(part))
    for value in blocks(part.name, 'json'):
        read_json(value)

returned = read_json(blocks('01-what-returning-a-thread-means.md', 'json')[0])
call, result = map(read_json, blocks('05-verify-api-requests-and-responses.md', 'json'))
answer = next(read_json(value) for value in blocks('07-metadata-loss-and-compaction.md', 'json')
              if read_json(value).get('type') == 'message')
schema = read_json(blocks('08-sd-jwt-component-evidence.md', 'json')[0])
whole_schema = read_json(blocks('06-portable-verification.md', 'json')[0])
user = {'type': 'message', 'role': 'user', 'content': [
    {'type': 'input_text', 'text': returned[0]['content'][0]['text']}
]}
ns = dict(user=user, call=call, result=result, answer=answer, returned=returned, schema=schema)
for name in ('05-verify-api-requests-and-responses.md', '06-portable-verification.md',
             '08-sd-jwt-component-evidence.md'):
    for code in blocks(name, 'python'):
        exec(compile(code, name, 'exec'), ns)

subject, response_id = 'api-account-1', 'resp-2'
public, presentation = ns['public_key'], ns['presentation']
verify, match = ns['verify_call_evidence'], ns['match_text_messages']
count = 0


def checked(value=presentation, account=subject, response=response_id, key=public):
    return verify(value, key, account, response, schema)


def rejects(label, action):
    global count
    try:
        action()
    except Exception:
        count += 1
        return
    raise AssertionError(f'Unexpected acceptance: {label}')


def decode(value):
    return urlsafe_b64decode(value + '=' * (-len(value) % 4))


def encode(value):
    return urlsafe_b64encode(json.dumps(value).encode()).decode().rstrip('=')


def jwt_claims(value):
    jwt = JWS()
    jwt.deserialize(value.split('~', 1)[0])
    jwt.verify(public)
    return read_json(jwt.payload)


def resign(mutate, typ=None):
    parts = presentation.split('~')
    claims = jwt_claims(presentation)
    mutate(claims)
    jwt = JWS(json.dumps(claims))
    jwt.add_signature(ns['key'], alg='ES256', protected=json.dumps({
        'alg': 'ES256', 'typ': typ or ns['TOKEN_TYPE']}))
    parts[0] = jwt.serialize(compact=True)
    return '~'.join(parts)


evidence = checked()
assert len(evidence['request']) == 3 and len(evidence['response']) == 1
assert evidence['request'][1]['name'] == call['name']
assert evidence['request'][1]['arguments'] == call['arguments']
assert evidence['request'][2]['output'] == result['output']
assert all(key not in evidence for key in ('thread_id', 'offset', 'previous'))
expected_matches = [
    {'runtime_index': 0, 'message_type': 'request', 'item_index': 0,
     'role': 'user', 'text': user['content'][0]['text']},
    {'runtime_index': 2, 'message_type': 'response', 'item_index': 0,
     'role': 'assistant', 'text': answer['content'][0]['text']},
]
assert ns['matched_messages'] == expected_matches
assert checked(ns['client_package']) == evidence

rejects('wrong API account', lambda: checked(account='other-account'))
rejects('wrong response identifier', lambda: checked(response='resp-1'))
rejects('wrong public key', lambda: checked(key=ns['JWK'].generate(kty='EC', crv='P-256')))
rejects('non-key-bound profile with appended key-binding data', lambda: checked(presentation + 'x'))

parts = presentation.split('~')
salts = []
for index in range(1, len(parts) - 1):
    disclosure = read_json(decode(parts[index]))
    salt, field, value = disclosure
    assert len(decode(salt)) == 16
    assert salt not in json.dumps(jwt_claims(presentation))
    salts.append(salt)
    changed = disclosure.copy()
    changed[2] = value + ' changed'
    altered = parts.copy()
    altered[index] = encode(changed)
    rejects(f'changed disclosure: {field}', lambda: checked('~'.join(altered)))
    changed = disclosure.copy()
    changed[0] = encode('another salt')
    altered[index] = encode(changed)
    rejects(f'changed salt: {field}', lambda: checked('~'.join(altered)))
    removed = parts.copy()
    del removed[index]
    rejects(f'missing required disclosure: {field}', lambda: checked('~'.join(removed)))
assert len(salts) == len(set(salts)) == 5
altered = parts.copy()
altered.insert(-1, parts[1])
rejects('duplicate disclosure', lambda: checked('~'.join(altered)))

for field, value in (('sub', 'another-account'), ('response_id', 'other-response')):
    jwt_parts = parts[0].split('.')
    changed = jwt_claims(presentation)
    changed[field] = value
    jwt_parts[1] = encode(changed)
    altered = parts.copy()
    altered[0] = '.'.join(jwt_parts)
    rejects(f'unsigned change: {field}', lambda: checked('~'.join(altered)))
    altered = resign(lambda claims: claims.update({field: value}))
    rejects(f'valid signature but mismatched scope: {field}', lambda: checked(altered))
future = resign(lambda claims: claims.update(iat=int(ns['time']()) + 3600))
rejects('future issuance time', lambda: checked(future))
wrong_type = resign(lambda claims: None, typ='other-profile+sd-jwt')
rejects('wrong profile', lambda: checked(wrong_type))
swapped = parts.copy()
jwt_parts = swapped[0].split('.')
claims = jwt_claims(presentation)
claims['request'].reverse()
jwt_parts[1] = encode(claims)
swapped[0] = '.'.join(jwt_parts)
rejects('unsigned array reordering', lambda: checked('~'.join(swapped)))

# Whole-item evidence uses complete repeated context, with order local to each array.
input_items, output_items = [user, call, result], [answer]
record = ns['record_call'](subject, response_id, input_items, output_items)
validate(record, whole_schema)
assert len(record['request']) == 3
assert ns['verify_call'](input_items, output_items, record, subject, response_id) == {
    'request': input_items, 'response': output_items}
for index, field in ((0, 'content'), (1, 'arguments'), (2, 'output')):
    changed = deepcopy(input_items)
    if field == 'content':
        changed[index][field][0]['text'] += ' changed'
    else:
        changed[index][field] += ' changed'
    rejects(f'whole input item changed: {index}', lambda: ns['verify_call'](
        changed, output_items, record, subject, response_id))
for changed in (list(reversed(input_items)), input_items[:-1], [*input_items, user]):
    rejects('whole input length or order', lambda: ns['verify_call'](
        changed, output_items, record, subject, response_id))
changed_output = deepcopy(output_items)
changed_output[0]['content'][0]['text'] += ' changed'
rejects('whole output changed', lambda: ns['verify_call'](
    input_items, changed_output, record, subject, response_id))
rejects('move request item to output', lambda: ns['verify_call'](
    [user, result], [call, answer], record, subject, response_id))
rejects('whole-call wrong account', lambda: ns['verify_call'](
    input_items, output_items, record, 'other', response_id))

# Real DSSE signatures protect each call independently; there is no predecessor.
key = Ed25519PrivateKey.generate()
body = ns['rfc8785'].dumps(record)
envelope = ns['sign_dsse'](body, key)
verified = read_json(ns['verified_dsse_payload'](envelope, key.public_key()))
validate(verified, whole_schema)
assert ns['verify_call'](input_items, output_items, verified, subject, response_id)
altered_envelope = deepcopy(envelope)
altered_envelope['payloadType'] = 'other-type'
rejects('DSSE type substitution', lambda: ns['verified_dsse_payload'](altered_envelope, key.public_key()))
altered_envelope = deepcopy(envelope)
from base64 import b64encode
altered_record = deepcopy(record)
altered_record['response_id'] = 'other-response'
altered_envelope['payload'] = b64encode(ns['rfc8785'].dumps(altered_record)).decode()
rejects('DSSE payload substitution', lambda: ns['verified_dsse_payload'](altered_envelope, key.public_key()))

# Returned runtime candidates are compared only for covered message claims.
for index in (0, 2):
    changed = deepcopy(returned)
    if index == 0:
        changed[index]['content'][0]['text'] += ' changed'
    else:
        changed[index]['text'] += ' changed'
    rejects('changed returned text', lambda: match(changed, evidence))
rejects('reordered returned messages', lambda: match(list(reversed(returned)), evidence))
rejects('duplicated returned message', lambda: match([*returned, returned[-1]], evidence))
changed = deepcopy(returned)
for item in changed:
    item['id'] = 'regenerated-id'
assert match(changed, evidence) == expected_matches
changed = deepcopy(returned)
changed[1]['aggregatedOutput'] = 'Unverified tool change'
assert match(changed, evidence) == expected_matches

# The proxy does not turn client-supplied assistant history into observed model output.
client_assistant = deepcopy(user)
client_assistant['role'] = 'assistant'
other = ns['issue_call']([client_assistant], [answer], ns['key'], subject, 'resp-3')
other_evidence = checked(ns['present'](other), response='resp-3')
other_runtime = [
    {'type': 'agentMessage', 'text': client_assistant['content'][0]['text']}, returned[-1]]
other_matches = match(other_runtime, other_evidence)
assert other_matches[0]['message_type'] == 'request'
assert other_matches[1]['message_type'] == 'response'

# Another call is valid independently, but cannot stand in for the selected response.
earlier = ns['issue_call']([user], [call], ns['key'], subject, 'resp-1')
earlier_presentation = ns['present'](earlier)
assert checked(earlier_presentation, response='resp-1')['response'][0]['type'] == 'function_call'
rejects('substitute another valid call', lambda: checked(earlier_presentation))

# This known reference-library gap is documented rather than claimed fixed.
extra = parts.copy()
extra.insert(-1, encode(['unreferenced-salt', 'unused', 'unused-value']))
assert checked('~'.join(extra)) == evidence

print(f'PASS: exact published code; sd-jwt {version("sd-jwt")}; {count} rejection cases')
print('PASS: full input/output per-call index and DSSE; SD-JWT issuance/presentation; client-held salts; runtime message claims')
print('PASS: input assistant roles remain client-supplied context; independent calls require no thread or predecessor')
print('LIMIT: no whole-runtime-thread or latest-call proof; tool records unverified by the text adapter; no live round trip')
print('KNOWN LIBRARY GAP: sd-jwt 0.10.4 accepts unreferenced disclosures; not full RFC 9901 conformance')
