"""initial schema

Revision ID: 0001
Revises:
Create Date: 2026-05-26 00:00:00.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # ── Enum 타입 ────────────────────────────────────────────────
    card_type_enum = postgresql.ENUM(
        "NEWS", "TECHNIQUE", name="card_type_enum", create_type=False
    )
    card_type_enum.create(op.get_bind(), checkfirst=True)

    category_enum = postgresql.ENUM(
        "CODING", "DESIGN", "GENERAL", name="category_enum", create_type=False
    )
    category_enum.create(op.get_bind(), checkfirst=True)

    difficulty_enum = postgresql.ENUM(
        "BEGINNER", "INTERMEDIATE", "ADVANCED", name="difficulty_enum", create_type=False
    )
    difficulty_enum.create(op.get_bind(), checkfirst=True)

    original_lang_enum = postgresql.ENUM(
        "KO", "EN", "JA", "ZH", name="original_lang_enum", create_type=False
    )
    original_lang_enum.create(op.get_bind(), checkfirst=True)

    source_group_enum = postgresql.ENUM(
        "NEWS_RSS", "GITHUB", "ENG_BLOG", "NEWSLETTER", name="source_group_enum", create_type=False
    )
    source_group_enum.create(op.get_bind(), checkfirst=True)

    batch_status_enum = postgresql.ENUM(
        "SCHEDULED", "RUNNING", "COMPLETED", "PARTIAL_FAILURE", "FAILED",
        name="batch_status_enum", create_type=False,
    )
    batch_status_enum.create(op.get_bind(), checkfirst=True)

    # ── users ────────────────────────────────────────────────────
    op.create_table(
        "users",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("provider", sa.String(50), nullable=False),
        sa.Column("provider_id", sa.String(200), nullable=False),
        sa.Column("nickname", sa.String(100), nullable=False),
        sa.Column("avatar_url", sa.String(2048), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("provider", "provider_id", name="uq_user_provider"),
    )

    # ── tags ─────────────────────────────────────────────────────
    op.create_table(
        "tags",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("slug", sa.String(100), nullable=False),
        sa.Column("category", sa.String(50), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
        sa.UniqueConstraint("slug"),
    )

    # ── cards ────────────────────────────────────────────────────
    op.create_table(
        "cards",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("card_type", postgresql.ENUM("NEWS", "TECHNIQUE", name="card_type_enum", create_type=False), nullable=False),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("key_points", postgresql.ARRAY(sa.Text()), nullable=True),
        sa.Column("problem", sa.Text(), nullable=True),
        sa.Column("idea", sa.Text(), nullable=True),
        sa.Column("code_snippet", sa.Text(), nullable=True),
        sa.Column("caveats", postgresql.ARRAY(sa.Text()), nullable=True),
        sa.Column("prerequisites", sa.Text(), nullable=True),
        sa.Column("source_url", sa.String(2048), nullable=False),
        sa.Column("source_name", sa.String(200), nullable=False),
        sa.Column("source_group", postgresql.ENUM("NEWS_RSS", "GITHUB", "ENG_BLOG", "NEWSLETTER", name="source_group_enum", create_type=False), nullable=False),
        sa.Column("original_lang", postgresql.ENUM("KO", "EN", "JA", "ZH", name="original_lang_enum", create_type=False), nullable=False, server_default="EN"),
        sa.Column("category", postgresql.ENUM("CODING", "DESIGN", "GENERAL", name="category_enum", create_type=False), nullable=False, server_default="GENERAL"),
        sa.Column("difficulty", postgresql.ENUM("BEGINNER", "INTERMEDIATE", "ADVANCED", name="difficulty_enum", create_type=False), nullable=False, server_default="BEGINNER"),
        sa.Column("thumbnail_url", sa.String(2048), nullable=True),
        sa.Column("like_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("bookmark_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("batch_id", sa.String(100), nullable=True),
        sa.Column("published_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint(
            "(card_type = 'NEWS' AND key_points IS NOT NULL AND problem IS NULL) OR "
            "(card_type = 'TECHNIQUE' AND problem IS NOT NULL AND idea IS NOT NULL)",
            name="card_type_fields",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("source_url"),
    )

    # ── card_tags ────────────────────────────────────────────────
    op.create_table(
        "card_tags",
        sa.Column("card_id", sa.BigInteger(), nullable=False),
        sa.Column("tag_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["card_id"], ["cards.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["tag_id"], ["tags.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("card_id", "tag_id"),
    )

    # ── user_likes ───────────────────────────────────────────────
    op.create_table(
        "user_likes",
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("card_id", sa.BigInteger(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["card_id"], ["cards.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("user_id", "card_id"),
        sa.UniqueConstraint("user_id", "card_id", name="uq_user_likes"),
    )

    # ── user_bookmarks ───────────────────────────────────────────
    op.create_table(
        "user_bookmarks",
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("card_id", sa.BigInteger(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["card_id"], ["cards.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("user_id", "card_id"),
        sa.UniqueConstraint("user_id", "card_id", name="uq_user_bookmarks"),
    )

    # ── batch_logs ───────────────────────────────────────────────
    op.create_table(
        "batch_logs",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("batch_id", sa.String(100), nullable=False),
        sa.Column("scheduled_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", postgresql.ENUM("SCHEDULED", "RUNNING", "COMPLETED", "PARTIAL_FAILURE", "FAILED", name="batch_status_enum", create_type=False), nullable=False, server_default="SCHEDULED"),
        sa.Column("collected_by_group", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("deduplicated_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("published_by_type", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("failed_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("api_tokens_used", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("api_cost_usd", sa.Numeric(10, 6), nullable=False, server_default="0"),
        sa.Column("error_log", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("batch_id", name="uq_batch_id"),
    )

    # ── translation_logs ─────────────────────────────────────────
    op.create_table(
        "translation_logs",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("card_id", sa.BigInteger(), nullable=False),
        sa.Column("original_text", sa.Text(), nullable=False),
        sa.Column("translated_text", sa.Text(), nullable=False),
        sa.Column("back_translated_text", sa.Text(), nullable=True),
        sa.Column("similarity_score", sa.Float(), nullable=True),
        sa.Column("passed", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("retry_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["card_id"], ["cards.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )

    # ── source_health ─────────────────────────────────────────────
    op.create_table(
        "source_health",
        sa.Column("source_id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("source_name", sa.String(200), nullable=False),
        sa.Column("source_group", sa.String(50), nullable=False),
        sa.Column("last_success_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("consecutive_failures", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_error_log", sa.Text(), nullable=True),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default="true"),
        sa.PrimaryKeyConstraint("source_id"),
        sa.UniqueConstraint("source_name"),
    )

    # ── 인덱스 ───────────────────────────────────────────────────
    op.create_index("idx_cards_feed", "cards", ["category", "card_type", "published_at"])
    op.create_index("idx_cards_batch", "cards", ["batch_id"])
    op.create_index("idx_card_tags_tag", "card_tags", ["tag_id"])
    op.create_index("idx_bookmarks_user", "user_bookmarks", ["user_id", "created_at"])
    op.create_index("idx_batch_logs_scheduled", "batch_logs", ["scheduled_at"])
    op.create_index("idx_source_health_group", "source_health", ["source_group", "enabled"])


def downgrade() -> None:
    op.drop_table("source_health")
    op.drop_table("translation_logs")
    op.drop_table("batch_logs")
    op.drop_table("user_bookmarks")
    op.drop_table("user_likes")
    op.drop_table("card_tags")
    op.drop_table("cards")
    op.drop_table("tags")
    op.drop_table("users")

    for enum_name in [
        "card_type_enum", "category_enum", "difficulty_enum",
        "original_lang_enum", "source_group_enum", "batch_status_enum",
    ]:
        op.execute(f"DROP TYPE IF EXISTS {enum_name}")
