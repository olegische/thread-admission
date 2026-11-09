"""Conversions a runtime applies to an MCP result before the model sees it.

The receiving service repeats an accepted conversion and compares its
output with the proxy's evidence. Other result shapes need their own rules.
"""


def model_input_for_mcp_result(result):
    """Convert one text block, preserving the MCP tool error flag."""
    if not isinstance(result, dict):
        return None
    is_error = result.get("isError", False)
    if type(is_error) is not bool:
        return None
    content = result.get("content")
    if not isinstance(content, list) or len(content) != 1:
        return None
    block = content[0]
    if not isinstance(block, dict) or block.get("type") != "text":
        return None
    value = block.get("text")
    if not isinstance(value, str):
        return None
    return "MCP tool error: " + value if is_error else value
