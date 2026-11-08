#!/usr/bin/env python3
"""Assemble the tool-admission article from its ordered Markdown parts."""

import argparse
from pathlib import Path
import posixpath
import re
from urllib.parse import urlsplit, urlunsplit


ROOT = Path(__file__).resolve().parent
PARTS = (
    "00-opening.md",
    "01-what-the-discussions-established.md",
    "02-two-kinds-of-evidence.md",
    "03-flat-chain.md",
    "04-admission-rules.md",
    "05-granularity.md",
    "06-tool-statement.md",
    "07-experiment.md",
    "08-limits.md",
    "09-composition.md",
)
OUTPUT = ROOT / "tool_admission_v01.md"


def rebase_links(text):
    """Resolve section-relative links from the assembled article's directory."""
    def replace(match):
        target = urlsplit(match.group(1))
        if target.scheme or target.netloc or not target.path or target.path.startswith("/"):
            return match.group(0)
        path = posixpath.normpath(posixpath.join("parts", target.path))
        return "](" + urlunsplit(("", "", path, target.query, target.fragment)) + ")"

    return re.sub(r"\]\(([^)\s]+)\)", replace, text)


def word_count(text):
    return len(text.split())


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="check without writing")
    args = parser.parse_args()

    chunks = []
    for name in PARTS:
        text = (ROOT / "parts" / name).read_text(encoding="utf-8").strip()
        if not text:
            raise SystemExit(f"Empty part: {name}")
        chunks.append(rebase_links(text))
    assembled = "\n\n".join(chunks) + "\n"

    if args.check:
        if not OUTPUT.exists() or OUTPUT.read_text(encoding="utf-8") != assembled:
            raise SystemExit("The assembled draft is missing or out of date; run build.py")
        print(f"OK: assembled draft matches all {len(PARTS)} parts")
    else:
        OUTPUT.write_text(assembled, encoding="utf-8")
        print(f"Built {OUTPUT.name} from {len(PARTS)} parts")

    print(f"Article body: {word_count(assembled):,} words")
    for name in PARTS:
        print(f"  {name}: {word_count((ROOT / 'parts' / name).read_text(encoding='utf-8')):,}")


if __name__ == "__main__":
    main()
