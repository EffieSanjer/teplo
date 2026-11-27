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
        hops = 0

        def getheader(self, name, default=None):
            type(self).hops += 1
            return f"/loop-{self.hops}"

    fake_network(monkeypatch, Response())
    with pytest.raises(FetchError, match="перенаправлений"):
        fetch_public("https://example.com", 100, 1)


def test_fetch_timeout(monkeypatch):
    monkeypatch.setattr(network, "public_addresses", lambda *args: ["93.184.216.34"])
    values = iter([0, 2])
    monkeypatch.setattr(network.time, "monotonic", lambda: next(values))
    with pytest.raises(FetchError, match="вовремя"):
        fetch_public("https://example.com", 100, 1)


def test_https_uses_default_port_443_for_host_header():
    conn = network.PinnedConnection("example.com", 443, "93.184.216.34", True, 1)
    assert conn.default_port == 443
    assert conn.port == conn.default_port
    plain = network.PinnedConnection("example.com", 80, "93.184.216.34", False, 1)
    assert plain.default_port == 80


def test_fake_ip_dials_hostname_not_mapped_address(monkeypatch):
    seen = {}

    class Connection:
        sock = None

        def __init__(self, host, port, address, secure, timeout):
            seen["dial"] = address
            seen["host"] = host

        def request(self, *args, **kwargs):
            pass

        def getresponse(self):
            class Response:
                status = 200

                def getheader(self, name, default=None):
                    return "identity" if name == "Content-Encoding" else default

                def read1(self, size):
                    return b""

            return Response()

        def close(self):
            pass

    monkeypatch.setattr(network, "public_addresses", lambda *args: ["198.19.1.85"])
    monkeypatch.setattr(network, "PinnedConnection", Connection)
    body, content_type, final = fetch_public("https://afisha.yandex.ru/moscow/concert/show", 100, 1)
    assert seen["dial"] == "afisha.yandex.ru"
    assert seen["host"] == "afisha.yandex.ru"
    assert body == b""
    assert final.startswith("https://afisha.yandex.ru/")


def test_public_ip_stays_pinned(monkeypatch):
    seen = {}

    class Connection:
        sock = None

        def __init__(self, host, port, address, secure, timeout):
            seen["dial"] = address

        def request(self, *args, **kwargs):
            pass

        def getresponse(self):
            class Response:
                status = 200

                def getheader(self, name, default=None):
                    return "identity" if name == "Content-Encoding" else default

                def read1(self, size):
                    return b""

            return Response()

        def close(self):
            pass

    monkeypatch.setattr(network, "public_addresses", lambda *args: ["93.184.216.34"])
    monkeypatch.setattr(network, "PinnedConnection", Connection)
    fetch_public("https://example.com/item", 100, 1)
    assert seen["dial"] == "93.184.216.34"
