"""PDF to Markdown: the text layer per page, no layout reconstruction, no OCR."""

import io

from ..errors import REASON_GUARD_TRIPPED, ToolError

__all__ = ["MAX_PAGES", "to_markdown"]

MAX_PAGES = 500

_NO_TEXT = "(This PDF has no text layer; it is probably a scan. Nothing could be extracted.)"


def to_markdown(data: bytes) -> str:
    import pypdf

    reader = pypdf.PdfReader(io.BytesIO(data))
    if reader.is_encrypted:
        raise ToolError(
            message="The PDF is encrypted.",
            hint=("Remove the password in a PDF tool and upload a copy, then read that one."),
        )
    count = len(reader.pages)
    if count > MAX_PAGES:
        raise ToolError(
            message=f"The PDF has {count} pages, more than {MAX_PAGES}.",
            hint="Split the document, or use files_download for the raw file.",
            reason=REASON_GUARD_TRIPPED,
        )
    out: list[str] = []
    any_text = False
    for number, page in enumerate(reader.pages, start=1):
        text = (page.extract_text() or "").strip()
        any_text = any_text or bool(text)
        out.append(f"## Page {number}")
        out.append("")
        if text:
            out.append(text)
            out.append("")
    if not any_text:
        out.insert(0, _NO_TEXT)
        out.insert(1, "")
    return "\n".join(out).strip() + "\n"
