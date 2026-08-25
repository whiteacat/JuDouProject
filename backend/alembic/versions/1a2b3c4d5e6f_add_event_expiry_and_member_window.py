"""add event expiry policy and member time window

Revision ID: 1a2b3c4d5e6f
Revises: d71862f1629e
Create Date: 2026-08-24

"""
import sqlalchemy as sa

from alembic import op

revision = '1a2b3c4d5e6f'
down_revision = 'd71862f1629e'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        'group_events',
        sa.Column('expiry_mode', sa.String(length=16), nullable=False,
                  server_default='none'),
    )
    op.add_column(
        'group_events',
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True),
    )
    # 存量行：默认长期有效，无需回填
    op.add_column(
        'event_members',
        sa.Column('window_start', sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        'event_members',
        sa.Column('window_end', sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column('event_members', 'window_end')
    op.drop_column('event_members', 'window_start')
    op.drop_column('group_events', 'expires_at')
    op.drop_column('group_events', 'expiry_mode')
