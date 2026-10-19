"""Executable example from article/parts/08-sd-jwt-component-evidence.md."""

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
