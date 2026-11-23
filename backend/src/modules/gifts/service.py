from datetime import timedelta

from fastapi import HTTPException
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from src.config import Settings
from src.infrastructure.database import Community, FriendSurpriseSpace, Item, Media, Reservation, User, utcnow
from src.modules.auth.service import Context
from src.modules.communities.service import require_recipient
from src.modules.gifts.schemas import ItemCreate, ItemInput, ItemOut, ReservationOut
from src.modules.users.access import friendship, require_visible_user


def missing():
    raise HTTPException(404, "Не найдено")


def require_list(db: Session, ctx: Context, recipient_id: str, list_type: str, settings: Settings):
    if list_type == "surprise" and recipient_id == ctx.user.id:
        missing()
    if list_type == "surprise":
        if not friendship(db, ctx.user.id, recipient_id):
            require_recipient(db, recipient_id, ctx.community_id, settings)
    else:
        require_visible_user(db, ctx.user.id, recipient_id, ctx.community_id, settings)


def accessible(db: Session, ctx: Context, item: Item, settings: Settings) -> bool:
    if item.list_type == "surprise":
        if item.recipient_id == ctx.user.id:
            return False
        if item.surprise_visibility == "private" and item.author_id != ctx.user.id:
            return False
        space = db.get(FriendSurpriseSpace, item.recipient_id)
        if space and space.community_id == item.community_id:
            # Only direct friends of the recipient; never friends of the author.
            return bool(friendship(db, ctx.user.id, item.recipient_id))
        if item.community_id != ctx.community_id:
            return False
        # Friendship must never bypass an existing group's membership checks.
        try:
            require_recipient(db, item.recipient_id, ctx.community_id, settings)
        except HTTPException as exc:
            if exc.status_code == 404:
                return False
            raise
        return True
    try:
        require_list(db, ctx, item.recipient_id, item.list_type, settings)
    except HTTPException as exc:
        if exc.status_code == 404:
            return False
        raise
    return True


def surprise_space(db: Session, ctx: Context, recipient_id: str, create: bool = False) -> str | None:
    # Explicit friendship uses a separate shared list, not either user's personal
    # workspace or a Telegram group. Existing group records are never migrated.
    if not friendship(db, ctx.user.id, recipient_id):
        return ctx.community_id
    if create:
        db.scalar(select(User).where(User.id == recipient_id).with_for_update())
    space = db.get(FriendSurpriseSpace, recipient_id)
    if not space and create:
        community = Community(name="Сюрпризы друзей")
        db.add(community)
        db.flush()
        space = FriendSurpriseSpace(recipient_id=recipient_id, community_id=community.id)
        db.add(space)
        db.flush()
    return space.community_id if space else None


def get_item(db: Session, ctx: Context, item_id: str, settings: Settings, manage: bool = False) -> Item:
    item = db.get(Item, item_id)
    if not item or not accessible(db, ctx, item, settings):
        missing()
    if manage and item.author_id != ctx.user.id:
        missing()
    return item


def attach_image(
    db: Session, ctx: Context, image_id: str | None, settings: Settings, previous_id: str | None = None
):
    if not image_id or image_id == previous_id:
        return
    media = db.get(Media, image_id)
    # Only the owner may attach a fresh upload; an edit can keep its current image.
    if (
        not media
        or media.owner_id != ctx.user.id
        or media.attached_at is not None
        or media.created_at <= utcnow() - timedelta(hours=settings.unattached_media_ttl_hours)
    ):
        missing()
    media.attached_at = utcnow()


def create_item(db: Session, ctx: Context, body: ItemCreate, settings: Settings) -> Item:
    require_list(db, ctx, body.recipient_id, body.list_type, settings)
    if body.list_type == "wishlist" and body.recipient_id != ctx.user.id:
        missing()
    attach_image(db, ctx, body.image_id, settings)
    item = Item(
        **body.model_dump(),
        author_id=ctx.user.id,
        community_id=surprise_space(db, ctx, body.recipient_id, create=True) if body.list_type == "surprise" else None,
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


def update_item(db: Session, ctx: Context, item_id: str, body: ItemInput, settings: Settings) -> Item:
    item = get_item(db, ctx, item_id, settings, manage=True)
    if item.archived_at:
        raise HTTPException(409, "Сначала восстановите запись из архива")
    attach_image(db, ctx, body.image_id, settings, item.image_id)
    for field, value in body.model_dump().items():
        if field == "surprise_visibility" and field not in body.model_fields_set:
            continue
        setattr(item, field, value)
    db.commit()
    db.refresh(item)
    return item


def list_items(db: Session, ctx: Context, recipient_id: str, list_type: str, settings: Settings):
    require_list(db, ctx, recipient_id, list_type, settings)
    query = select(Item).where(Item.recipient_id == recipient_id, Item.list_type == list_type)
    if list_type == "surprise":
        space_id = surprise_space(db, ctx, recipient_id)
        if space_id is None:
            return []
        query = query.where(
            Item.community_id == space_id,
            or_(Item.surprise_visibility == "friends", Item.author_id == ctx.user.id),
        )
    return db.scalars(
        query.order_by(
            Item.archived_at.is_not(None),
            Item.archived_at.desc(),
            Item.created_at.desc(),
            Item.id.desc(),
        )
    ).all()


def serialize(db: Session, ctx: Context, item: Item) -> ItemOut:
    fields = {
        key: getattr(item, key) for key in ItemOut.model_fields
        if key not in {"author_name", "can_manage", "image_is_icon", "reservation", "can_reserve"}
    }
    # Never query or expose reservation data to the recipient.
    visible = item.recipient_id != ctx.user.id
    reservation = db.get(Reservation, item.id) if visible else None
    return ItemOut(
        **fields,
        reservation=ReservationOut(
            reserved_by_me=reservation.user_id == ctx.user.id,
            reserver_name=db.get(User, reservation.user_id).display_name,
        ) if reservation else None,
        can_reserve=visible and not item.archived_at and (not reservation or reservation.user_id == ctx.user.id),
        image_is_icon=bool(item.image_id and db.get(Media, item.image_id).is_icon),
        author_name=db.get(User, item.author_id).display_name,
        can_manage=item.author_id == ctx.user.id,
    )


def reserve_item(db: Session, ctx: Context, item_id: str, reserved: bool, settings: Settings) -> Item:
    # Lock the shared item so simultaneous attempts cannot both claim it.
    item = db.scalar(select(Item).where(Item.id == item_id).with_for_update())
    if not item or not accessible(db, ctx, item, settings):
        missing()
    if item.recipient_id == ctx.user.id:
        missing()
    if item.archived_at:
        raise HTTPException(409, "Подарок уже в архиве")
    reservation = db.get(Reservation, item.id)
    if reservation and reservation.user_id != ctx.user.id:
        raise HTTPException(409, "Этот подарок уже забронировал другой друг")
    if reserved and not reservation:
        db.add(Reservation(item_id=item.id, user_id=ctx.user.id))
    elif not reserved and reservation:
        db.delete(reservation)
    db.commit()
    db.refresh(item)
    return item
