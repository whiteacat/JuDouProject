"""create notifications table + notify settings

Revision ID: b8c9d0e1f2a3
Revises: a7b8c9d0e1f2
Create Date: 2026-09-14

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "b8c9d0e1f2a3"
down_revision: Union[str, None] = "a7b8c9d0e1f2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "notifications",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("type", sa.String(32), nullable=False),
        sa.Column("title", sa.String(64), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("target_type", sa.String(16), nullable=True),
        sa.Column("target_id", sa.BigInteger(), nullable=True),
        sa.Column("actor_id", sa.BigInteger(), nullable=True),
        sa.Column("actor_name", sa.String(64), nullable=True),
        sa.Column("is_read", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index(
        "idx_notifications_user",
        "notifications",
        ["user_id", "is_read", sa.text("created_at DESC")],
    )
    # 通知配置开关（沿用 app_settings 键值表；value 列为 Boolean，需传布尔值）
    conn = op.get_bind()
    for key in ("notify_enabled", "notify_member_join", "notify_review"):
        conn.execute(
            sa.text(
                "INSERT INTO app_settings (key, value, updated_at) "
                "VALUES (:k, :v, now()) "
                "ON CONFLICT (key) DO NOTHING"
            ),
            {"k": key, "v": True},
        )


def downgrade() -> None:
    op.drop_table("notifications")
    conn = op.get_bind()
    conn.execute(
        sa.text(
            "DELETE FROM app_settings WHERE key IN "
            "('notify_enabled', 'notify_member_join', 'notify_review')"
        )
    )
