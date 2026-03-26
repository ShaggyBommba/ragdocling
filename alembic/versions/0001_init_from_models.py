"""init from ORM models

Revision ID: 0001_init_from_models
Revises:
Create Date: 2026-03-23 02:52:00
"""

from typing import Sequence, Union

from alembic import op

from dacke.infrastructure.repositories.providers.postgres.models import Base


revision: str = "0001_init_from_models"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create all tables from corrected models
    Base.metadata.create_all(bind=op.get_bind())


def downgrade() -> None:
    # Drop all tables
    Base.metadata.drop_all(bind=op.get_bind())
