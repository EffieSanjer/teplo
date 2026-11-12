from src.config import get_settings


def test_old_development_session_cannot_be_used_after_public_switch(client, monkeypatch):
    settings = get_settings()
    monkeypatch.setattr(settings, "dev_login_enabled", False)
    monkeypatch.setattr(settings, "telegram_mode", "polling")
    monkeypatch.setattr(settings, "telegram_chat_id", -100)
    assert client.get("/api/v1/users").status_code == 403
    assert client.post("/api/v1/auth/dev").status_code == 404
