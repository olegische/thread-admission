#!/usr/bin/env python3
"""Assemble the article from its ordered Markdown parts."""

import argparse
from pathlib import Path
import re


ROOT = Path(__file__).resolve().parent
PARTS = (
    "00-opening.md",
    "01-what-returning-a-thread-means.md",
    "02-choose-what-you-need-to-preserve.md",
    "03-snapshot-and-catalog.md",
    "04-verified-prefix-and-summary.md",
    "05-verify-api-requests-and-responses.md",
    "06-portable-verification.md",
    "07-metadata-loss-and-compaction.md",
    "08-sd-jwt-component-evidence.md",
    "09-conclusion.md",
)
OUTPUT = ROOT / "context_admission.md"


def word_count(text):
    """Whitespace count of Markdown body, excluding YAML and References."""
    text = re.sub(r"\A---\n.*?\n---\n", "", text, count=1, flags=re.S)
    text = re.split(r"(?m)^## References\s*$", text, maxsplit=1)[0]
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
        # Image paths in parts are relative to article/parts/.
        text = text.replace("](../images/", "](images/")
        chunks.append(text)
    assembled = "\n\n".join(chunks) + "\n"

    if args.check:
        if not OUTPUT.exists() or OUTPUT.read_text(encoding="utf-8") != assembled:
            raise SystemExit("The assembled draft is missing or out of date; run build.py")
        print(f"OK: assembled draft matches all {len(PARTS)} parts")
    else:
        OUTPUT.write_text(assembled, encoding="utf-8")
        print(f"Built {OUTPUT.name} from {len(PARTS)} parts")

    count = word_count(assembled)
    print(f"Article body: {count:,} words")


if __name__ == "__main__":
    main()
