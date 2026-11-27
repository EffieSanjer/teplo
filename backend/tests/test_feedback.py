from src.config import get_settings
from src.infrastructure.database import AuthIdentity
from src.modules.feedback import routes


def test_feedback_requires_admin(client, monkeypatch):
    settings = get_settings()
    monkeypatch.setattr(settings, "telegram_bot_token", "123:secret")
    monkeypatch.setattr(settings, "telegram_admin_id", None)
    monkeypatch.setattr(routes, "send_message", lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError()))
    result = client.post("/api/v1/feedback", json={"message": "Сделайте кнопку крупнее"})
    assert result.status_code == 503
    assert "недоступна" in result.json()["detail"]


def test_feedback_sends_to_admin(client, db, monkeypatch):
    settings = get_settings()
    monkeypatch.setattr(settings, "telegram_bot_token", "123:secret")
    monkeypatch.setattr(settings, "telegram_admin_id", 42)
    sent = []

    def capture(settings_arg, chat_id, text, **kwargs):
        sent.append((chat_id, text, kwargs))

    monkeypatch.setattr(routes, "send_message", capture)
    db.add(
        AuthIdentity(
            user_id=settings.dev_user_id,
            provider="telegram",
            provider_user_id="777",
            username="wish_user",
        )
    )
    db.commit()

    result = client.post("/api/v1/feedback", json={"message": "Добавьте тёмную тему <script>"})
    assert result.status_code == 204
    assert len(sent) == 1
    chat_id, text, kwargs = sent[0]
    assert chat_id == 42
    assert kwargs.get("parse_mode", "HTML") == "HTML"
    assert "Предложение для «Кстати»" in text
    assert "@wish_user" in text
    assert "<code>777</code>" in text
    assert "&lt;script&gt;" in text
    assert "<script>" not in text


def test_feedback_rate_limit(client, monkeypatch):
    settings = get_settings()
    monkeypatch.setattr(settings, "telegram_bot_token", "123:secret")
    monkeypatch.setattr(settings, "telegram_admin_id", 42)
    monkeypatch.setattr(routes, "send_message", lambda *args, **kwargs: None)
    for _ in range(3):
        assert client.post("/api/v1/feedback", json={"message": "ок"}).status_code == 204
    limited = client.post("/api/v1/feedback", json={"message": "ещё"})
    assert limited.status_code == 429


def test_feedback_validates_message(client, monkeypatch):
    settings = get_settings()
    monkeypatch.setattr(settings, "telegram_bot_token", "123:secret")
    monkeypatch.setattr(settings, "telegram_admin_id", 42)
    monkeypatch.setattr(routes, "send_message", lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError()))
    assert client.post("/api/v1/feedback", json={"message": ""}).status_code == 422
    assert client.post("/api/v1/feedback", json={"message": "x" * 1001}).status_code == 422
