# Architecture

Dacke is a RAG backend built with Clean Architecture and DDD. The entry point is `src/dacke/app.py`; the wiring lives in `src/dacke/infrastructure/dependencies.py`.

---

## Startup sequence

```
uvicorn → app.build() → FastAPI lifespan → App() → app.state.wireframe
```

`app.py` defines a `lifespan` context manager. On startup it instantiates `App` (the DI container), calls `wireframe.startup()` to open DB/blob connections and launch the Celery worker thread, then yields. On shutdown it drains all connections and stops the worker.

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
    ├── Repositories (ports) ──► Postgres / MinIO (infrastructure)
    └── EventBus (port)      ──► DomainEventBus → Celery task queue
                                        │
                                        ▼
                             Celery tasks (background workers)
                                        │
                                        ▼
                             Handlers (application/services/handlers/)
                                        │
                                        ▼
                             DoclingExtractor → Document
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

4. **Handlers** — used by Celery tasks, not the HTTP path:
   - `ConvertArtifactToDocumentHandler` — fetches artifact, gets presigned URL, selects the PRODUCTION pipeline, runs `DoclingExtractor`, applies transformers from `TransformerRegistry`
   - `CleanupArtifactDataHandler` — deletes blob and metadata record

5. **Celery worker** — started as a daemon thread inside `App.startup()`. The worker listens on `artifacts_1` queue with concurrency 2.

---

## Request → response: artifact upload

```
POST /api/v1/workspaces/{ws}/collections/{coll}/artifacts
    │
    ├── validate workspace + collection exist (direct repo calls)
    │
    ├── UploadFileUseCase.execute(ArtifactUploadDTO)
    │       ├── ArtifactBlobRepository.save_blob(...)    → MinIO
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
    │                               └── apply TransformerRegistry transformers
    │
    └── return ArtifactDTO
```

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
| Task queue | Celery + Redis | `infrastructure/celery/` |
| Document extraction | Docling + MLX/EasyOCR | `infrastructure/pipeline/extractor.py` |
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
```

A `Pipeline` holds `ExtractionSettings` that control how `DoclingExtractor` processes artifacts in its collection. Only the `PRODUCTION` pipeline is used for processing.
