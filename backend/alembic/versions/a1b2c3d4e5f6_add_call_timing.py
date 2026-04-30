"""add call timing columns to optimization_runs

Revision ID: a1b2c3d4e5f6
Revises: 705784e1396b
Create Date: 2026-04-29 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, Sequence[str], None] = '705784e1396b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'optimization_runs',
        sa.Column('call_scheduled_at', sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        'optimization_runs',
        sa.Column('call_attempted_at', sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column('optimization_runs', 'call_attempted_at')
    op.drop_column('optimization_runs', 'call_scheduled_at')
