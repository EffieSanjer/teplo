from typing import Literal

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from src.config import Settings, get_settings
from src.infrastructure.database import get_db, utcnow
from src.modules.auth.service import Context, get_context
from src.modules.gifts import service
from src.modules.gifts.schemas import ArchiveInput, ItemCreate, ItemInput, ItemOut

router = APIRouter(tags=["gifts"])


@router.get("/users/{recipient_id}/items/{list_type}", response_model=list[ItemOut])
def listing(
    recipient_id: str,
    list_type: Literal["wishlist", "surprise"],
    ctx: Context = Depends(get_context),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    return [
        service.serialize(db, ctx, item)
        for item in service.list_items(db, ctx, recipient_id, list_type, settings)
    ]


@router.post("/items", response_model=ItemOut, status_code=201)
def create(
    body: ItemCreate,
    ctx: Context = Depends(get_context),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    return service.serialize(db, ctx, service.create_item(db, ctx, body, settings))


@router.get("/items/{item_id}", response_model=ItemOut)
def detail(
    item_id: str,
    ctx: Context = Depends(get_context),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    return service.serialize(db, ctx, service.get_item(db, ctx, item_id, settings))


@router.put("/items/{item_id}", response_model=ItemOut)
def update(
    item_id: str,
    body: ItemInput,
    ctx: Context = Depends(get_context),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    return service.serialize(db, ctx, service.update_item(db, ctx, item_id, body, settings))


@router.post("/items/{item_id}/archive", response_model=ItemOut)
def archive(
    item_id: str,
    body: ArchiveInput,
    ctx: Context = Depends(get_context),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    item = service.get_item(db, ctx, item_id, settings, manage=True)
    if body.archived and not item.archived_at:
        item.archived_at = utcnow()
    elif not body.archived:
        item.archived_at = None
    db.commit()
    db.refresh(item)
    return service.serialize(db, ctx, item)


@router.delete("/items/{item_id}", status_code=204)
def delete(
    item_id: str,
    ctx: Context = Depends(get_context),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    db.delete(service.get_item(db, ctx, item_id, settings, manage=True))
    db.commit()


@router.post("/items/{item_id}/surprise", response_model=ItemOut, status_code=201)
def copy(
    item_id: str,
    ctx: Context = Depends(get_context),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    return service.serialize(db, ctx, service.copy_as_surprise(db, ctx, item_id, settings))
