"""Unit tests for UrlExtractTransformer."""

import pytest

from dacke.infrastructure.pipeline.transformers.url_extract import UrlExtractTransformer

from .common import make_doc


class TestUrlExtractTransformer:
    @pytest.mark.asyncio
    async def test_extracts_single_url(self) -> None:
        doc = make_doc("Visit https://example.com for more info.")
        await UrlExtractTransformer().transform(doc)
        assert doc.chunks[0].metadata["urls"] == ["https://example.com"]

    @pytest.mark.asyncio
    async def test_extracts_multiple_urls(self) -> None:
        doc = make_doc("See https://foo.com and https://bar.org/page?q=1")
        await UrlExtractTransformer().transform(doc)
        urls = doc.chunks[0].metadata["urls"] or []
        assert "https://foo.com" in urls
        assert "https://bar.org/page?q=1" in urls

    @pytest.mark.asyncio
    async def test_deduplicates_urls(self) -> None:
        doc = make_doc("https://example.com and https://example.com again")
        await UrlExtractTransformer().transform(doc)
        assert doc.chunks[0].metadata["urls"] == ["https://example.com"]

    @pytest.mark.asyncio
    async def test_no_urls_sets_none(self) -> None:
        doc = make_doc("No links in this text at all.")
        await UrlExtractTransformer().transform(doc)
        assert doc.chunks[0].metadata["urls"] is None

    @pytest.mark.asyncio
    async def test_preserves_url_order(self) -> None:
        doc = make_doc(
            "First https://alpha.com then https://beta.com then https://gamma.com"
        )
        await UrlExtractTransformer().transform(doc)
        urls = doc.chunks[0].metadata["urls"] or []
        assert urls == ["https://alpha.com", "https://beta.com", "https://gamma.com"]

    @pytest.mark.asyncio
    async def test_multiple_chunks_processed(self) -> None:
        doc = make_doc("https://first.com", "no url", "https://second.com")
        await UrlExtractTransformer().transform(doc)
        assert doc.chunks[0].metadata["urls"] == ["https://first.com"]
        assert doc.chunks[1].metadata["urls"] is None
        assert doc.chunks[2].metadata["urls"] == ["https://second.com"]

    @pytest.mark.asyncio
    async def test_http_and_https_both_extracted(self) -> None:
        doc = make_doc("http://insecure.com and https://secure.com")
        await UrlExtractTransformer().transform(doc)
        urls = doc.chunks[0].metadata["urls"] or []
        assert "http://insecure.com" in urls
        assert "https://secure.com" in urls
