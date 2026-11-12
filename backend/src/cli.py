import argparse
from datetime import timedelta
from decimal import Decimal

from sqlalchemy import delete
from sqlalchemy.orm import Session

from src.config import get_settings
from src.infrastructure.database import (
    AuthSession,
    Community,
    CommunityIntegration,
    Item,
    Membership,
    RateBucket,
    User,
    get_engine,
    utcnow,
)
from src.modules.media.service import cleanup

LOCAL_COMMUNITY = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"
REAL_COMMUNITY = "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb"
FRIENDS = [
    ("22222222-2222-4222-8222-222222222222", "Аня Смирнова"),
    ("33333333-3333-4333-8333-333333333333", "Максим Волков"),
    ("44444444-4444-4444-8444-444444444444", "Саша Ким"),
]


def seed(db: Session):
    settings = get_settings()
    if not settings.dev_login_enabled or settings.telegram_mode != "disabled":
        raise SystemExit("Seed is only available with local development login enabled")
    if not db.get(Community, LOCAL_COMMUNITY):
        db.add(Community(id=LOCAL_COMMUNITY, name="Наша компания"))
    people = [(settings.dev_user_id, "Вы"), *FRIENDS]
    if settings.dev_user_id in {uid for uid, _ in FRIENDS}:
        raise SystemExit("DEV_USER_ID must not match a demo friend")
    for uid, name in people:
        if not db.get(User, uid):
            db.add(User(id=uid, display_name=name))
    db.flush()
    for uid, _ in people:
        if not db.get(Membership, (LOCAL_COMMUNITY, uid)):
            db.add(Membership(community_id=LOCAL_COMMUNITY, user_id=uid))
    db.flush()
    templates = [
        (
            settings.dev_user_id,
            settings.dev_user_id,
            "wishlist",
            "idea",
            "Что-нибудь для рисования",
            "Люблю акварель и красивую бумагу. Буду рад новым материалам и вдохновению.",
            None,
            "3500",
            False,
        ),
        (
            settings.dev_user_id,
            settings.dev_user_id,
            "wishlist",
            "gift",
            "Наушники для любимой музыки",
            "Полноразмерные, беспроводные. Цвет — тёплый белый или графитовый.",
            "https://www.sony.com/headphones",
            "15000",
            False,
        ),
        (
            settings.dev_user_id,
            settings.dev_user_id,
            "wishlist",
            "idea",
            "Выходные за городом",
            "Маленький домик, лес и никакого расписания 🌲",
            None,
            None,
            False,
        ),
        (
            settings.dev_user_id,
            settings.dev_user_id,
            "wishlist",
            "idea",
            "Керамическая кружка",
            "Ручная работа, неровные края, уютная глазурь.",
            None,
            "2000",
            True,
        ),
        (
            FRIENDS[0][0],
            FRIENDS[0][0],
            "wishlist",
            "idea",
            "Мастер-класс по керамике",
            "Давно мечтаю сделать свою первую чашку!",
            None,
            "4500",
            False,
        ),
        (
            FRIENDS[0][0],
            FRIENDS[0][0],
            "wishlist",
            "gift",
            "Книга об искусстве",
            "Красивое издание для долгих вечеров.",
            "https://www.taschen.com",
            None,
            False,
        ),
        (
            FRIENDS[1][0],
            FRIENDS[1][0],
            "wishlist",
            "idea",
            "Настольная игра для компании",
            "На 4–6 человек, чтобы разобраться за один вечер.",
            None,
            "5000",
            False,
        ),
        (
            FRIENDS[2][0],
            FRIENDS[2][0],
            "wishlist",
            "idea",
            "Билет на концерт",
            "Джаз, маленький зал и хорошая компания.",
            None,
            None,
            False,
        ),
        (
            FRIENDS[0][0],
            settings.dev_user_id,
            "surprise",
            "idea",
            "Набор для уютного вечера",
            "Чай, свеча и тёплый плед — Аня не увидит эту запись.",
            None,
            "3000",
            False,
        ),
        (
            settings.dev_user_id,
            FRIENDS[1][0],
            "surprise",
            "idea",
            "Скрытый сюрприз",
            "Получатель не должен увидеть ни эту запись, ни её количество.",
            None,
            "1000",
            False,
        ),
    ]
    for i, (recipient, author, list_type, kind, title, description, url, price, archived) in enumerate(
        templates
    ):
        item_id = f"dddddddd-dddd-4ddd-8ddd-{i + 1:012d}"
        if not db.get(Item, item_id):
            db.add(
                Item(
                    id=item_id,
                    recipient_id=recipient,
                    author_id=author,
                    list_type=list_type,
                    community_id=LOCAL_COMMUNITY if list_type == "surprise" else None,
                    item_type=kind,
                    title=title,
                    description=description,
                    url=url,
                    price=Decimal(price) if price else None,
                    currency="RUB" if price else None,
                    archived_at=utcnow() if archived else None,
                    created_at=utcnow() - timedelta(minutes=i),
                )
            )
    db.commit()
    print("Demo data ready (existing records preserved).")


def configure_telegram(db: Session):
    settings = get_settings()
    if settings.dev_login_enabled or not settings.telegram_chat_id:
        raise SystemExit("Disable development login and configure TELEGRAM_CHAT_ID first")
    if not db.get(Community, REAL_COMMUNITY):
        db.add(Community(id=REAL_COMMUNITY, name="Наши вишлисты"))
        db.flush()
    integration = db.get(CommunityIntegration, REAL_COMMUNITY)
    if integration:
        integration.telegram_chat_id = settings.telegram_chat_id
    else:
        db.add(CommunityIntegration(community_id=REAL_COMMUNITY, telegram_chat_id=settings.telegram_chat_id))
    db.commit()
    print("Telegram community configured separately from demo data.")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=["seed", "configure-telegram", "cleanup", "export-openapi"])
    args = parser.parse_args()
    if args.command == "export-openapi":
        import json
        from src.main import app

        print(json.dumps(app.openapi(), ensure_ascii=False, indent=2))
        return
    with Session(get_engine()) as db:
        if args.command == "seed":
            seed(db)
        elif args.command == "configure-telegram":
            configure_telegram(db)
        else:
            count = cleanup(db, get_settings())
            db.execute(delete(AuthSession).where(AuthSession.expires_at < utcnow()))
            db.execute(delete(RateBucket))
            db.commit()
            print(f"Removed {count} unreferenced images and expired sessions.")


if __name__ == "__main__":
    main()
