"""PowerPoint to Markdown: a heading per slide, text frames, tables, speaker notes."""

from pathlib import Path

import pytest

from mcp_connector.documents import limits
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


def test_the_output_stops_at_the_cap_with_a_note(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(limits, "MAX_OUTPUT_CHARS", 40)
    text = pptx_conv.to_markdown(FIXTURE.read_bytes())
    body, _, note = text.rstrip("\n").rpartition("\n")
    assert note == "(output truncated at 40 characters)"
    assert len(body.rstrip("\n")) <= 40
    assert "## Slide 2" not in text
