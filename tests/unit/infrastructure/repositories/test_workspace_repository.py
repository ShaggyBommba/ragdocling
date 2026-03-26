"""Tests for WorkspaceRepository."""

from collections.abc import AsyncIterator

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from dacke.domain.aggregates.workspace import Workspace
from dacke.infrastructure.repositories.providers.postgres.models import WorkspacesTable
from dacke.infrastructure.repositories.providers.postgres.repo_workspace import (
    WorkspaceAcl,
    WorkspaceRepository,
)

pytest_plugins = ("pytest_asyncio",)


class TestWorkspaceAcl:
    """Test WorkspaceAcl translation layer."""

    @pytest.fixture
    def acl(self) -> WorkspaceAcl:
        return WorkspaceAcl()

    @pytest.fixture
    def workspace(self) -> Workspace:
        return Workspace.create("Test Workspace")

    def test_roundtrip_conversion(self, acl: WorkspaceAcl, workspace: Workspace) -> None:
        """Test roundtrip conversion domain -> ORM -> domain."""
        orm = acl.from_domain(workspace)
        domain = acl.to_domain(orm)

        assert domain.identity.value == workspace.identity.value
        assert domain.name == workspace.name
        assert domain.collection_ids == workspace.collection_ids


class TestWorkspaceRepository:
    """Test WorkspaceRepository persistence operations."""

    @pytest_asyncio.fixture
    async def repository(self) -> AsyncIterator[WorkspaceRepository]:
        """Create repository instance with in-memory database."""
        engine = create_async_engine(
            "sqlite+aiosqlite:///:memory:",
            echo=False,
        )
        async with engine.begin() as conn:
            await conn.run_sync(WorkspacesTable.metadata.create_all)

        repo = WorkspaceRepository("sqlite+aiosqlite:///:memory:")
        repo._engine = engine
        repo._client = async_sessionmaker(
            bind=engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )
        yield repo
        await engine.dispose()

    @pytest.mark.asyncio
    async def test_save_workspace(self, repository: WorkspaceRepository) -> None:
        """Test saving a workspace aggregate."""
        workspace = Workspace.create("Test Workspace")
        await repository.create(workspace)
        assert workspace.identity.value is not None

    @pytest.mark.asyncio
    async def test_get_workspace_by_name(self, repository: WorkspaceRepository) -> None:
        """Test retrieving a workspace by name."""
        workspace = Workspace.create("Test Workspace")
        await repository.create(workspace)
        retrieved = await repository.get_by_name("Test Workspace")
        assert retrieved is not None
        assert retrieved.name == "Test Workspace"

    @pytest.mark.asyncio
    async def test_get_all_workspaces(self, repository: WorkspaceRepository) -> None:
        """Test retrieving all workspaces."""
        workspace1 = Workspace.create("Workspace 1")
        workspace2 = Workspace.create("Workspace 2")
        await repository.create(workspace1)
        await repository.create(workspace2)
        all_workspaces = await repository.get_all()
        assert len(all_workspaces) >= 2

    @pytest.mark.asyncio
    async def test_delete_workspace(self, repository: WorkspaceRepository) -> None:
        """Test deleting a workspace."""
        workspace = Workspace.create("To Delete")
        await repository.create(workspace)
        await repository.delete(workspace)
        retrieved = await repository.get_by_name("To Delete")
        assert retrieved is None

    @pytest.mark.asyncio
    async def test_workspace_not_found(self, repository: WorkspaceRepository) -> None:
        """Test retrieving non-existent workspace returns None."""
        retrieved = await repository.get_by_name("NonExistent")
        assert retrieved is None
