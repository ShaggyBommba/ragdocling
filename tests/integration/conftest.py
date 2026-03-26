import asyncio

import pytest
from sqlalchemy.ext.asyncio import create_async_engine

from dacke.infrastructure.config import AppSettings
from dacke.infrastructure.repositories.providers.postgres.models import Base


@pytest.fixture(scope="session", autouse=True)
def reset_integration_schema() -> None:
    async def _reset() -> None:
        engine = create_async_engine(AppSettings().database_url)
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
            await conn.run_sync(Base.metadata.create_all)
        await engine.dispose()

    asyncio.run(_reset())
