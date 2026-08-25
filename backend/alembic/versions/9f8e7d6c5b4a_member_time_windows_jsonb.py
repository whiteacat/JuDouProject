"""member time windows: single window_start/window_end -> time_windows JSONB (multi-day multi-segment)

Revision ID: 9f8e7d6c5b4a
Revises: 1a2b3c4d5e6f
Create Date: 2026-08-24

存量数据转换：window_start/window_end 均为 NOT NULL 时折算为单段
[{"date": 聚餐日, "start": "HH:mm", "end": "HH:mm"}]，本地时区（+08:00）；
空值行置 '[]'。
"""
import sqlalchemy as sa

from alembic import op
from sqlalchemy.dialects import postgresql

revision = '9f8e7d6c5b4a'
down_revision = '1a2b3c4d5e6f'
branch_labels = None
depends_on = None


CONVERT_SQL = sa.text(
    """
    UPDATE event_members
    SET time_windows = jsonb_build_array(
          jsonb_build_object(
            'date', to_char(window_start AT TIME ZONE '+08:00', 'YYYY-MM-DD'),
            'start', to_char(window_start AT TIME ZONE '+08:00', 'HH24:MI'),
            'end', to_char(window_end AT TIME ZONE '+08:00', 'HH24:MI')
          )
        )
    WHERE window_start IS NOT NULL AND window_end IS NOT NULL
    """
)


def upgrade() -> None:
    op.add_column(
        'event_members',
        sa.Column('time_windows', postgresql.JSONB(astext_type=sa.Text()),
                  nullable=False, server_default=sa.text("'[]'::jsonb")),
    )
    # 存量单窗口折算为多段结构（单段）
    op.execute(CONVERT_SQL)
    op.drop_column('event_members', 'window_start')
    op.drop_column('event_members', 'window_end')


def downgrade() -> None:
    op.add_column(
        'event_members',
        sa.Column('window_start', sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        'event_members',
        sa.Column('window_end', sa.DateTime(timezone=True), nullable=True),
    )
    op.execute(
        sa.text(
            """
            UPDATE event_members
            SET window_start = (time_windows->0->>'date')::date + (time_windows->0->>'start')::time,
                window_end   = (time_windows->0->>'date')::date + (time_windows->0->>'end')::time
            WHERE jsonb_array_length(time_windows) >= 1
            """
        )
    )
    op.drop_column('event_members', 'time_windows')
