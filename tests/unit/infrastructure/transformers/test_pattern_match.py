"""Unit tests for PatternMatchTransformer."""

import pytest

from dacke.infrastructure.pipeline.transformers.pattern_match import (
    PatternMatchTransformer,
)

from .common import make_doc


class TestPatternMatchTransformer:
    @pytest.mark.asyncio
    async def test_matching_pattern_sets_tags(self) -> None:
        doc = make_doc("Contact us at hello@example.com for details.")
        transformer = PatternMatchTransformer(
            patterns={"email": r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"}
        )
        await transformer.transform(doc)
        assert doc.chunks[0].metadata["tags"] == ["email"]

    @pytest.mark.asyncio
    async def test_no_match_sets_none(self) -> None:
        doc = make_doc("No email address here.")
        transformer = PatternMatchTransformer(
            patterns={"email": r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"}
        )
        await transformer.transform(doc)
        assert doc.chunks[0].metadata["tags"] is None

    @pytest.mark.asyncio
    async def test_multiple_patterns_all_matching(self) -> None:
        doc = make_doc("Email: foo@bar.com  DOI: 10.1000/xyz123")
        transformer = PatternMatchTransformer(
            patterns={
                "email": r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}",
                "doi": r"10\.\d{4,}/\S+",
            }
        )
        await transformer.transform(doc)
        assert set(doc.chunks[0].metadata["tags"] or []) == {"email", "doi"}

    @pytest.mark.asyncio
    async def test_partial_match(self) -> None:
        doc = make_doc("No doi here, just foo@bar.com")
        transformer = PatternMatchTransformer(
            patterns={
                "email": r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}",
                "doi": r"10\.\d{4,}/\S+",
            }
        )
        await transformer.transform(doc)
        assert doc.chunks[0].metadata["tags"] == ["email"]

    @pytest.mark.asyncio
    async def test_multiple_chunks_independent(self) -> None:
        doc = make_doc("foo@bar.com", "no match here")
        transformer = PatternMatchTransformer(
            patterns={"email": r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"}
        )
        await transformer.transform(doc)
        assert doc.chunks[0].metadata["tags"] == ["email"]
        assert doc.chunks[1].metadata["tags"] is None

    @pytest.mark.asyncio
    async def test_empty_document_returns_document(self) -> None:
        doc = make_doc()
        transformer = PatternMatchTransformer(patterns={"email": r"\S+@\S+"})
        result = await transformer.transform(doc)
        assert result is doc

    @pytest.mark.asyncio
    async def test_returns_same_document(self) -> None:
        doc = make_doc("content")
        transformer = PatternMatchTransformer(patterns={})
        result = await transformer.transform(doc)
        assert result is doc
