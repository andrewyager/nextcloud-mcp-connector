"""Word to Markdown.

Body order is kept. Headers, footers, footnotes, comments and images are not.
The library is imported inside the function so the package imports without the extra.
"""

import io
import re
from collections.abc import Iterable

__all__ = ["to_markdown"]

_HEADING_RE = re.compile(r"^Heading (\d+)$")


def _heading_prefix(style_name: str) -> str:
    if style_name == "Title":
        return "#"
    match = _HEADING_RE.match(style_name)
    if match is None:
        return ""
    return "#" * min(int(match.group(1)), 6)


def _cell(text: str) -> str:
    return " ".join(text.split()).replace("|", "\\|")


def _table_lines(rows: Iterable[Iterable[str]]) -> list[str]:
    lines: list[str] = []
    for index, row in enumerate(rows):
        cells = [_cell(value) for value in row]
        lines.append("| " + " | ".join(cells) + " |")
        if index == 0:
            lines.append("| " + " | ".join("---" for _ in cells) + " |")
    return lines


def to_markdown(data: bytes) -> str:
    import docx
    from docx.table import Table
    from docx.text.paragraph import Paragraph

    document = docx.Document(io.BytesIO(data))
    out: list[str] = []
    for block in document.iter_inner_content():
        if isinstance(block, Paragraph):
            text = block.text.strip()
            if not text:
                continue
            style = (block.style.name if block.style is not None else "") or ""
            prefix = _heading_prefix(style)
            if prefix:
                out.append(f"{prefix} {text}")
            elif style.startswith("List"):
                out.append(f"- {text}")
            else:
                out.append(text)
            out.append("")
        elif isinstance(block, Table):
            rows = [[cell.text for cell in row.cells] for row in block.rows]
            out.extend(_table_lines(rows))
            out.append("")
    return "\n".join(out).strip() + "\n"
