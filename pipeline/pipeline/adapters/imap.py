"""IMAP 수신함 어댑터 — 최근 N시간 이내 이메일 파싱."""
import os
from datetime import datetime, timezone

from pipeline.adapters.base import BaseAdapter, RawItem, SourceGroup

_MAX_CONTENT_LEN = 10_000


class IMAPAdapter(BaseAdapter):
    """IMAP 수신함에서 발신자별 이메일을 읽어 RawItem으로 변환."""

    source_group = SourceGroup.NEWSLETTER

    def __init__(
        self,
        sender_email: str,
        source_name: str,
        host: str = "",
        user: str = "",
        password: str = "",
        mailbox: str = "",
    ):
        self.sender_email = sender_email
        self.source_name = source_name
        self.host = host or os.getenv("IMAP_HOST", "")
        self.user = user or os.getenv("IMAP_USER", "")
        self.password = password or os.getenv("IMAP_PASSWORD", "")
        self.mailbox = mailbox or os.getenv("IMAP_MAILBOX", "INBOX")

    def fetch(self, since: datetime) -> list[RawItem]:
        if not all([self.host, self.user, self.password]):
            raise RuntimeError(
                f"IMAP 자격증명 누락 (IMAP_HOST/IMAP_USER/IMAP_PASSWORD) — {self.source_name}"
            )

        try:
            from imap_tools import AND, MailBox
        except ImportError as exc:
            raise ImportError("imap_tools 패키지가 설치되지 않았습니다.") from exc

        items: list[RawItem] = []
        with MailBox(self.host).login(
            self.user, self.password, initial_folder=self.mailbox
        ) as mb:
            criteria = AND(from_=self.sender_email, date_gte=since.date())
            for msg in mb.fetch(criteria, mark_seen=False, bulk=True):
                if msg.date is None:
                    continue
                published_at = msg.date
                if published_at.tzinfo is None:
                    published_at = published_at.replace(tzinfo=timezone.utc)
                if published_at <= since:
                    continue

                subject = msg.subject or ""
                content = msg.text.strip() if msg.text else (msg.html or "")
                if not subject or not content.strip():
                    continue

                uid = str(msg.uid or "")
                url = f"email://{self.source_name}/{uid}"

                items.append(
                    RawItem(
                        url=url,
                        title=subject,
                        content=content[:_MAX_CONTENT_LEN],
                        published_at=published_at,
                        source_name=self.source_name,
                        source_group=self.source_group,
                        original_lang="en",
                        extra={"sender": self.sender_email, "msg_uid": uid},
                    )
                )

        return items
