"""PowerPoint to Markdown: a heading per slide, text frames, tables, speaker notes."""

from pathlib import Path

from mcp_connector.documents import pptx as pptx_conv

FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "documents" / "sample.pptx"


def test_each_slide_becomes_a_heading_with_its_text_tables_and_notes() -> None:
    text = pptx_conv.to_markdown(FIXTURE.read_bytes())

    assert "## Slide 1: Quarterly Report" in text
    assert "The figures below are final." in text
    assert "| Item | Amount |" in text
    assert "| Servers | 12 |" in text
    assert "Notes: Speaker note one." in text
    assert "## Slide 2: Appendix" in text
    assert text.index("## Slide 1") < text.index("## Slide 2")


def test_the_title_is_not_repeated_as_a_text_frame() -> None:
    text = pptx_conv.to_markdown(FIXTURE.read_bytes())
    assert text.count("Quarterly Report") == 1
