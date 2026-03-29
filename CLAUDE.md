# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Dependencies (uses uv)
make sync          # Install/sync dependencies
make install       # Install with dev dependencies

# Development
make run           # Start FastAPI dev server (uvicorn)
make docker-up     # Start local services (Postgres, MinIO, Redis)
make docker-down   # Stop local services
make dev-setup     # Full local environment setup
make migrate       # Run Alembic database migrations

# Testing
make test          # Run all tests (verbose)
make test-cov      # Run tests with HTML coverage report
make test-all      # Full CI pipeline: lint + type-check + test-cov

# Code quality
make lint          # Ruff linting
make format        # Black formatting
make type-check    # MyPy strict type checking
```

To run a single test file:
```bash
uv run pytest tests/unit/domain/aggregates/test_workspace.py -v
```

## Architecture

This is a RAG (Retrieval Augmented Generation) backend service using **Clean Architecture** with Domain-Driven Design. The package is named `dacke` and lives in `src/dacke/`.

### Layer hierarchy

```
Controllers  →  Application (Use Cases / Services)  →  Domain  ←  Infrastructure
```

- **`domain/`** — Pure business logic: aggregates (`Workspace`, `Collection`, `Artifact`, `Pipeline`, `Document`), value objects (`ArtifactID`, `ArtifactMetadata`, `ObjectAddress`, `ExtractionSettings`), and ports (interfaces).
- **`application/`** — Use cases (e.g. `UploadFileUseCase`, `PromotePipelineUseCase`) and service handlers. No framework dependencies.
- **`controllers/`** — FastAPI routers for 4 resources: workspaces, collections, artifacts, pipelines.
- **`infrastructure/`** — Concrete implementations: SQLAlchemy repositories (Postgres), MinIO blob storage, Celery task queue, Docling/MLX extractors.
- **`dto/`** — Pydantic DTOs for API request/response serialization.

### Dependency injection

`infrastructure/dependencies.py` contains the `App` class — the DI container. It instantiates all repositories, use cases, event bus, and Celery tasks, and is passed as FastAPI app state in `app.py`.

### Domain hierarchy

`Workspace → Collections → Artifacts` (cascade delete). Collections enforce limits: 100 files max, 10 MB per file. `Pipeline` belongs to a `Collection` and has a lifecycle: `STAGING → PRODUCTION → ARCHIVED`.

### Storage

Artifacts are stored in MinIO (S3-compatible). The `ObjectAddress` value object tracks bucket/prefix/filename. Metadata is persisted in Postgres via `ArtifactMetadataRepository`; binary content via `ArtifactBlobRepository`.

### Async task processing

Celery + Redis handles background tasks (document extraction, artifact cleanup). The `Dispatcher` port abstracts task submission; `Handler` handles domain events via the event bus in `infrastructure/bus.py`.

### Document processing pipeline

`DoclingExtractor` (in `infrastructure/pipeline/`) uses the Docling library to extract content from uploaded files. `TransformerRegistry` supports pluggable transformers; `IdentityTransformer` is the no-op base implementation. MLX/MLX-LM and EasyOCR provide ML capabilities.

## Local environment

Copy `.env.example` to `.env`. Run `make docker-up` to start Postgres (5432), MinIO (9000/9001), and Redis (6379). Integration tests require these services running.

## Database migrations

Managed with Alembic. Config in `alembic.ini`, migrations in `alembic/`. Run `make migrate` to apply.
