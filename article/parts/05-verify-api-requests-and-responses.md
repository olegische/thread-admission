## Verify the context of a model call

A service can also recognize returned content against observations made at the inference interface. Introduce an operator-controlled proxy: the agent sends model requests through it, and it forwards requests and relays response streams. The proxy can record the ordered input it received and output it delivered for each completed call.

Use the response identifier exposed at the agent-facing interface to retrieve that call's verification record. The authenticated API account scopes access to it. The proxy needs no agent thread ID, global history offset, or knowledge of which conversation the runtime is saving.

First consider a runtime that saves the same API items used at this interface. User messages, assistant messages, function calls, and results remain separate objects.

### Record complete input and output arrays

Hash each entire API item in the agreed saved/replayable representation, using JCS before SHA-256. Include its type, role where present, content, function arguments or result, and call ID. An `arguments` value remains a string: rewriting the JSON inside that string changes this whole-item hash.

If output-to-input conversion removes output-only fields, apply that agreed conversion before hashing output items. The verification record covers these represented items, not SSE delta boundaries or every field of the HTTP request. The input and output arrays remain separate and ordered.

There is no deduplication across calls. When the agent sends earlier items again, those items belong to the new request's input too. Their positions are local to that array. This matches client-managed conversation state, where earlier input and output are sent with the next request. [Conversation state](https://developers.openai.com/api/docs/guides/conversation-state)

### Follow the same two model calls

Both requests use `stream: true`, send the accumulated context in `input`, and use neither `previous_response_id` nor a provider-managed conversation.

The first input contains the user's request to run `export.py`. The response introduces a function call, streams its arguments, and supplies the finalized item at `response.output_item.done`:

```json
{
  "type": "function_call",
  "call_id": "call-1",
  "name": "exec_command",
  "arguments": "{\"cmd\":\"python export.py\",\"workdir\":\"/workspace\"}"
}
```

The agent executes the command locally and constructs the result:

```json
{
  "type": "function_call_output",
  "call_id": "call-1",
  "output": "Chunk ID: abc123\nWall time: 0.1000 seconds\nProcess exited with code 0\nOutput:\nWrote export.csv (128 rows).\n"
}
```

The second input includes the user message, function call, and result. The model streams the final answer, “Created export.csv with 128 rows.” The proxy captures finalized output items and publishes a completed-call record after successful response completion. An interrupted stream does not become a completed-call record. [Streaming function calls](https://developers.openai.com/api/docs/guides/function-calling#streaming)

| Completed call | Full request input | Finalized response output |
|---|---|---|
| `resp-1` | User message | Function call |
| `resp-2` | User message, function call, tool result | Assistant answer |

For this example, the second call alone covers all four records as input plus output. The first call's output is repeated in the second call's input. No cross-call history ledger is necessary to establish what the second call contained.

### Compare a returned call with the operator's record

The index key is the authenticated API subject and response ID. The caller supplies candidate input and output arrays; the receiver compares them with the recorded arrays in full, including their lengths and order:

```python
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
```

At capture, the proxy stores `record_call(...)` under `(subject, response_id)`. At return, the receiver obtains `evidence` from that protected index, not from an unauthenticated upload. Changing an item, moving it within an array, deleting it, or moving it from request to response fails the comparison.

A match establishes the role values and order presented in that call. An assistant item in its input is authenticated as client-supplied context; it is not thereby proved to be an earlier model output. Establishing that stronger property requires evidence of the corresponding earlier response. The current output is covered as output delivered by the proxy. A tool result in the input remains a report received from the client, not proof of local execution.

### Where this representation is available

With a Responses backend, OpenAI Agents SDK exposes a saved/replayable history interface through `result.to_input_list()`. This makes it a useful example for defining the representation to be compared; the verification index is an application addition. [Agents SDK results](https://openai.github.io/openai-agents-python/results/)

The capture and export paths must use the same output-to-input conversion. SDK conversion, for example, removes some output-only fields. [SDK conversion code](https://github.com/openai/openai-agents-python/blob/main/src/agents/items.py#L205-L237)

The next section moves the expected hashes out of the operator's index and into signed evidence held by the user. We then examine how a runtime's own thread export differs from the input and output of a model call.
