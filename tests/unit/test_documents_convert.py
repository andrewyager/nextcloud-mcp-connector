"""The dispatcher: format to converter, the extra-missing refusal, one error for any parser."""

import importlib
import sys
import threading
from pathlib import Path

import pytest

from mcp_connector import documents
from mcp_connector.documents import docx as docx_conv
from mcp_connector.errors import REASON_GUARD_TRIPPED, ToolError

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "documents"
DOCX = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"


@pytest.mark.anyio
async def test_convert_dispatches_by_format_and_names_it() -> None:
    result = await documents.convert(
        (FIXTURES / "sample.docx").read_bytes(), DOCX, "/Docs/sample.docx"
    )
    assert result.format == "docx"
    assert result.markdown.startswith("# Quarterly Report")

    pdf = await documents.convert(
        (FIXTURES / "sample.pdf").read_bytes(), "application/pdf", "/Docs/sample.pdf"
    )
    assert pdf.format == "pdf"
    assert "## Page 1" in pdf.markdown


def test_the_zip_guard_runs_for_office_files_and_not_for_pdf() -> None:
    with pytest.raises(ToolError) as info:
        documents.convert_sync(b"not a zip at all", DOCX, "/Docs/a.docx")
    assert "readable Office file" in info.value.message

    # A PDF is not a zip; the guard must not touch it. The parser refuses instead.
    with pytest.raises(ToolError) as info:
        documents.convert_sync(b"not a pdf", "application/pdf", "/Docs/a.pdf")
    assert "could not be read as pdf" in info.value.message


def test_a_parser_exception_becomes_one_refusal_naming_file_and_format(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def boom(_data: bytes) -> str:
        raise ValueError("internal detail that must not leak")

    monkeypatch.setattr(docx_conv, "to_markdown", boom)
    with pytest.raises(ToolError) as info:
        documents.convert_sync((FIXTURES / "sample.docx").read_bytes(), DOCX, "/Docs/a.docx")
    assert info.value.message == "/Docs/a.docx could not be read as docx."
    assert "internal detail" not in str(info.value)
    assert "Open the file in Nextcloud" in info.value.hint


def test_a_guard_refusal_passes_through_unchanged(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def refuse(_data: bytes) -> str:
        raise ToolError(message="x", hint="y", reason=REASON_GUARD_TRIPPED)

    monkeypatch.setattr(docx_conv, "to_markdown", refuse)
    with pytest.raises(ToolError) as info:
        documents.convert_sync((FIXTURES / "sample.docx").read_bytes(), DOCX, "/Docs/a.docx")
    assert info.value.message == "x"
    assert info.value.hint == "y"
    assert info.value.reason == REASON_GUARD_TRIPPED


def test_without_the_extra_the_refusal_names_the_install_command(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # An entry of None in sys.modules makes ``import docx`` raise ImportError,
    # which is what a missing package does.
    for name in ("docx", "openpyxl", "pptx", "pypdf"):
        monkeypatch.setitem(sys.modules, name, None)

    with pytest.raises(ToolError) as info:
        documents.convert_sync((FIXTURES / "sample.docx").read_bytes(), DOCX, "/Docs/a.docx")
    assert "documents extra" in info.value.message
    assert "nextcloud-mcp-connector[documents]" in info.value.hint


def test_the_package_imports_without_the_extra(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    for name in ("docx", "openpyxl", "pptx", "pypdf", "mcp_connector.documents"):
        monkeypatch.delitem(sys.modules, name, raising=False)
    for name in ("docx", "openpyxl", "pptx", "pypdf"):
        monkeypatch.setitem(sys.modules, name, None)

    module = importlib.import_module("mcp_connector.documents")
    assert hasattr(module, "convert")


def test_the_conversion_executor_has_two_workers() -> None:
    assert documents._EXECUTOR._max_workers == 2


@pytest.mark.anyio
async def test_convert_runs_in_the_documents_executor_and_matches_convert_sync(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    threads: list[str] = []
    real = docx_conv.to_markdown

    def recording(data: bytes) -> str:
        threads.append(threading.current_thread().name)
        return real(data)

    monkeypatch.setattr(docx_conv, "to_markdown", recording)
    data = (FIXTURES / "sample.docx").read_bytes()
    result = await documents.convert(data, DOCX, "/Docs/sample.docx")

    assert result == documents.convert_sync(data, DOCX, "/Docs/sample.docx")
    assert threads[0].startswith("documents")
