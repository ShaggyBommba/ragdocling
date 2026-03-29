import logging

from collections.abc import AsyncGenerator

from contextlib import asynccontextmanager

from fastapi import FastAPI

from fastapi.middleware.cors import CORSMiddleware

from dacke.controllers.artifact import router as artifact_router

from dacke.controllers.collection import router as collection_router

from dacke.controllers.pipeline import router as pipeline_router

from dacke.controllers.workspace import router as workspace_router

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    from dacke.infrastructure.config import AppSettings
    from dacke.infrastructure.dependencies import App
    from dacke.infrastructure.utility.logging import LoggingSetup

    settings = AppSettings()
    LoggingSetup.setup(settings.logging)

    wireframe: App = App()
    app.state.wireframe = wireframe
    await wireframe.startup()
    yield
    await wireframe.shutdown()


def build() -> FastAPI:
    """Factory function to build the FastAPI app."""

    # Create ASGI app at module level
    app = FastAPI(title="Dacke Service", version="1.0.0", lifespan=lifespan)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Register routers
    app.include_router(workspace_router)
    app.include_router(collection_router)
    app.include_router(artifact_router)
    app.include_router(pipeline_router)

    return app


app = build()
