from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, Index, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    provider: Mapped[str] = mapped_column(String(50), nullable=False)        # google | github
    provider_id: Mapped[str] = mapped_column(String(200), nullable=False)
    nickname: Mapped[str] = mapped_column(String(100), nullable=False)
    avatar_url: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    likes: Mapped[list["UserLike"]] = relationship("UserLike", back_populates="user")
    bookmarks: Mapped[list["UserBookmark"]] = relationship("UserBookmark", back_populates="user")

    __table_args__ = (
        UniqueConstraint("provider", "provider_id", name="uq_user_provider"),
    )


class UserLike(Base):
    __tablename__ = "user_likes"

    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    card_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("cards.id", ondelete="CASCADE"), primary_key=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    user: Mapped["User"] = relationship("User", back_populates="likes")
    card: Mapped["Card"] = relationship("Card")  # noqa: F821

    __table_args__ = (
        UniqueConstraint("user_id", "card_id", name="uq_user_likes"),
    )


class UserBookmark(Base):
    __tablename__ = "user_bookmarks"

    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    card_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("cards.id", ondelete="CASCADE"), primary_key=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    user: Mapped["User"] = relationship("User", back_populates="bookmarks")
    card: Mapped["Card"] = relationship("Card")  # noqa: F821

    __table_args__ = (
        UniqueConstraint("user_id", "card_id", name="uq_user_bookmarks"),
        Index("idx_bookmarks_user", "user_id", "created_at"),
    )


# forward reference 해소
from app.models.card import Card  # noqa: E402, F401
