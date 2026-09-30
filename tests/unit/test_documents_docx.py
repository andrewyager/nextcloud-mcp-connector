"""Word to Markdown: headings by level, paragraphs, list items, pipe tables, dropped rest."""

from pathlib import Path

from mcp_connector.documents import docx as docx_conv

FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "documents" / "sample.docx"


def test_headings_paragraphs_lists_and_tables_come_out_in_document_order() -> None:
    text = docx_conv.to_markdown(FIXTURE.read_bytes())
    lines = [line for line in text.splitlines() if line.strip()]

    assert lines[0] == "# Quarterly Report"
    assert lines[1] == "The figures below are final."
    assert lines[2] == "- First point"
    assert lines[3] == "| Item | Amount |"
    assert lines[4] == "| --- | --- |"
    assert lines[5] == "| Servers | 12 |"
    assert lines[6] == "## Appendix"
    assert lines[7] == "Nothing else."


def test_heading_levels_above_six_are_capped() -> None:
    assert docx_conv._heading_prefix("Heading 9") == "######"
    assert docx_conv._heading_prefix("Heading 2") == "##"
    assert docx_conv._heading_prefix("Title") == "#"
    assert docx_conv._heading_prefix("Normal") == ""


def test_cell_text_is_flattened_to_one_line_and_pipes_are_escaped() -> None:
    assert docx_conv._cell("a\nb | c") == "a b \\| c"
