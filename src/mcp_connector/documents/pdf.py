"""PDF to Markdown: the text layer per page, no layout reconstruction, no OCR."""

import io

from ..errors import REASON_GUARD_TRIPPED, ToolError
from .limits import Output

__all__ = ["MAX_PAGES", "to_markdown"]

MAX_PAGES = 500

_NO_TEXT = "(This PDF has no text layer; it is probably a scan. Nothing could be extracted.)"


def to_markdown(data: bytes) -> str:
    import pypdf

    reader = pypdf.PdfReader(io.BytesIO(data))
    # An owner-password-only PDF (bank statements, for example) opens with the empty user
    # password. Only a PDF that needs a real user password is refused.
    if reader.is_encrypted and not reader.decrypt(""):
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
    out = Output()
    any_text = False
    for number, page in enumerate(reader.pages, start=1):
        if out.full:
            break
        text = (page.extract_text() or "").strip()
        any_text = any_text or bool(text)
        out.add(f"## Page {number}")
        out.add("")
        if text:
            out.add(text)
            out.add("")
    if not any_text:
        return f"{_NO_TEXT}\n\n{out.text()}"
    return out.text()
