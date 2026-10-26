## Granularity belongs to the issuer

A model statement discloses message text, function names, arguments and tool outputs as units. A tool statement discloses a result, and a result is not one thing. A mail tool returns a message with a sender, a subject, a body and attachments. A payment tool returns an identifier, an amount, a fee and a status. Who decides what can be disclosed independently?

The executor does. It knows its domain; the profile does not. A mail server may issue the body as one disclosure or each paragraph as its own. A payment server may issue amount, fee and recipient separately so that a fee dispute can see the fee without the recipient. The profile fixes only how the subdivision is named: `result.sha256` and `result.length` commit to the whole, and `result.parts` carries the executor's own named disclosures, each a selectively disclosable claim, opaque to the profile and described by a schema the executor publishes under its `tool_id`.

The reason to do this with selective disclosure rather than a signed blob is that one result has several readers with different entitlements.

| Reader | What it needs from the record |
|---|---|
| The service continuing the task | the content the task needs |
| An auditor | who called, which operation, when, with what outcome |
| Another party in the process | one confirmed value: an amount, a status, an identifier |
| A fee review | the fee and the parameters it was computed from |

Sending the auditor the whole email to establish that a call was made is over-disclosure. A signature over the whole object forces a choice between disclosing everything and designing verifiable parts by hand. SD-JWT gives the parts ready-made, with their own salts, held by the client and presented on request. The earlier article's open question, whether verifiers really need different parts or whether whole-record signing would do, has its first concrete case here, and the experiment section tests it rather than assuming it.

What the executor can attest also depends on what it observes. For a payment, accepting the request, submitting the transaction and receiving its confirmation are three observations at three times, and an executor that only saw the first should issue a statement that says so. The executor signs what it saw. The profile's `outcome` field is deliberately coarse for this reason: `executed` means the executor's own operation completed, not that the world changed as intended.
