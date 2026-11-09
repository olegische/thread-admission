"""Check article assembly, code/schema consistency, and executable examples."""
import ast
import json
import os
from pathlib import Path
import re
import subprocess
import sys
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[1]
PARTS = ROOT / "articles/thread_admission/parts"
TOOL_PARTS = ROOT / "articles/tool_admission/parts"


def check_markdown_links():
    count = 0
    for directory, folders, filenames in os.walk(ROOT):
        folders[:] = [name for name in folders if not name.startswith(".") and name != "__pycache__"]
        for filename in filenames:
            if not filename.endswith(".md"):
                continue
            source = Path(directory) / filename
            text = source.read_text(encoding="utf-8")
            links = re.findall(r"\]\((?:<([^>\n]+)>|([^)\s]+))\)", text)
            links += re.findall(r"(?m)^ {0,3}\[[^]\n]+\]:\s*(?:<([^>\n]+)>|(\S+))", text)
            for angle, plain in links:
                link = angle or plain
                url = urlsplit(link)
                if url.scheme == "file" or url.path.startswith("/") and not url.netloc:
                    raise AssertionError(f"Absolute local link in {source.relative_to(ROOT)}: {link}")
                if url.scheme or url.netloc:
                    own_repo = (url.hostname == "github.com" and
                                url.path.rstrip("/").startswith("/olegische/thread-admission/")
                                or url.hostname == "raw.githubusercontent.com" and
                                url.path.startswith("/olegische/thread-admission/")
                                or url.hostname == "github.com" and
                                url.path.rstrip("/") == "/olegische/thread-admission" and url.fragment)
                    if own_repo:
                        raise AssertionError(f"Use a relative repository link in {source.relative_to(ROOT)}: {link}")
                    continue
                target = (source.parent / unquote(url.path)).resolve() if url.path else source
                if not target.is_relative_to(ROOT) or not target.exists():
                    raise AssertionError(f"Missing repository target in {source.relative_to(ROOT)}: {link}")
                if url.fragment and target.suffix == ".md":
                    anchors = set()
                    seen = {}
                    for heading in re.findall(r"(?m)^ {0,3}#{1,6}\s+(.+?)\s*#*\s*$", target.read_text(encoding="utf-8")):
                        slug = re.sub(r"[^\w\- ]", "", heading.lower()).replace(" ", "-")
                        number = seen.get(slug, 0)
                        anchors.add(slug + (f"-{number}" if number else ""))
                        seen[slug] = number + 1
                    if unquote(url.fragment) not in anchors:
                        raise AssertionError(f"Missing Markdown anchor in {source.relative_to(ROOT)}: {link}")
                count += 1
    print(f"PASS: {count} relative Markdown links and images resolve", flush=True)


def blocks(part, language, parts=None):
    return re.findall(rf"```{language}\n(.*?)```", ((parts or PARTS) / part).read_text(), re.S)


def definitions(source):
    result = {}
    for node in ast.parse(source).body:
        if isinstance(node, ast.FunctionDef):
            result[node.name] = ast.dump(node, include_attributes=False)
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id.isupper():
                    result[target.id] = ast.dump(node, include_attributes=False)
    return result


def check_tool_article():
    """Tool admission: section 7 code, section 6 schema, section 3 digests, fixtures."""
    published = definitions("\n".join(blocks("07-experiment.md", "python", TOOL_PARTS)))
    standalone = {}
    for module in ("digests.py", "mcp.py", "model_calls.py", "tool_record.py"):
        standalone.update(definitions((ROOT / "examples" / module).read_text()))
    for name, definition in published.items():
        if standalone.get(name) != definition:
            raise AssertionError(f"Article/code drift: {name}")
    schema = json.loads((ROOT / "schemas/tool-call.schema.json").read_text())
    if schema != json.loads(blocks("06-tool-statement.md", "json", TOOL_PARTS)[0]):
        raise AssertionError("Article/schema drift: tool-call.schema.json")

    section_three = (TOOL_PARTS / "03-flat-chain.md").read_text()
    examples = re.findall(r"arguments:\s+(\S.*?)\nraw_sha256:\s+([0-9a-f]{64})\njcs_sha256:\s+([0-9a-f]{64})",
                          section_three)
    if len(examples) != 2:
        raise AssertionError("Expected two argument digest examples in section 3")
    sys.path.insert(0, str(ROOT / "examples"))
    from digests import argument_digests
    from mcp import model_input_for_mcp_result
    for raw, raw_digest, jcs_digest in examples:
        if argument_digests(raw) != {"raw_sha256": raw_digest, "jcs_sha256": jcs_digest}:
            raise AssertionError(f"Section 3 digests do not match: {raw}")

    call_1 = json.loads((ROOT / "fixtures/tool/model-call-1.json").read_text())
    call_2 = json.loads((ROOT / "fixtures/tool/model-call-2.json").read_text())
    result = json.loads((ROOT / "fixtures/tool/tool-result.json").read_text())
    error = json.loads((ROOT / "fixtures/tool/tool-result-error.json").read_text())
    request = call_1["output"][0]
    if (request["type"] != "function_call" or request["arguments"] != examples[0][0]
            or call_2["input"][:2] != [*call_1["input"], request]
            or call_2["input"][2] != {"type": "function_call_output", "call_id": request["call_id"],
                                      "output": model_input_for_mcp_result(result)}
            or error.get("isError") is not True or result.get("isError") is not None):
        raise AssertionError("Tool fixtures drift")
    meta = json.loads(blocks("06-tool-statement.md", "json", TOOL_PARTS)[1])
    if (meta["params"]["name"] != request["name"]
            or meta["params"]["arguments"] != json.loads(request["arguments"])):
        raise AssertionError("Section 6 request example differs from the tool fixtures")
    print("PASS: tool article code, schema, digests and fixtures match the article", flush=True)


def main():
    check_markdown_links()
    sources = {
        "snapshot.py": "03-snapshot-and-catalog.md",
        "prefix.py": "04-verified-prefix-and-summary.md",
        "call_index.py": "05-verify-api-requests-and-responses.md",
        "dsse_envelope.py": "06-portable-verification.md",
        "sdjwt_evidence.py": "08-sd-jwt-component-evidence.md",
        "runtime_adapter.py": "08-sd-jwt-component-evidence.md",
    }
    for module, part in sources.items():
        published = definitions("\n".join(blocks(part, "python")))
        standalone = definitions((ROOT / "examples" / module).read_text())
        if not standalone:
            raise AssertionError(f"No code in {module}")
        for name, definition in standalone.items():
            if published.get(name) != definition:
                raise AssertionError(f"Article/code drift: {module}:{name}")
        # Split section 8 into evidence and runtime-adapter modules.
        if part != "08-sd-jwt-component-evidence.md" and standalone != published:
            raise AssertionError(f"Missing published definition in {module}")
    section_eight = definitions("\n".join(blocks("08-sd-jwt-component-evidence.md", "python")))
    extracted = {}
    for module in ("sdjwt_evidence.py", "runtime_adapter.py"):
        extracted.update(definitions((ROOT / "examples" / module).read_text()))
    if extracted != section_eight:
        raise AssertionError("Section 8 extraction is incomplete")

    schemas = {
        "catalog-entry.schema.json": "03-snapshot-and-catalog.md",
        "checkpoint.schema.json": "04-verified-prefix-and-summary.md",
        "whole-call.schema.json": "06-portable-verification.md",
        "component-call.schema.json": "08-sd-jwt-component-evidence.md",
    }
    for filename, part in schemas.items():
        if json.loads((ROOT / "schemas" / filename).read_text()) != json.loads(blocks(part, "json")[0]):
            raise AssertionError(f"Article/schema drift: {filename}")

    returned = json.loads((ROOT / "fixtures/app-server-transcript.json").read_text())
    if returned != json.loads(blocks("01-what-returning-a-thread-means.md", "json")[0]):
        raise AssertionError("Article/runtime-fixture drift")
    call = json.loads((ROOT / "fixtures/api-call.json").read_text())
    answer = next(json.loads(b) for b in blocks("07-metadata-loss-and-compaction.md", "json")
                  if json.loads(b).get("type") == "message")
    user = {"type": "message", "role": "user", "content": [
        {"type": "input_text", "text": returned[0]["content"][0]["text"]}]}
    if len(call["input"]) != 3 or call["input"][0] != user or call["output"] != [answer]:
        raise AssertionError("Article/API-fixture drift")
    tool_call, result = call["input"][1:]
    execution = returned[1]
    if (tool_call["type"] != "function_call"
            or tool_call["name"] != "exec_command"
            or json.loads(tool_call["arguments"]) != {
                "cmd": execution["command"], "workdir": execution["cwd"]}
            or result["type"] != "function_call_output"
            or result["call_id"] != tool_call["call_id"]
            or not result["output"].endswith(execution["aggregatedOutput"])):
        raise AssertionError("API/runtime-fixture drift")
    print("PASS: standalone functions, constants, schemas and fixtures match the article", flush=True)
    check_tool_article()
    for script, args in (
        ("articles/thread_admission/build.py", ["--check"]),
        ("articles/tool_admission/build.py", ["--check"]),
        ("examples/run.py", []),
        ("examples/run_tool.py", []),
        ("articles/thread_admission/notes/check_sdjwt_example.py", []),
    ):
        subprocess.run([sys.executable, str(ROOT / script), *args], cwd=ROOT, check=True)


if __name__ == "__main__":
    main()
