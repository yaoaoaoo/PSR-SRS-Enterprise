"""0002_add_client_event_id

Revision ID: 1d69fffd1e6b
Revises: cfe827193ef4
Create Date: 2026-06-19 00:48:56.538946

Adds ``client_event_id`` column to events, and synchronises
``users.price_preference`` from 0001's Float to the current ORM's
String(32) using SQLite-compatible batch_alter_table.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '1d69fffd1e6b'
down_revision: Union[str, None] = 'cfe827193ef4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Add client_event_id to events
    op.add_column(
        'events',
        sa.Column(
            'client_event_id',
            sa.String(length=64),
            nullable=True,
            comment='Client-generated idempotency key',
        ),
    )
    op.create_index(
        op.f('ix_events_client_event_id'),
        'events', ['client_event_id'], unique=True,
    )

    # 2. Fix users.price_preference: Float -> String(32)
    #    The MVP CSV has string values ("mid_range", "premium", "budget").
    with op.batch_alter_table('users') as batch_op:
        batch_op.alter_column(
            'price_preference',
            existing_type=sa.FLOAT(),
            type_=sa.String(length=32),
            existing_nullable=True,
        )


def downgrade() -> None:
    # Reverse order of upgrade

    # 1. Restore users.price_preference: String(32) -> Float
    with op.batch_alter_table('users') as batch_op:
        batch_op.alter_column(
            'price_preference',
            existing_type=sa.String(length=32),
            type_=sa.FLOAT(),
            existing_nullable=True,
        )

    # 2. Remove client_event_id
    op.drop_index(op.f('ix_events_client_event_id'), table_name='events')
    op.drop_column('events', 'client_event_id')
