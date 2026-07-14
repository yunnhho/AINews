"""그룹 D-2 — IMAP 이메일 뉴스레터 수집 (4개)."""
from pipeline.adapters.base import RawItem
from pipeline.adapters.imap import IMAPAdapter
from pipeline.sources.common import collect_sources

# (sender, name)
_D2_SOURCES: list[tuple[str, str]] = [
    ("dan@tldrnewsletter.com", "TLDR AI"),
    ("bens-bites@bensbites.beehiiv.com", "Ben's Bites"),
    ("therundownai@mail.beehiiv.com", "The Rundown AI"),
    ("contact@aiweekly.co", "AI Engineer Weekly"),
]


def collect_group_d2() -> list[RawItem]:
    """D-2 IMAP 이메일 뉴스레터 수집."""
    fetchers = [
        (name, IMAPAdapter(sender_email=sender, source_name=name).fetch)
        for sender, name in _D2_SOURCES
    ]
    return collect_sources("Group D-2", "NEWSLETTER", fetchers)
