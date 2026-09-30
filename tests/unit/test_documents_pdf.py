"""PDF to Markdown: a heading per page, extracted text, refusals for encrypted and oversize."""

import io
from pathlib import Path

import pypdf
import pytest

from mcp_connector.documents import pdf as pdf_conv
from mcp_connector.errors import REASON_GUARD_TRIPPED, ToolError

FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "documents" / "sample.pdf"


def test_each_page_becomes_a_heading_with_its_text() -> None:
    text = pdf_conv.to_markdown(FIXTURE.read_bytes())

    assert "## Page 1" in text
    assert "Quarterly Report" in text
    assert "Servers 12" in text
    assert "## Page 2" in text
    assert "Appendix" in text
    assert text.index("## Page 1") < text.index("## Page 2")


def _blank_pdf(pages: int) -> bytes:
    writer = pypdf.PdfWriter()
    for _ in range(pages):
        writer.add_blank_page(width=200, height=200)
    buffer = io.BytesIO()
    writer.write(buffer)
    return buffer.getvalue()


def test_a_pdf_without_a_text_layer_says_so_at_the_top() -> None:
    text = pdf_conv.to_markdown(_blank_pdf(2))
    first = text.splitlines()[0]
    assert "no text layer" in first
    assert "## Page 1" in text


def test_an_encrypted_pdf_is_refused_without_trying() -> None:
    writer = pypdf.PdfWriter()
    writer.add_blank_page(width=200, height=200)
    writer.encrypt(user_password="", owner_password="owner")
    buffer = io.BytesIO()
    writer.write(buffer)

    with pytest.raises(ToolError) as info:
        pdf_conv.to_markdown(buffer.getvalue())
    assert "encrypted" in info.value.message
    assert info.value.reason != REASON_GUARD_TRIPPED


def test_too_many_pages_are_refused(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(pdf_conv, "MAX_PAGES", 3)
    with pytest.raises(ToolError) as info:
        pdf_conv.to_markdown(_blank_pdf(4))
    assert info.value.reason == REASON_GUARD_TRIPPED
