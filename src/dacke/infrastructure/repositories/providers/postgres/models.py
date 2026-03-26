"""Base ORM model with common columns."""

from datetime import datetime
from typing import Any

from sqlalchemy import (
    JSON,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
)
from sqlalchemy import (
    Enum as SQLAlchemyEnum,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

from dacke.domain.values.pipeline import PipelineLifecycle


class Base(DeclarativeBase):
    pass


class BaseTable(Base):
    """Abstract base class for all ORM models."""

    __abstract__ = True

    id: Mapped[str] = mapped_column(String(36), primary_key=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.now, onupdate=datetime.now
    )


class ArtifactsTable(BaseTable):
    """SQLAlchemy model for artifacts table."""

    __tablename__ = "artifacts"

    collection_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("collections.id", ondelete="CASCADE"), nullable=False
    )
    object_address: Mapped[str] = mapped_column(String(255), nullable=False)
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    source: Mapped[str] = mapped_column(String(50), nullable=False)
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    mime_type: Mapped[str] = mapped_column(String(100), nullable=False)
    checksum: Mapped[str] = mapped_column(String(255), nullable=False)

    # Author is nullable, so we use str | None for correct type checking
    author: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Integrated metadata from the old FileMetadataTable
    metadata_json: Mapped[dict[str, Any]] = mapped_column(
        "metadata", JSON, nullable=False, default=dict
    )

    collection: Mapped["CollectionsTable"] = relationship(
        "CollectionsTable",
        back_populates="artifacts",
    )


class PipelinesTable(BaseTable):
    """SQLAlchemy model for pipelines table."""

    __tablename__ = "pipelines"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    collection_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("collections.id", ondelete="CASCADE"),
        nullable=False,
    )
    lifecycle: Mapped[PipelineLifecycle] = mapped_column(
        SQLAlchemyEnum(PipelineLifecycle),
        nullable=False,
        default=PipelineLifecycle.STAGING,
    )
    transformations_settings: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    extraction_settings: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)

    collection = relationship(
        "CollectionsTable",
        lazy="select",
        back_populates="pipelines",
        passive_deletes=True,
    )


class CollectionsTable(BaseTable):
    """SQLAlchemy model for collections table."""

    __tablename__ = "collections"

    workspace_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    max_count_files: Mapped[int] = mapped_column(Integer, nullable=False, default=100)
    max_file_size_kb: Mapped[float] = mapped_column(Float, nullable=False, default=10240.0)

    workspace = relationship(
        "WorkspacesTable",
        lazy="select",
        back_populates="collections",
        passive_deletes=True,
    )

    artifacts = relationship(
        "ArtifactsTable",
        lazy="select",
        cascade="all",
        back_populates="collection",
        passive_deletes=True,
    )

    pipelines = relationship(
        "PipelinesTable",
        lazy="select",
        cascade="all",
        back_populates="collection",
        passive_deletes=True,
    )


class WorkspacesTable(BaseTable):
    """SQLAlchemy model for workspaces table."""

    __tablename__ = "workspaces"

    name: Mapped[str] = mapped_column(String(255), nullable=False)

    collections = relationship(
        "CollectionsTable",
        lazy="select",
        cascade="all",
        back_populates="workspace",
        passive_deletes=True,
    )
