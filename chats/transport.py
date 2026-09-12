"""Bounded HTTP without proxy inheritance, redirects with credentials, or DNS rebinding."""

import http.client
import ipaddress
import json
import os
import socket
import ssl
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from urllib.parse import quote, urlsplit, urlunsplit

from .errors import ChatError

_DNS = ThreadPoolExecutor(max_workers=4, thread_name_prefix="chat-dns")


@dataclass
class Budget:
    seconds: float = 60
    deadline: float = field(init=False)
    counts: dict = field(default_factory=dict)
    active_check: object = field(default=None, repr=False)

    def __post_init__(self):
        self.deadline = time.monotonic() + self.seconds

    def remaining(self, cap=None):
        left = self.deadline - time.monotonic()
        if left <= 0:
            raise ChatError("deadline_exceeded", 504, failure_reason="timeout")
        return min(left, cap) if cap else left

    def consume(self, kind):
        self.remaining()
        self.ensure_active()
        self.counts[kind] = self.counts.get(kind, 0) + 1
        if self.counts[kind] > {"model": 2}[kind]:
            raise ChatError("deadline_exceeded", 504)

    def ensure_active(self):
        if self.active_check is not None:
            self.active_check()


def safe_url(url):
    if not isinstance(url, str) or len(url) > 2048 or any(ord(c) <= 32 for c in url) or "\\" in url:
        raise ChatError("unsafe_url")
    try:
        parts = urlsplit(url)
        host = (parts.hostname or "").encode("idna").decode("ascii").lower()
        port = parts.port or (443 if parts.scheme == "https" else 80)
        if (
            parts.scheme not in {"https", "http"}
            or not host
            or parts.username is not None
            or parts.password is not None
        ):
            raise ValueError
        if port != (443 if parts.scheme == "https" else 80) or host.endswith(".") or ":" in host:
            raise ValueError
        # Literal addresses, including alternative numeric forms, are not useful source hosts.
        if (
            host == "localhost"
            or host.endswith((".localhost", ".local", ".internal"))
            or "." not in host
        ):
            raise ValueError
        try:
            ipaddress.ip_address(host)
        except ValueError:
            pass
        else:
            raise ValueError
        if host.replace(".", "").isdigit():
            raise ValueError
        path = quote(parts.path or "/", safe="/%:@!$&'()*+,;=-._~")
        query = quote(parts.query, safe="%=&;:+,/?@!$'()*-._~")
        return urlunsplit((parts.scheme, host, path, query, ""))
    except ValueError, UnicodeError:
        raise ChatError("unsafe_url") from None


def public_addresses(host, port, timeout):
    try:
        future = _DNS.submit(socket.getaddrinfo, host, port, type=socket.SOCK_STREAM)
        addresses = future.result(timeout=timeout)
        if not addresses or any(
            not ipaddress.ip_address(item[4][0]).is_global for item in addresses
        ):
            raise ChatError("unsafe_url")
        return sorted(addresses, key=lambda item: item[0] != socket.AF_INET)
    except TimeoutError:
        future.cancel()
        raise ChatError("deadline_exceeded", 504, failure_reason="timeout") from None
    except OSError, ValueError:
        raise ChatError("provider_unavailable", failure_reason="dns_error") from None


def request(url, *, budget, method="GET", headers=None, body=None, max_bytes=1_000_000, timeout=25):
    """One bounded request only; redirects are never followed."""
    if os.environ.get("FEMAKTIV_OFFLINE_CHECKS") == "1":
        raise ChatError("network_disabled", 503)
    url = safe_url(url)
    parts = urlsplit(url)
    host, port = parts.hostname, 443 if parts.scheme == "https" else 80
    operation_deadline = min(budget.deadline, time.monotonic() + timeout)
    response_status = None

    def remaining():
        left = operation_deadline - time.monotonic()
        if left <= 0:
            raise ChatError(
                "deadline_exceeded",
                504,
                provider_http_status=response_status,
                failure_reason="timeout",
            )
        return left

    addresses = public_addresses(host, port, remaining())
    connection = http.client.HTTPConnection(host, port, timeout=remaining())
    sock = None
    watchdog = None
    try:
        family, socktype, proto, _, address = addresses[0]
        sock = socket.socket(family, socktype, proto)
        sock.settimeout(remaining())
        sock.connect(address)  # Exact validated address, no second DNS resolution.
        if parts.scheme == "https":
            sock.settimeout(remaining())
            sock = ssl.create_default_context().wrap_socket(sock, server_hostname=host)
        connection.sock = sock

        def stop_slow_response():
            try:
                sock.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass

        # Bound slow-drip headers too: individual recv timeouts reset on each byte.
        watchdog = threading.Timer(remaining(), stop_slow_response)
        watchdog.daemon = True
        watchdog.start()
        request_headers = {
            "Host": host,
            "User-Agent": "femaktiv-prototype/0.1",
            "Accept-Encoding": "identity",
            **(headers or {}),
        }
        target = parts.path + ("?" + parts.query if parts.query else "")
        sock.settimeout(remaining())
        connection.request(method, target, body=body, headers=request_headers)
        sock.settimeout(remaining())
        response = connection.getresponse()
        response_status = response.status
        response_headers = {key.lower(): value for key, value in response.getheaders()}
        if response_headers.get("content-encoding", "identity").lower() not in {"", "identity"}:
            raise ChatError(
                "provider_unavailable",
                provider_http_status=response_status,
                failure_reason="unsupported_encoding",
            )
        data = bytearray()
        while not response.isclosed():
            sock.settimeout(remaining())
            chunk = response.read1(min(16384, max_bytes + 1 - len(data)))
            if not chunk:
                break
            data.extend(chunk)
            if len(data) > max_bytes:
                raise ChatError(
                    "provider_unavailable",
                    provider_http_status=response_status,
                    failure_reason="response_too_large",
                )
        remaining()
        return response.status, response_headers, bytes(data)
    except TimeoutError, socket.timeout:
        raise ChatError(
            "deadline_exceeded",
            504,
            provider_http_status=response_status,
            failure_reason="timeout",
        ) from None
    except OSError, ValueError, http.client.HTTPException:
        remaining()
        raise ChatError(
            "provider_unavailable",
            provider_http_status=response_status,
            failure_reason="connection_error",
        ) from None
    finally:
        if watchdog is not None:
            watchdog.cancel()
        connection.close()
        if sock is not None:
            sock.close()


def request_json(url, *, budget, headers, payload=None):
    body = json.dumps(payload, ensure_ascii=False).encode() if payload is not None else None
    status, _, data = request(
        url,
        budget=budget,
        method="POST" if body is not None else "GET",
        headers={"Accept": "application/json", "Content-Type": "application/json", **headers},
        body=body,
    )
    if status == 429:
        raise ChatError(
            "rate_limited", 429, provider_http_status=status, failure_reason="http_error"
        )
    if status != 200:
        raise ChatError(
            "provider_unavailable", 503, provider_http_status=status, failure_reason="http_error"
        )
    try:
        return json.loads(data)
    except ValueError, UnicodeError:
        raise ChatError(
            "invalid_reply", provider_http_status=status, failure_reason="invalid_json"
        ) from None
