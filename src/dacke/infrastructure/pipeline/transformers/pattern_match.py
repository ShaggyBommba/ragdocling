import re
from logging import getLogger

from dacke.application.ports.transformer import Transformer
from dacke.domain.aggregates.document import Document

logging = getLogger(__name__)


class PatternMatchTransformer(Transformer[Document, Document]):
    """Scans each chunk's content against a set of regex patterns and writes
    the names of all matching patterns into chunk.metadata['matched_patterns']."""

    def __init__(self, patterns: dict[str, str]) -> None:
        """
        Args:
            patterns: mapping of pattern name -> regex string.
        """
        self._compiled = {
            name: re.compile(pattern) for name, pattern in patterns.items()
        }

    async def transform(self, document: Document) -> Document:
        total_matches = 0
        chunks = document.chunks
        logging.info(
            f"PatternMatchTransformer: scanning {len(chunks)} chunk(s) "
            f"against patterns {list(self._compiled.keys())}"
        )
        for chunk in chunks:
            matches = [
                name
                for name, regex in self._compiled.items()
                if regex.search(chunk.content)
            ]
            chunk.metadata["tags"] = matches if matches else None
            if matches:
                total_matches += len(matches)
                logging.debug(f"Chunk {chunk.identity}: matched {matches}")
        logging.info(
            f"PatternMatchTransformer: done — {total_matches} match(es) across {len(chunks)} chunk(s)"
        )
        return document
