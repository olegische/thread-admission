"""Check article assembly, code/schema consistency, and executable examples."""
import ast
import json
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
PARTS = ROOT / "article/parts"


def blocks(part, language):
    return re.findall(rf"```{language}\n(.*?)```", (PARTS / part).read_text(), re.S)


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


def main():
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
    tool_call, result = map(json.loads, blocks("05-verify-api-requests-and-responses.md", "json"))
    answer = next(json.loads(b) for b in blocks("07-metadata-loss-and-compaction.md", "json")
                  if json.loads(b).get("type") == "message")
    user = {"type": "message", "role": "user", "content": [
        {"type": "input_text", "text": returned[0]["content"][0]["text"]}]}
    if call["input"] != [user, tool_call, result] or call["output"] != [answer]:
        raise AssertionError("Article/API-fixture drift")
    print("PASS: standalone functions, constants, schemas and fixtures match the article", flush=True)
    for script, args in (
        ("article/build.py", ["--check"]),
        ("examples/run.py", []),
        ("article/notes/check_sdjwt_example.py", []),
    ):
        subprocess.run([sys.executable, str(ROOT / script), *args], cwd=ROOT, check=True)


if __name__ == "__main__":
    main()
