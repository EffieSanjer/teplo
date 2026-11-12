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


def public_addresses(hostname: str, port: int) -> list[str]:
    try:
        results = socket.getaddrinfo(hostname, port, type=socket.SOCK_STREAM)
    except OSError:
        raise FetchError("Не удалось определить адрес сайта") from None
    addresses = list(dict.fromkeys(result[4][0] for result in results))
    if not addresses:
        raise FetchError("Адрес сайта не найден")
    for address in addresses:
        ip = ipaddress.ip_address(address)
        # Mapped IPv6 and transition ranges can tunnel to unexpected IPv4 endpoints.
        if (
            not ip.is_global
            or address == "168.63.129.16"  # Azure infrastructure virtual IP.
            or ip.is_multicast
            or ip.is_unspecified
            or isinstance(ip, ipaddress.IPv6Address)
            and (ip.ipv4_mapped is not None or ip.sixtofour is not None or ip.teredo is not None)
        ):
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
    try:
        for _ in range(4):
            valid_url(url)
            parts = urlsplit(url)
            if parts.port not in {None, 80 if parts.scheme == "http" else 443}:
                raise FetchError("Порт сайта не поддерживается")
            host = parts.hostname.encode("idna").decode("ascii")
            port = parts.port or (443 if parts.scheme == "https" else 80)
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
                        "User-Agent": "FriendsWishlist/0.1 (product preview)",
                        "Accept": "text/html,application/xhtml+xml,image/*",
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
                    raise FetchError("Сайт не предоставил данные")
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
