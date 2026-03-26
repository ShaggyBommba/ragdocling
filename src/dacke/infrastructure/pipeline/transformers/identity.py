from dacke.application.ports.transformer import Transformer
from dacke.domain.aggregates.document import Document


class IdentityTransformer(Transformer[Document, Document]):
    async def transform(self, document: Document) -> Document:
        return document
