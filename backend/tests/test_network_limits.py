import pytest

from src.integrations.product_metadata import network
from src.integrations.product_metadata.network import FetchError, fetch_public


def fake_network(monkeypatch, response):
    class Connection:
        sock = None

        def __init__(self, *args):
            pass

        def request(self, *args, **kwargs):
            pass

        def getresponse(self):
            return response

        def close(self):
            pass

    monkeypatch.setattr(network, "public_addresses", lambda *args: ["93.184.216.34"])
    monkeypatch.setattr(network, "PinnedConnection", Connection)


def test_streaming_response_limit(monkeypatch):
    class Response:
        status = 200

        def getheader(self, name, default=None):
            return default

        def read1(self, size):
            return b"x" * size

    fake_network(monkeypatch, Response())
    with pytest.raises(FetchError, match="слишком большой"):
        fetch_public("https://example.com", 100, 1)


def test_redirect_limit(monkeypatch):
    class Response:
        status = 302

        def getheader(self, name, default=None):
            return "/loop"

    fake_network(monkeypatch, Response())
    with pytest.raises(FetchError, match="перенаправлений"):
        fetch_public("https://example.com", 100, 1)


def test_fetch_timeout(monkeypatch):
    monkeypatch.setattr(network, "public_addresses", lambda *args: ["93.184.216.34"])
    values = iter([0, 2])
    monkeypatch.setattr(network.time, "monotonic", lambda: next(values))
    with pytest.raises(FetchError, match="вовремя"):
        fetch_public("https://example.com", 100, 1)
