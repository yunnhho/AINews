"""add cards.is_published for translation review draft state

Revision ID: 0004
Revises: 0003
Create Date: 2026-06-04 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

revision: str = "0004"
down_revision: Union[str, None] = "0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "cards",
        sa.Column(
            "is_published",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
        ),
    )
    # 기존 피드 인덱스를 is_published 선두 컬럼으로 재생성
    op.drop_index("idx_cards_feed", table_name="cards")
    op.create_index(
        "idx_cards_feed",
        "cards",
        ["is_published", "category", "card_type", "published_at"],
    )


def downgrade() -> None:
    op.drop_index("idx_cards_feed", table_name="cards")
    op.create_index(
        "idx_cards_feed",
        "cards",
        ["category", "card_type", "published_at"],
    )
    op.drop_column("cards", "is_published")
