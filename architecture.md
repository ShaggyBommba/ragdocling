# Architecture

Dacke is a RAG backend built with Clean Architecture and DDD. The entry point is `src/dacke/app.py`; the wiring lives in `src/dacke/infrastructure/dependencies.py`.

---

## Startup sequence

```
uvicorn → app.build() → FastAPI lifespan → App() → app.state.wireframe
```

`app.py` defines a `lifespan` context manager. On startup it instantiates `App` (the DI container), calls `wireframe.startup()` to open DB/blob/vector connections and launch the Celery worker thread, then yields. On shutdown it drains all connections and stops the worker.

---

## Layer overview

```
HTTP Request
    │
    ▼
Controllers (FastAPI routers)
    │  call use case methods on app.state.wireframe
    ▼
Use Cases (application/services/usecases/)
    │  orchestrate domain logic, publish domain events
    ▼
Domain (aggregates, value objects, events)
    │
    ├── Repositories (ports) ──► Postgres / MinIO / Qdrant (infrastructure)
    └── EventBus (port)      ──► DomainEventBus → Celery task queue
                                        │
                                        ▼
                             Celery tasks (background workers)
                                        │
                                        ▼
                             Handlers (application/services/handlers/)
                                        │
                                        ▼
                             DoclingExtractor → Document → Embedder → Qdrant
```

---

## The DI container: `App`

`App.__init__` builds the entire object graph in order:

1. **Repositories** — instantiated with connection strings from `AppSettings`:
   - `ArtifactBlobRepository` — MinIO (S3-compatible blob storage)
   - `ArtifactMetadataRepository` — Postgres
   - `WorkspaceRepository` — Postgres
   - `CollectionRepository` — Postgres
   - `PipelineRepository` — Postgres
   - `QdrantEmbeddingRepository` — Qdrant (per-pipeline vector collections)

2. **Event bus** — `DomainEventBus` with two registered event→task mappings:
   - `ArtifactUploadedEvent` → `celery_app.send_task("artifacts.upload.1", ...)`
   - `ArtifactDeletedEvent`  → `celery_app.send_task("artifacts.delete.1", ...)`

3. **Use cases** — injected with repos and the bus:
   - `UploadFileUseCase` — saves blob + metadata, publishes `ArtifactUploadedEvent`
   - `DeleteFileUseCase` — deletes blob + metadata, publishes `ArtifactDeletedEvent`
   - `CreateWorkspaceUseCase`
   - `CreateCollectionUseCase`
   - `DemotePipelineUseCase`
   - `ListArtifactsInCollectionUseCase`
   - `RetrieveUseCase` — embeds a query, fetches top-k results from Qdrant, and optionally expands results by following chunk reference URLs

4. **Handlers** — used by Celery tasks, not the HTTP path:
   - `ConvertArtifactToDocumentHandler` — fetches artifact, gets presigned URL, selects the PRODUCTION pipeline, runs `DoclingExtractor`, applies transformers from `TransformerRegistry`, embeds chunks via `OpenAIEmbedder`, removes any existing embeddings for the artifact (overwrite), then persists new embeddings to Qdrant
   - `CleanupArtifactDataHandler` — removes embeddings from Qdrant for all collection pipelines, then deletes blob and metadata record

5. **Celery worker** — started as a daemon thread inside `App.startup()`. The worker listens on `artifacts_1` queue with concurrency 2.

---

## Request → response: artifact upload

```
POST /api/v1/workspaces/{ws}/collections/{coll}/artifacts
    │
    ├── validate workspace + collection exist (direct repo calls)
    │
    ├── UploadFileUseCase.execute(ArtifactUploadDTO)
    │       ├── ArtifactBlobRepository.save_blob(...)         → MinIO
    │       ├── ArtifactMetadataRepository.save_artifact(...) → Postgres
    │       └── DomainEventBus.publish(ArtifactUploadedEvent)
    │               └── celery_app.send_task("artifacts.upload.1", payload)
    │                           │  (async, returns immediately)
    │                           ▼
    │                   convert_artifact_to_document (Celery task)
    │                       └── ConvertArtifactToDocumentHandler.handle(...)
    │                               ├── fetch artifact metadata
    │                               ├── get presigned URL from MinIO
    │                               ├── find PRODUCTION pipeline for collection
    │                               ├── DoclingExtractor.extract(url, settings)
    │                               │       ├── Docling conversion (PDF/DOCX/…)
    │                               │       ├── ImageAttachment (picture_area ≥ threshold)
    │                               │       │     └── LLM description via VLM API
    │                               │       ├── TableAttachment (CSV export)
    │                               │       └── HybridChunker → list[Chunk]
    │                               ├── TransformerRegistry.apply(document)
    │                               │       ├── PatternMatchTransformer (regex → matched_patterns)
    │                               │       └── UrlExtractTransformer (urls)
    │                               ├── OpenAIEmbedder.embed_many(chunks)
    │                               ├── QdrantEmbeddingRepository.delete_by_origin(origin)  ← overwrite
    │                               └── QdrantEmbeddingRepository.save_many(embeddings)
    │
    └── return ArtifactDTO
```

---

## Request → response: retrieve

```
POST /api/v1/workspaces/{ws}/collections/{coll}/pipelines/{pipeline_id}/retrieve
    Body: { "query": "...", "top_k": 5, "reranker": null, "expand_links": true }
    │
    ├── validate workspace + collection exist
    │
    ├── RetrieveUseCase.execute(RetrieveDTO)
    │       ├── PipelineRepository.get_pipeline_by_id(pipeline_id)
    │       ├── OpenAIEmbedder.embed(query_chunk, embedding_settings)
    │       ├── QdrantEmbeddingRepository.search(vector, pipeline_id, top_k)
    │       ├── [optional] Reranker.rerank(query, documents, top_n)
    │       └── [if expand_links] QdrantEmbeddingRepository.fetch_by_origin(referenced_urls)
    │               └── appends linked chunks (score=0.0) to ranked results
    │
    └── return list[RetrieveResultDTO]
          { score, text, title, pages, origin, attachments }
```

---

## Request → response: artifact delete

```
DELETE /api/v1/workspaces/{ws}/collections/{coll}/artifacts/{artifact_id}
    │
    ├── validate workspace + collection exist
    │
    ├── DeleteFileUseCase.execute(DeleteArtifactDTO)
    │       ├── ArtifactMetadataRepository.get_artifact_by_id(artifact_id)
    │       └── DomainEventBus.publish(ArtifactDeletedEvent)
    │               └── celery_app.send_task("artifacts.delete.1", payload)
    │                           │  (async)
    │                           ▼
    │                   cleanup_artifact (Celery task)
    │                       └── CleanupArtifactDataHandler.handle(...)
    │                               ├── fetch artifact metadata (to get origin URL)
    │                               ├── get all pipelines for collection
    │                               ├── QdrantEmbeddingRepository.delete_by_origin(origin, pipeline_id)
    │                               │       └── repeated for each pipeline
    │                               ├── ArtifactBlobRepository.delete_blob(address) → MinIO
    │                               └── ArtifactMetadataRepository.delete_artifact(id) → Postgres
    │
    └── return 204 No Content
```

---

## Document processing pipeline

After extraction, each `Document` contains a list of `Chunk` objects. Each chunk carries:

| Field | Source |
|---|---|
| `content` | Docling serialized text |
| `pages` | minimum page number from provenance |
| `title` | first heading from `element.meta.headings` |
| `origin` | source URL of the artifact |
| `matched_patterns` | set by `PatternMatchTransformer` (e.g. DOI, email, arXiv) |
| `urls` | set by `UrlExtractTransformer` |
| `attachments` | `ImageAttachment` / `TableAttachment` linked by `self_ref` |

Chunks are embedded with the pipeline's `EmbeddingSettings.model` via an OpenAI-compatible `/v1/embeddings` endpoint (default: LM Studio at `http://localhost:1234`). The resulting `Embedding` entities are upserted into Qdrant under collection `embeddings_{pipeline_hex}`.

### Attachment filtering

Pictures below `ExtractionSettings.images.min_area_fraction` (default `0.05` = 5% of page area) are skipped during attachment extraction — matching the Docling VLM description threshold so attachment payloads always have meaningful descriptions.

---

## Event bus and Celery routing

`DomainEventBus` is a synchronous in-process dispatcher. Its registered handlers call `celery_app.send_task(...)` which enqueues a job to Redis. Task routing is configured in `celery/app.py`:

| Event | Task name | Queue |
|---|---|---|
| `ArtifactUploadedEvent` | `artifacts.upload.1` | `artifacts_1` |
| `ArtifactDeletedEvent`  | `artifacts.delete.1` | `artifacts_1` |

Celery tasks call `get_app()` to create a fresh `App` instance (tasks run in worker process/thread, not the web server process).

---

## Infrastructure details

| Component | Technology | Location |
|---|---|---|
| Web framework | FastAPI (uvicorn) | `app.py` |
| Database | Postgres via SQLAlchemy async | `repositories/providers/postgres/` |
| Blob storage | MinIO (aiobotocore) | `repositories/providers/minio/` |
| Vector store | Qdrant (per-pipeline collections) | `repositories/providers/qdrant/` |
| Task queue | Celery + Redis | `infrastructure/celery/` |
| Document extraction | Docling + MLX/EasyOCR | `infrastructure/pipeline/extractor.py` |
| Embeddings | OpenAI-compatible API (LM Studio) | `infrastructure/pipeline/embedder.py` |
| Transformer pipeline | `TransformerRegistry` | `infrastructure/pipeline/registry.py` |
| Config | Pydantic `AppSettings` | `infrastructure/config.py` |
| Migrations | Alembic | `alembic/` |

---

## Domain model relationships

```
Workspace
  └── Collection (many, cascade delete)
        ├── Artifact (many, max 100, max 10 MB each)
        └── Pipeline (lifecycle: STAGING → PRODUCTION → ARCHIVED)
                └── Qdrant collection: embeddings_{pipeline_hex}
```

A `Pipeline` holds `ExtractionSettings` that control how `DoclingExtractor` processes artifacts in its collection. Only the `PRODUCTION` pipeline is used for processing uploaded artifacts. Any pipeline can be queried via the `/retrieve` endpoint.

---

## Configuration (`AppSettings`)

Key environment variables (see `.env.example`):

| Variable | Default | Purpose |
|---|---|---|
| `DATABASE_URL` | — | Postgres async connection string |
| `MINIO_ENDPOINT` | — | MinIO host:port |
| `EMBEDDER_BASE_URL` | `http://localhost:1234` | OpenAI-compatible embedding API |
| `QDRANT_URL` | `http://localhost:6333` | Qdrant server |
| `REDIS_URL` | — | Celery broker / result backend |
