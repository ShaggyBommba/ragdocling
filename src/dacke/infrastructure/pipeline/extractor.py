from logging import getLogger

from docling.datamodel.accelerator_options import AcceleratorOptions
from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import (
    CodeFormulaVlmOptions,
    EasyOcrOptions,
    PdfPipelineOptions,
    PictureDescriptionApiOptions,
    PictureDescriptionVlmEngineOptions,
    TableFormerMode,
    TableStructureOptions,
)
from docling.document_converter import DocumentConverter, PdfFormatOption
from docling_core.transforms.chunker.hierarchical_chunker import (
    ChunkingDocSerializer,
    ChunkingSerializerProvider,
    TripletTableSerializer,
)
from docling_core.transforms.chunker.hybrid_chunker import HybridChunker
from docling_core.transforms.chunker.tokenizer.huggingface import HuggingFaceTokenizer
from docling_core.transforms.serializer.markdown import MarkdownParams
from docling_core.types.doc.base import ImageRefMode
from docling_core.types.doc.document import DoclingDocument
from pydantic import AnyUrl
from transformers import AutoTokenizer, PreTrainedTokenizerBase

from dacke.application.ports.extractor import Extractor
from dacke.domain.aggregates.document import Document
from dacke.domain.entities.attachment import Attachment
from dacke.domain.entities.chunk import Chunk
from dacke.domain.exceptions import DomainError
from dacke.domain.values.artifact import StoragePath
from dacke.domain.values.attachment import AttachmentTypes, Content
from dacke.domain.values.document import DocumentID, DocumentMetadata
from dacke.domain.values.extraction import ExtractionSettings
from dacke.domain.values.pipeline import PipelineID

logging = getLogger(__name__)


class Serializer(ChunkingSerializerProvider):
    """Custom serializer for document chunking with image handling."""

    def get_serializer(self, doc: DoclingDocument) -> ChunkingDocSerializer:
        return ChunkingDocSerializer(
            doc=doc,
            table_serializer=TripletTableSerializer(),
            params=MarkdownParams(
                image_placeholder="![image]",
                image_mode=ImageRefMode.REFERENCED,
                indent=4,
            ),
        )


class DoclingExtractor(Extractor[ExtractionSettings, Document]):

    def pdf(self, request: ExtractionSettings) -> PdfPipelineOptions:
        options = PdfPipelineOptions()
        options.document_timeout = request.runtime.document_timeout
        options.artifacts_path = request.runtime.artifacts_path
        options.allow_external_plugins = request.runtime.allow_external_plugins
        options.force_backend_text = request.runtime.force_backend_text

        options.accelerator_options = AcceleratorOptions(
            device=request.compute.device,
            num_threads=request.compute.num_threads,
            cuda_use_flash_attention2=False,
        )

        options.do_ocr = request.ocr.enabled
        if request.ocr.enabled:
            options.ocr_options = EasyOcrOptions(
                lang=request.ocr.languages,
                force_full_page_ocr=False,
                bitmap_area_threshold=0.05,
                use_gpu=None,
            )

        options.do_table_structure = request.tables.enabled
        options.table_structure_options = TableStructureOptions(
            do_cell_matching=True,
            mode=(
                TableFormerMode.ACCURATE
                if request.tables.quality in {"accurate", "balanced"}
                else TableFormerMode.FAST
            ),
        )

        options.do_code_enrichment = request.enrichments.code
        options.do_formula_enrichment = request.enrichments.formulas
        options.code_formula_options = CodeFormulaVlmOptions.from_preset(
            "codeformulav2",
            scale=2.0,
            max_size=None,
            extract_code=request.enrichments.code,
            extract_formulas=request.enrichments.formulas,
        )

        options.images_scale = request.images.scale
        options.generate_page_images = request.images.page_images
        options.generate_picture_images = request.images.picture_images
        options.generate_parsed_pages = request.images.parsed_pages

        options.do_picture_classification = request.enrichments.picture_classification

        options.do_picture_description = request.enrichments.picture_description
        if request.enrichments.picture_description:
            if request.description.use_remote_api:
                options.enable_remote_services = True
                options.picture_description_options = PictureDescriptionApiOptions(
                    url=AnyUrl(request.description.url),
                    headers=request.description.headers,
                    params=request.description.params,
                    timeout=request.description.timeout,
                    concurrency=request.description.concurrency,
                    prompt=request.description.prompt,
                    scale=2.0,
                    picture_area_threshold=0.5,
                    classification_min_confidence=0.0,
                )
            else:
                options.picture_description_options = (
                    PictureDescriptionVlmEngineOptions.from_preset(
                        "smolvlm",
                        prompt=request.description.prompt,
                        scale=2.0,
                        picture_area_threshold=0.5,
                        classification_min_confidence=0.0,
                    )
                )

        options.ocr_batch_size = request.runtime.ocr_batch_size
        options.layout_batch_size = request.runtime.layout_batch_size
        options.table_batch_size = request.runtime.table_batch_size
        options.batch_polling_interval_seconds = (
            request.runtime.batch_polling_interval_seconds
        )
        options.queue_max_size = request.runtime.queue_max_size

        return options

    def chunker(self, config: ExtractionSettings) -> HybridChunker:
        serializer = Serializer()

        tokenizer_model: PreTrainedTokenizerBase = AutoTokenizer.from_pretrained(
            "sentence-transformers/all-MiniLM-L6-v2",
            use_fast=True,
        )  # type: ignore

        tokenizer = HuggingFaceTokenizer(
            tokenizer=tokenizer_model,
            max_tokens=512,
        )

        chunker = HybridChunker(
            tokenizer=tokenizer,
            serializer_provider=serializer,
            merge_peers=True,
        )
        return chunker

    def _extract_image_attachments(
        self,
        document: DoclingDocument,
        folder: StoragePath,
        pipeline_id: PipelineID,
    ) -> dict[str, Attachment]:
        """Extract images from the document and replace them with references."""
        attachments = {}
        for idx, item in enumerate(document.tables):
            content = item.export_to_dataframe(document)
            assert (
                content is not None
            ), f"Failed to extract image content for TableItem {item.self_ref}"

            attachment = Attachment.create(
                pipeline_id=pipeline_id,
                location=folder.resolve(f"table_{idx}.csv"),
                attachment_type=AttachmentTypes.TABLE,
                metadata={"caption": item.caption_text(document)},
                content=Content.from_csv(content),
            )
            logging.info(item.model_dump_json(indent=2))

            assert (
                attachment is not None
            ), f"Failed to create attachment for TableItem {item.self_ref}"
            attachments[item.self_ref] = attachment

        return attachments

    def _extract_table_attachments(
        self,
        document: DoclingDocument,
        folder: StoragePath,
        pipeline_id: PipelineID,
    ) -> dict[str, Attachment]:
        """Extract images from the document and replace them with references."""
        attachments = {}
        for idx, item in enumerate(document.pictures):
            location = folder.resolve(f"picture_{idx}.jpg")
            content = item.get_image(document)

            assert (
                content is not None
            ), f"Failed to extract image content for TableItem {item.self_ref}"
            assert (
                item.image is not None and item.image.uri is not None
            ), f"PictureItem {item.self_ref} is missing image URI"
            item.image.uri = AnyUrl(location.s3_uri)

            attachment = Attachment.create(
                pipeline_id=pipeline_id,
                location=location,
                attachment_type=AttachmentTypes.IMAGE,
                metadata={
                    "caption": item.caption_text(document),
                    "description": getattr(item.meta, "description", None),
                },
                content=Content.from_image(content),
            )
            assert (
                attachment is not None
            ), f"Failed to create attachment for PictureItem {item.self_ref}"
            attachments[item.self_ref] = attachment

        return attachments

    def _extract_attachments(
        self,
        document: DoclingDocument,
        folder: StoragePath,
        pipeline_id: PipelineID,
    ) -> dict[str, Attachment]:
        image_attachment = self._extract_image_attachments(
            document=document,
            folder=folder.at("images"),
            pipeline_id=pipeline_id,
        )

        table_attachment = self._extract_table_attachments(
            document=document,
            folder=folder.at("tables"),
            pipeline_id=pipeline_id,
        )
        return {**image_attachment, **table_attachment}

    async def extract(
        self,
        folder: StoragePath,
        pipeline_id: PipelineID,
        extraction_settings: ExtractionSettings,
        url: AnyUrl,
    ) -> Document:

        result = Document(
            identity=DocumentID.from_ref("filename", pipeline_id=pipeline_id),
            metadata=DocumentMetadata(
                title="#Filename", source_url=url.encoded_string()
            ),
        )

        logging.info(
            f"Starting extraction for URL: {url} with config: {extraction_settings}"
        )
        converter = DocumentConverter(
            allowed_formats=[
                InputFormat.PDF,
                InputFormat.DOCX,
                InputFormat.PPTX,
                InputFormat.HTML,
                InputFormat.IMAGE,
                InputFormat.ASCIIDOC,
                InputFormat.MD,
                InputFormat.CSV,
                InputFormat.JSON_DOCLING,
                InputFormat.AUDIO,
                InputFormat.VTT,
                InputFormat.LATEX,
            ],
            format_options={
                InputFormat.PDF: PdfFormatOption(
                    pipeline_options=self.pdf(extraction_settings)
                )
            },
        )

        conversion = converter.convert(str(url))
        doc = conversion.document

        # Ensure document was successfully converted
        if doc is None:
            raise DomainError(f"Failed to convert document {url}: No document produced")

        chunker = self.chunker(extraction_settings)
        attachments = self._extract_attachments(
            document=doc,
            folder=folder,
            pipeline_id=pipeline_id,
        )

        assert doc is not None, "Document conversion failed, no document produced"
        for idx, element in enumerate(chunker.chunk(doc)):

            chunk = Chunk.create(
                content=element.text,
                document_id=result.identity,
                reference=f"#Filename/#chunk-{idx}",
            )

            assert element.meta is not None, f"Chunk {idx} is missing metadata"

            for item in getattr(element.meta, "doc_items", []):
                reference = getattr(item, "self_ref", None)
                assert (
                    reference is not None
                ), f"Doc item in chunk {idx} is missing self_ref"
                if reference in attachments:
                    chunk.add_attachment(attachments.pop(reference))

            result.add_chunk(chunk)

        return result
