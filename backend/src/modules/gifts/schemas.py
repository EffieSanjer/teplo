from datetime import datetime
from decimal import Decimal
from typing import Literal
from urllib.parse import urlsplit

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


def valid_url(value: str) -> str:
    try:
        parts = urlsplit(value)
        if parts.scheme not in {"http", "https"} or not parts.hostname or parts.username or parts.password:
            raise ValueError()
        if any(ord(c) < 33 for c in value) or "\\" in value:
            raise ValueError()
        _ = parts.port
        parts.hostname.encode("idna")
    except (ValueError, UnicodeError):
        raise ValueError("Укажите корректную HTTP(S)-ссылку без учётных данных") from None
    return value


class ItemInput(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    item_type: Literal["idea", "gift", "certificate"]
    title: str | None = Field(default=None, max_length=200)
    description: str | None = Field(default=None, max_length=5000)
    url: str | None = Field(default=None, max_length=2048)
    image_id: str | None = Field(default=None, min_length=36, max_length=36)
    price: Decimal | None = Field(default=None, ge=0, max_digits=14, decimal_places=2)
    currency: str | None = Field(default=None, pattern=r"^[A-Z]{3}$")
    price_mode: Literal["approximate", "from"] = "approximate"

    @field_validator("title", "description", "url", "currency", mode="before")
    @classmethod
    def empty_to_none(cls, value):
        return value.strip() or None if isinstance(value, str) else value

    @field_validator("url")
    @classmethod
    def check_url(cls, value):
        return valid_url(value) if value else value

    @model_validator(mode="after")
    def required_fields(self):
        if self.item_type == "idea" and not self.title:
            raise ValueError("У идеи должно быть название")
        if self.item_type == "gift" and not self.url:
            raise ValueError("У конкретного подарка должна быть ссылка")
        if self.item_type == "certificate" and not self.url:
            raise ValueError("У магазина для сертификата должна быть ссылка")
        if self.price is not None and not self.currency:
            raise ValueError("Укажите валюту цены")
        return self


class ItemCreate(ItemInput):
    recipient_id: str = Field(min_length=36, max_length=36)
    list_type: Literal["wishlist", "surprise"]


class ItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    recipient_id: str
    author_id: str
    author_name: str
    list_type: Literal["wishlist", "surprise"]
    item_type: Literal["idea", "gift", "certificate"]
    title: str | None
    description: str | None
    url: str | None
    image_id: str | None
    image_is_icon: bool = False
    price: Decimal | None
    currency: str | None
    price_mode: Literal["approximate", "from"]
    archived_at: datetime | None
    created_at: datetime
    updated_at: datetime
    can_manage: bool


class ArchiveInput(BaseModel):
    archived: bool
