import os

os.environ.update(
    {
        "APP_ENV": "test",
        "PUBLIC_BASE_URL": "http://testserver",
        "DATABASE_URL": "sqlite://",
        "SESSION_SECRET": "test-secret-that-is-at-least-32-characters",
        "DEV_LOGIN_ENABLED": "true",
        "TELEGRAM_MODE": "disabled",
    }
)

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool
from sqlalchemy.engine import make_url

from src.config import get_settings
from src.infrastructure.database import Base, get_db
from src.main import app
from src.cli import FRIENDS, LOCAL_COMMUNITY, seed
from src.modules.auth.service import create_session


@pytest.fixture
def db(tmp_path):
    test_url = os.environ.get("TEST_DATABASE_URL")
    if test_url:
        # Explicit disposable database only; never drop tables in the application DB.
        if make_url(test_url).database != "wishlist_test":
            raise RuntimeError("TEST_DATABASE_URL must use the dedicated wishlist_test database")
        engine = create_engine(test_url)
        Base.metadata.drop_all(engine)
    else:
        engine = create_engine("sqlite://", poolclass=StaticPool, connect_args={"check_same_thread": False})

        @event.listens_for(engine, "connect")
        def foreign_keys(connection, _):
            connection.execute("PRAGMA foreign_keys=ON")

    Base.metadata.create_all(engine)
    settings = get_settings()
    settings.media_root = tmp_path / "media"
    with Session(engine, expire_on_commit=False) as session:
        seed(session)
        app.dependency_overrides[get_db] = lambda: session
        yield session
    app.dependency_overrides.clear()
    engine.dispose()


@pytest.fixture
def client(db):
    with TestClient(app, base_url="http://testserver", headers={"Origin": "http://testserver"}) as client:
        result = client.post("/api/v1/auth/dev")
        assert result.status_code == 200
        client.headers["X-CSRF-Token"] = result.json()["csrf_token"]
        yield client


@pytest.fixture
def login_as(db):
    from fastapi import Response

    def login(user_id, community_id=LOCAL_COMMUNITY):
        response = Response()
        csrf = create_session(db, response, user_id, community_id, get_settings())
        cookie = response.headers["set-cookie"].split(";", 1)[0].split("=", 1)[1]
        client = TestClient(
            app,
            base_url="http://testserver",
            headers={
                "Origin": "http://testserver",
                "X-CSRF-Token": csrf,
            },
        )
        client.cookies.set("wishlist_session", cookie)
        return client

    return login


@pytest.fixture
def friend_id():
    return FRIENDS[0][0]
