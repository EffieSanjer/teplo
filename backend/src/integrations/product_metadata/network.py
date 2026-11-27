"""Bounded HTTP client with DNS pinning; no proxies, cookies or automatic redirects."""

import http.client
import ipaddress
import socket
import ssl
import time
from urllib.parse import urljoin, urlsplit

from src.modules.gifts.schemas import valid_url


class FetchError(ValueError):
    pass


# Clash/Surge/V2Ray fake-ip and similar local DNS proxies map public hosts into
# RFC 2544 benchmarking space. It is not a LAN/loopback range, so fetching still
# goes through the proxy rather than to localhost or cloud metadata.
_FAKE_IP = ipaddress.ip_network("198.18.0.0/15")


def _blocked_address(address: str) -> bool:
    ip = ipaddress.ip_address(address)
    if address == "168.63.129.16":  # Azure infrastructure virtual IP.
        return True
    if ip.is_multicast or ip.is_unspecified:
        return True
    if isinstance(ip, ipaddress.IPv6Address) and (
        ip.ipv4_mapped is not None or ip.sixtofour is not None or ip.teredo is not None
    ):
        return True
    if ip in _FAKE_IP:
        return False
    return not ip.is_global


def public_addresses(hostname: str, port: int) -> list[str]:
    try:
        results = socket.getaddrinfo(hostname, port, type=socket.SOCK_STREAM)
    except OSError:
        raise FetchError("Не удалось определить адрес сайта") from None
    addresses = list(dict.fromkeys(result[4][0] for result in results))
    if not addresses:
        raise FetchError("Адрес сайта не найден")
    for address in addresses:
        # Mapped IPv6 and transition ranges can tunnel to unexpected IPv4 endpoints.
        if _blocked_address(address):
            raise FetchError("Недопустимый адрес сайта")
    return addresses


class PinnedConnection(http.client.HTTPConnection):
    def __init__(self, host: str, port: int, address: str, secure: bool, timeout: float):
        super().__init__(host, port=port, timeout=timeout)
        self.address, self.secure = address, secure

    def connect(self):
        # Numeric address prevents a second DNS lookup and DNS-rebinding TOCTOU.
        family = socket.AF_INET6 if ":" in self.address else socket.AF_INET
        sock = socket.socket(family, socket.SOCK_STREAM)
        sock.settimeout(self.timeout)
        try:
            sock.connect((self.address, self.port))
            if self.secure:
                sock = ssl.create_default_context().wrap_socket(sock, server_hostname=self.host)
            self.sock = sock
        except Exception:
            sock.close()
            raise


def fetch_public(url: str, max_bytes: int, timeout: float) -> tuple[bytes, str, str]:
    deadline = time.monotonic() + timeout
    seen_paths: set[tuple[str, str, str]] = set()
    try:
        for _ in range(4):
            valid_url(url)
            parts = urlsplit(url)
            if parts.port not in {None, 80 if parts.scheme == "http" else 443}:
                raise FetchError("Порт сайта не поддерживается")
            host = parts.hostname.encode("idna").decode("ascii")
            port = parts.port or (443 if parts.scheme == "https" else 80)
            path_key = (parts.scheme, host, parts.path or "/")
            # Ozon and similar anti-bot bounces repeat the same path with __rr=N.
            if path_key in seen_paths:
                raise FetchError("Сайт запросил проверку безопасности")
            seen_paths.add(path_key)
            addresses = public_addresses(host, port)
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise FetchError("Сайт не ответил вовремя")
            conn = PinnedConnection(host, port, addresses[0], parts.scheme == "https", remaining)
            try:
                target = parts.path or "/"
                if parts.query:
                    target += "?" + parts.query
                conn.request(
                    "GET",
                    target,
                    headers={
                        # A browser-like UA is used for public pages/APIs only:
                        # no cookies, login, JS execution or CAPTCHA bypass.
                        "User-Agent": (
                            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                            "AppleWebKit/537.36 (KHTML, like Gecko) "
                            "Chrome/124.0.0.0 Safari/537.36"
                        ),
                        "Accept": (
                            "text/html,application/xhtml+xml,application/json;q=0.9,"
                            "image/*;q=0.8,*/*;q=0.7"
                        ),
                        "Accept-Language": "ru-RU,ru;q=0.9,en;q=0.8",
                        "Accept-Encoding": "identity",
                        "Connection": "close",
                    },
                )
                response = conn.getresponse()
                if response.status in {301, 302, 303, 307, 308}:
                    location = response.getheader("Location")
                    if not location:
                        raise FetchError("Некорректное перенаправление")
                    url = urljoin(url, location)
                    continue
                if response.status != 200:
                    err_body = b""
                    err_ct = response.getheader("Content-Type", "")
                    if response.status in {403, 429, 503}:
                        try:
                            length = response.getheader("Content-Length")
                            limit = max_bytes if not length else min(max_bytes, int(length))
                            if limit > 0:
                                # Bounded read so challenge/block pages can be detected.
                                remaining = deadline - time.monotonic()
                                if remaining > 0 and conn.sock:
                                    conn.sock.settimeout(remaining)
                                err_body = response.read(min(limit, 262144))
                        except Exception:
                            err_body = b""
                    err = FetchError("Сайт не предоставил данные")
                    err.status = response.status
                    err.body = err_body
                    err.content_type = err_ct
                    err.url = url
                    raise err
                if response.getheader("Content-Encoding", "identity").lower() != "identity":
                    raise FetchError("Неподдерживаемое сжатие ответа")
                length = response.getheader("Content-Length")
                if length and int(length) > max_bytes:
                    raise FetchError("Ответ сайта слишком большой")
                body = bytearray()
                while True:
                    remaining = deadline - time.monotonic()
                    if remaining <= 0:
                        raise FetchError("Сайт не ответил вовремя")
                    if conn.sock:
                        conn.sock.settimeout(remaining)
                    chunk = response.read1(min(65536, max_bytes + 1 - len(body)))
                    if not chunk:
                        return bytes(body), response.getheader("Content-Type", ""), url
                    body.extend(chunk)
                    if len(body) > max_bytes:
                        raise FetchError("Ответ сайта слишком большой")
            finally:
                conn.close()
        raise FetchError("Слишком много перенаправлений")
    except FetchError:
        raise
    except (ValueError, OSError, http.client.HTTPException, UnicodeError):
        raise FetchError("Не удалось получить данные сайта. Заполните поля вручную") from None
