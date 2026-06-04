import enum
from datetime import datetime

from sqlalchemy import (
    BigInteger, Boolean, CheckConstraint, DateTime, Enum, ForeignKey,
    Index, Integer, String, Text, func,
)
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class CardType(str, enum.Enum):
    NEWS = "NEWS"
    TECHNIQUE = "TECHNIQUE"


class Category(str, enum.Enum):
    CODING = "CODING"
    DESIGN = "DESIGN"
    GENERAL = "GENERAL"


class Difficulty(str, enum.Enum):
    BEGINNER = "BEGINNER"
    INTERMEDIATE = "INTERMEDIATE"
    ADVANCED = "ADVANCED"


class OriginalLang(str, enum.Enum):
    KO = "KO"
    EN = "EN"
    JA = "JA"
    ZH = "ZH"


class SourceGroup(str, enum.Enum):
    NEWS_RSS = "NEWS_RSS"
    GITHUB = "GITHUB"
    ENG_BLOG = "ENG_BLOG"
    NEWSLETTER = "NEWSLETTER"


class Card(Base):
    __tablename__ = "cards"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    card_type: Mapped[CardType] = mapped_column(Enum(CardType, name="card_type_enum"), nullable=False)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)

    # NEWS 전용
    key_points: Mapped[list[str] | None] = mapped_column(ARRAY(Text), nullable=True)

    # TECHNIQUE 전용
    problem: Mapped[str | None] = mapped_column(Text, nullable=True)
    idea: Mapped[str | None] = mapped_column(Text, nullable=True)
    code_snippet: Mapped[str | None] = mapped_column(Text, nullable=True)
    caveats: Mapped[list[str] | None] = mapped_column(ARRAY(Text), nullable=True)
    prerequisites: Mapped[str | None] = mapped_column(Text, nullable=True)

    source_url: Mapped[str] = mapped_column(String(2048), nullable=False, unique=True)
    source_name: Mapped[str] = mapped_column(String(200), nullable=False)
    source_group: Mapped[SourceGroup] = mapped_column(
        Enum(SourceGroup, name="source_group_enum"), nullable=False
    )
    original_lang: Mapped[OriginalLang] = mapped_column(
        Enum(OriginalLang, name="original_lang_enum"), nullable=False, default=OriginalLang.EN
    )
    category: Mapped[Category] = mapped_column(
        Enum(Category, name="category_enum"), nullable=False, default=Category.GENERAL
    )
    difficulty: Mapped[Difficulty] = mapped_column(
        Enum(Difficulty, name="difficulty_enum"), nullable=False, default=Difficulty.BEGINNER
    )
    thumbnail_url: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    like_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    bookmark_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    # 역번역 검증 통과 카드만 공개 피드/검색에 노출. 실패 카드는 비공개 초안으로
    # 저장되어 관리자 번역 검토 큐에서 승인 대기한다.
    is_published: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="true")
    batch_id: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    published_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    tags: Mapped[list["Tag"]] = relationship(
        "Tag", secondary="card_tags", back_populates="cards", lazy="selectin"
    )
    card_tags: Mapped[list["CardTag"]] = relationship("CardTag", back_populates="card")
    translation_logs: Mapped[list["TranslationLog"]] = relationship(  # noqa: F821
        "TranslationLog", back_populates="card"
    )

    __table_args__ = (
        CheckConstraint(
            "(card_type = 'NEWS' AND key_points IS NOT NULL AND problem IS NULL) OR "
            "(card_type = 'TECHNIQUE' AND problem IS NOT NULL AND idea IS NOT NULL)",
            name="card_type_fields",
        ),
        Index("idx_cards_feed", "is_published", "category", "card_type", "published_at"),
    )


class Tag(Base):
    __tablename__ = "tags"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    slug: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    category: Mapped[str | None] = mapped_column(String(50), nullable=True)

    cards: Mapped[list["Card"]] = relationship(
        "Card", secondary="card_tags", back_populates="tags", lazy="selectin"
    )


class CardTag(Base):
    __tablename__ = "card_tags"

    card_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("cards.id", ondelete="CASCADE"), primary_key=True)
    tag_id: Mapped[int] = mapped_column(Integer, ForeignKey("tags.id", ondelete="CASCADE"), primary_key=True)

    card: Mapped["Card"] = relationship("Card", back_populates="card_tags")
    tag: Mapped["Tag"] = relationship("Tag")

    __table_args__ = (
        Index("idx_card_tags_tag", "tag_id"),
    )


# 순환 import 방지용 forward reference
from app.models.batch import TranslationLog  # noqa: E402, F401
