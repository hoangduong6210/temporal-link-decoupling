#!/usr/bin/env python3
"""Render the repository's narrow conference Markdown subset as stable HTML.

The renderer intentionally has no third-party dependency. It accepts headings,
paragraphs, and pipe tables, escapes all text, and emits deterministic UTF-8
HTML. Unsupported Markdown syntax fails instead of silently changing content.
"""

from __future__ import annotations

import argparse
from html import escape
from pathlib import Path
import re


TABLE_RULE = re.compile(r"^\|(?:\s*:?-+:?\s*\|)+$")


class RenderError(ValueError):
    """The manuscript uses syntax outside the auditable source subset."""


def _cells(line: str) -> list[str]:
    if not line.startswith("|") or not line.endswith("|"):
        raise RenderError(f"invalid table row: {line}")
    return [cell.strip() for cell in line[1:-1].split("|")]


def render(source: str) -> str:
    """Return deterministic HTML while preserving every visible scalar."""

    lines = source.splitlines()
    output = ["<!doctype html>", "<html>", "<head>", "<title>Decoupled Temporal Link Prediction with SR-GNN</title>", "</head>", "<body>"]
    paragraph: list[str] = []
    index = 0

    def flush_paragraph() -> None:
        if paragraph:
            output.append(f"<p>{escape(' '.join(paragraph))}</p>")
            paragraph.clear()

    while index < len(lines):
        line = lines[index].rstrip()
        if not line:
            flush_paragraph()
            index += 1
            continue
        if line.startswith("# ") or line.startswith("## "):
            flush_paragraph()
            level = "h1" if line.startswith("# ") else "h2"
            title = line[2:] if level == "h1" else line[3:]
            output.append(f"<{level}>{escape(title)}</{level}>")
            index += 1
            continue
        if line.startswith("|"):
            flush_paragraph()
            if index + 1 >= len(lines) or TABLE_RULE.fullmatch(lines[index + 1]) is None:
                raise RenderError("table header lacks a canonical separator")
            headers = _cells(line)
            output.append("<table>")
            output.append("<thead><tr>" + "".join(f"<th>{escape(cell)}</th>" for cell in headers) + "</tr></thead>")
            output.append("<tbody>")
            index += 2
            while index < len(lines) and lines[index].startswith("|"):
                cells = _cells(lines[index])
                if len(cells) != len(headers):
                    raise RenderError("table row width differs from its header")
                output.append("<tr>" + "".join(f"<td>{escape(cell)}</td>" for cell in cells) + "</tr>")
                index += 1
            output.extend(["</tbody>", "</table>"])
            continue
        if line.startswith(("- ", "* ", ">", "```")):
            raise RenderError(f"unsupported Markdown construct: {line}")
        paragraph.append(line.strip())
        index += 1

    flush_paragraph()
    output.extend(["</body>", "</html>"])
    return "\n".join(output) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    arguments = parser.parse_args()
    rendered = render(arguments.source.read_text(encoding="utf-8"))
    arguments.output.parent.mkdir(parents=True, exist_ok=True)
    with arguments.output.open("w", encoding="utf-8", newline="\n") as stream:
        stream.write(rendered)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
