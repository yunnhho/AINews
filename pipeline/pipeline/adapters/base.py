"""어댑터 공통 인터페이스 + RawItem 데이터 클래스."""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


class SourceGroup(str, Enum):
    NEWS_RSS = "NEWS_RSS"
    GITHUB = "GITHUB"
    ENG_BLOG = "ENG_BLOG"
    NEWSLETTER = "NEWSLETTER"


@dataclass
class RawItem:
    url: str
    title: str
    content: str
    published_at: datetime
    source_name: str
    source_group: SourceGroup
    original_lang: str          # "en" | "ko"
    extra: dict = field(default_factory=dict)


class BaseAdapter(ABC):
    source_name: str = ""
    source_group: SourceGroup = SourceGroup.NEWS_RSS

    @abstractmethod
    def fetch(self, since: datetime) -> list[RawItem]:
        """since 이후 게시된 아이템 반환."""
        ...
