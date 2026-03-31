"""Unit tests for RetrieveResultDTO and _build_formatted_text."""

from unittest.mock import MagicMock
from uuid import uuid4

import pytest
from qdrant_client.http.models import ScoredPoint

from dacke.dto.retrieve import RetrieveResultDTO, _build_formatted_text


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_point(
    text: str = "chunk content",
    origin: str = "https://example.com/doc.pdf",
    title: str | None = "My Doc",
    pages: int | None = 3,
    tags: list[str] | None = None,
    attachments: list[dict] | None = None,
    score: float = 0.85,
    references: list[str] | None = None,
) -> ScoredPoint:
    point = MagicMock(spec=ScoredPoint)
    point.id = str(uuid4())
    point.score = score
    point.payload = {
        "text": text,
        "origin": origin,
        "title": title,
        "pages": pages,
        "tags": tags or [],
        "attachments": attachments or [],
        "references": references or [],
    }
    return point


# ---------------------------------------------------------------------------
# Tests: _build_formatted_text
# ---------------------------------------------------------------------------


class TestBuildFormattedText:
    def test_includes_result_header(self) -> None:
        text = _build_formatted_text(
            raw_text="body", score=0.9, title=None, origin="http://x.com",
            pages=None, tags=[], attachments=[], index=1, total=3,
        )
        assert "# Result 1/3" in text

    def test_includes_score_in_header(self) -> None:
        text = _build_formatted_text(
            raw_text="body", score=0.1234, title=None, origin="http://x.com",
            pages=None, tags=[], attachments=[],
        )
        assert "0.1234" in text

    def test_includes_origin_in_frontmatter(self) -> None:
        text = _build_formatted_text(
            raw_text="body", score=0.5, title=None, origin="https://source.com/file.pdf",
            pages=None, tags=[], attachments=[],
        )
        assert "https://source.com/file.pdf" in text

    def test_includes_title_as_h2(self) -> None:
        text = _build_formatted_text(
            raw_text="body", score=0.5, title="My Title", origin="http://x.com",
            pages=None, tags=[], attachments=[],
        )
        assert "## My Title" in text

    def test_no_title_omits_h2(self) -> None:
        text = _build_formatted_text(
            raw_text="body", score=0.5, title=None, origin="http://x.com",
            pages=None, tags=[], attachments=[],
        )
        assert "## " not in text or "## Attachments" not in text

    def test_includes_pages_in_frontmatter(self) -> None:
        text = _build_formatted_text(
            raw_text="body", score=0.5, title=None, origin="http://x.com",
            pages=5, tags=[], attachments=[],
        )
        assert "pages: 5" in text

    def test_includes_tags_in_frontmatter(self) -> None:
        text = _build_formatted_text(
            raw_text="body", score=0.5, title=None, origin="http://x.com",
            pages=None, tags=["ai", "rag"], attachments=[],
        )
        assert "ai" in text
        assert "rag" in text

    def test_includes_attachments_section(self) -> None:
        attachments = [{"reference": "http://x.com/img.png", "description": "A chart"}]
        text = _build_formatted_text(
            raw_text="body", score=0.5, title=None, origin="http://x.com",
            pages=None, tags=[], attachments=attachments,
        )
        assert "## Attachments" in text
        assert "img.png" in text


# ---------------------------------------------------------------------------
# Tests: RetrieveResultDTO.from_point
# ---------------------------------------------------------------------------


class TestRetrieveResultDTO:
    def test_from_point_populates_score(self) -> None:
        point = _make_point(score=0.77)
        dto = RetrieveResultDTO.from_point(point)
        assert dto.score == pytest.approx(0.77)

    def test_from_point_score_override(self) -> None:
        point = _make_point(score=0.99)
        dto = RetrieveResultDTO.from_point(point, score_override=0.0)
        assert dto.score == pytest.approx(0.0)

    def test_from_point_populates_origin(self) -> None:
        point = _make_point(origin="https://my-source.com/doc.pdf")
        dto = RetrieveResultDTO.from_point(point)
        assert dto.origin == "https://my-source.com/doc.pdf"

    def test_from_point_populates_title(self) -> None:
        point = _make_point(title="Important Paper")
        dto = RetrieveResultDTO.from_point(point)
        assert dto.title == "Important Paper"

    def test_from_point_none_title(self) -> None:
        point = _make_point(title=None)
        dto = RetrieveResultDTO.from_point(point)
        assert dto.title is None

    def test_from_point_populates_pages(self) -> None:
        point = _make_point(pages=7)
        dto = RetrieveResultDTO.from_point(point)
        assert dto.pages == 7

    def test_from_point_text_contains_content(self) -> None:
        point = _make_point(text="hello world")
        dto = RetrieveResultDTO.from_point(point)
        assert "hello world" in dto.text

    def test_from_point_index_and_total_in_text(self) -> None:
        point = _make_point()
        dto = RetrieveResultDTO.from_point(point, index=2, total=5)
        assert "2/5" in dto.text

    def test_from_point_empty_payload(self) -> None:
        point = MagicMock(spec=ScoredPoint)
        point.id = str(uuid4())
        point.score = 0.5
        point.payload = {}
        dto = RetrieveResultDTO.from_point(point)
        assert dto.score == pytest.approx(0.5)
        assert dto.origin == ""
