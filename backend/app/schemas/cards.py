from datetime import datetime
from typing import Literal

from pydantic import BaseModel

from app.models.card import CardType, Category, Difficulty, OriginalLang, SourceGroup


class TagSchema(BaseModel):
    id: int
    name: str
    slug: str

    model_config = {"from_attributes": True}


class CardBase(BaseModel):
    id: int
    card_type: CardType
    category: Category
    difficulty: Difficulty
    title: str
    summary: str
    source_url: str
    source_name: str
    source_group: SourceGroup
    original_lang: OriginalLang
    thumbnail_url: str | None = None
    like_count: int
    bookmark_count: int
    published_at: datetime
    tags: list[TagSchema] = []
    is_liked: bool = False
    is_bookmarked: bool = False

    model_config = {"from_attributes": True}


class NewsCardResponse(CardBase):
    card_type: Literal[CardType.NEWS] = CardType.NEWS
    key_points: list[str] | None = None


class TechniqueCardResponse(CardBase):
    card_type: Literal[CardType.TECHNIQUE] = CardType.TECHNIQUE
    problem: str | None = None
    idea: str | None = None
    code_snippet: str | None = None
    caveats: list[str] | None = None
    prerequisites: str | None = None


CardResponse = NewsCardResponse | TechniqueCardResponse


class FeedResponse(BaseModel):
    items: list[NewsCardResponse | TechniqueCardResponse]
    next_cursor: str | None = None
    has_more: bool = False
