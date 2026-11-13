import uuid
from datetime import datetime, timezone
from decimal import Decimal
from functools import lru_cache

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    create_engine,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker

from src.config import get_settings


def utcnow() -> datetime:
    # Naive UTC consistently across PostgreSQL and the SQLite test adapter.
    return datetime.now(timezone.utc).replace(tzinfo=None)


def new_id() -> str:
    return str(uuid.uuid4())


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    display_name: Mapped[str] = mapped_column(String(120))
    avatar_media_id: Mapped[str | None] = mapped_column(String(36))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)


class AuthIdentity(Base):
    __tablename__ = "auth_identities"
    __table_args__ = (UniqueConstraint("provider", "provider_user_id"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    provider: Mapped[str] = mapped_column(String(30))
    provider_user_id: Mapped[str] = mapped_column(String(100))
    username: Mapped[str | None] = mapped_column(String(120))


class Community(Base):
    __tablename__ = "communities"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    name: Mapped[str] = mapped_column(String(120))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)


class CommunityIntegration(Base):
    __tablename__ = "community_integrations"
    community_id: Mapped[str] = mapped_column(ForeignKey("communities.id"), primary_key=True)
    telegram_chat_id: Mapped[int] = mapped_column(BigInteger, unique=True)


class Membership(Base):
    __tablename__ = "community_memberships"
    community_id: Mapped[str] = mapped_column(ForeignKey("communities.id"), primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), primary_key=True)
    status: Mapped[str] = mapped_column(String(20), default="active")
    checked_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    __table_args__ = (CheckConstraint("status IN ('active', 'left')", name="membership_status"),)


class PersonalWorkspace(Base):
    __tablename__ = "personal_workspaces"
    community_id: Mapped[str] = mapped_column(ForeignKey("communities.id"), primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), unique=True)


class Media(Base):
    __tablename__ = "media"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    storage_key: Mapped[str] = mapped_column(String(100), unique=True)
    mime_type: Mapped[str] = mapped_column(String(50))
    size: Mapped[int] = mapped_column(Integer)
    is_icon: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    owner_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    # Once attached, uploader ownership must NEVER bypass the linked-item ACL.
    attached_at: Mapped[datetime | None] = mapped_column(DateTime)


class Item(Base):
    __tablename__ = "items"
    __table_args__ = (
        CheckConstraint("list_type IN ('wishlist', 'surprise')", name="item_list_type"),
        CheckConstraint("item_type IN ('idea', 'gift', 'certificate')", name="item_type"),
        CheckConstraint("price_mode IN ('approximate', 'from')", name="item_price_mode"),
        CheckConstraint(
            "(list_type = 'wishlist' AND author_id = recipient_id AND community_id IS NULL) OR "
            "(list_type = 'surprise' AND author_id <> recipient_id AND community_id IS NOT NULL)",
            name="item_ownership",
        ),
        CheckConstraint(
            "item_type <> 'idea' OR length(trim(title)) > 0 AND title IS NOT NULL", name="idea_title"
        ),
        CheckConstraint("item_type <> 'gift' OR url IS NOT NULL AND length(url) > 0", name="gift_url"),
        CheckConstraint(
            "item_type <> 'certificate' OR url IS NOT NULL AND length(url) > 0", name="certificate_url"
        ),
        CheckConstraint("price IS NULL OR price >= 0 AND currency IS NOT NULL", name="item_price"),
        Index(
            "ix_items_list", "recipient_id", "list_type", "community_id", "archived_at", "created_at", "id"
        ),
    )
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    recipient_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    author_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    list_type: Mapped[str] = mapped_column(String(10))
    community_id: Mapped[str | None] = mapped_column(ForeignKey("communities.id"))
    item_type: Mapped[str] = mapped_column(String(16))
    title: Mapped[str | None] = mapped_column(String(200))
    description: Mapped[str | None] = mapped_column(Text)
    url: Mapped[str | None] = mapped_column(String(2048))
    image_id: Mapped[str | None] = mapped_column(ForeignKey("media.id"), index=True)
    price: Mapped[Decimal | None] = mapped_column(Numeric(14, 2))
    currency: Mapped[str | None] = mapped_column(String(3))
    price_mode: Mapped[str] = mapped_column(String(16), default="approximate", server_default="approximate")
    archived_at: Mapped[datetime | None] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)


class AuthSession(Base):
    __tablename__ = "auth_sessions"
    token_hash: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    community_id: Mapped[str] = mapped_column(ForeignKey("communities.id"))
    csrf_token: Mapped[str] = mapped_column(String(64))
    expires_at: Mapped[datetime] = mapped_column(DateTime, index=True)


class RateBucket(Base):
    __tablename__ = "rate_buckets"
    key: Mapped[str] = mapped_column(String(100), primary_key=True)
    window: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    count: Mapped[int] = mapped_column(Integer)


@lru_cache
def get_engine():
    return create_engine(get_settings().database_url, pool_pre_ping=True, hide_parameters=True)


def get_db():
    with sessionmaker(get_engine(), expire_on_commit=False)() as db:
        yield db
