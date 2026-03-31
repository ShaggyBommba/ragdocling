import re
from logging import getLogger

from dacke.application.ports.transformer import Transformer
from dacke.domain.aggregates.document import Document

logging = getLogger(__name__)

_URL_RE = re.compile(
    r"https?://"
    r"(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,}"
    r"(?::\d+)?"
    r"(?:/[^\s\"'<>]*)?"
    r"(?:\?[^\s\"'<>]*)?"
    r"(?:#[^\s\"'<>]*)?",
    re.IGNORECASE,
)


class UrlExtractTransformer(Transformer[Document, Document]):
    """Extracts all HTTP/HTTPS URLs from each chunk's content and writes
    them (deduplicated, order-preserved) into chunk.metadata['urls']."""

    async def transform(self, document: Document) -> Document:
        total_urls = 0
        chunks = document.chunks
        logging.info(f"UrlExtractTransformer: scanning {len(chunks)} chunk(s)")
        for chunk in chunks:
            found = list(dict.fromkeys(_URL_RE.findall(chunk.content)))
            chunk.metadata["urls"] = found if found else None
            if found:
                total_urls += len(found)
                logging.debug(f"Chunk {chunk.identity}: extracted {found}")
        logging.info(
            f"UrlExtractTransformer: done — {total_urls} URL(s) across {len(chunks)} chunk(s)"
        )
        return document
