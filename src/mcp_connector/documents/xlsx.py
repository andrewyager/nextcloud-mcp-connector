"""Excel to Markdown: a heading per sheet and a pipe table of the stored values.

Values, not formulas: ``data_only=True`` reads what the last save cached, which is what a
reader of the sheet sees. Hidden sheets are included, because hiding is not a permission.
"""

import datetime
import io
from typing import Any

from ..errors import REASON_GUARD_TRIPPED, ToolError

__all__ = ["MAX_ROWS", "MAX_SHEETS", "to_markdown"]

MAX_SHEETS = 50
MAX_ROWS = 10000


def _text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, datetime.datetime):
        # openpyxl returns dates as datetimes; a midnight time means a plain date.
        if value.time() == datetime.time():
            return value.date().isoformat()
        return value.isoformat()
    if isinstance(value, datetime.date):
        return value.isoformat()
    return " ".join(str(value).split()).replace("|", "\\|")


def _trim(rows: list[list[str]]) -> list[list[str]]:
    while rows and not any(rows[-1]):
        rows.pop()
    width = 0
    for row in rows:
        for index in range(len(row) - 1, -1, -1):
            if row[index]:
                width = max(width, index + 1)
                break
    return [row[:width] + [""] * (width - len(row[:width])) for row in rows]


def _sheet_lines(rows: list[list[str]], omitted: int) -> list[str]:
    lines: list[str] = []
    for index, row in enumerate(rows):
        lines.append("| " + " | ".join(row) + " |")
        if index == 0:
            lines.append("| " + " | ".join("---" for _ in row) + " |")
    if omitted:
        lines.append(f"({omitted} rows omitted, the sheet is longer than {MAX_ROWS} rows)")
    return lines


def to_markdown(data: bytes) -> str:
    import openpyxl

    workbook = openpyxl.load_workbook(io.BytesIO(data), read_only=True, data_only=True)
    sheets = workbook.worksheets
    if len(sheets) > MAX_SHEETS:
        raise ToolError(
            message=f"The workbook has {len(sheets)} sheets, more than {MAX_SHEETS}.",
            hint="Split the workbook, or use files_download for the raw file.",
            reason=REASON_GUARD_TRIPPED,
        )
    out: list[str] = []
    for sheet in sheets:
        rows: list[list[str]] = []
        omitted = 0
        for index, values in enumerate(sheet.iter_rows(values_only=True)):
            if index >= MAX_ROWS:
                omitted += 1
                continue
            rows.append([_text(value) for value in values])
        rows = _trim(rows)
        out.append(f"## {sheet.title}")
        out.append("")
        if rows:
            out.extend(_sheet_lines(rows, omitted))
        else:
            out.append("(empty sheet)")
        out.append("")
    workbook.close()
    return "\n".join(out).strip() + "\n"
