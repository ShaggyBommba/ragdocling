from dacke.application.ports.extractor import Extractor
from dacke.domain.aggregates.document import Document
from dacke.domain.values.extraction import ExtractionSettings
from docling.datamodel.accelerator_options import AcceleratorOptions
from docling.datamodel.pipeline_options import (
    CodeFormulaVlmOptions,
    EasyOcrOptions,
    PdfPipelineOptions,
    PictureDescriptionApiOptions,
    PictureDescriptionVlmEngineOptions,
    TableFormerMode,
    TableStructureOptions,
)
from pydantic import AnyUrl, HttpUrl


class DoclingExtractor(Extractor[ExtractionSettings, Document]):
    def options(self, request: ExtractionSettings) -> PdfPipelineOptions:
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

    async def extract(self, config: ExtractionSettings, url: HttpUrl) -> Document:
        options = self.options(config)
        return Document()
