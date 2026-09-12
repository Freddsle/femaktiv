import io
import os
import socket
from unittest.mock import Mock, patch

from django.test import SimpleTestCase

from chats import transport
from chats.errors import ChatError


class TransportTests(SimpleTestCase):
    def test_unsafe_schemes_hosts_ports_and_credentials_are_rejected(self):
        for url in (
            "file:///etc/passwd",
            "http://127.0.0.1/",
            "http://[::1]/",
            "https://localhost/",
            "http://2130706433/",
            "http://0x7f000001/",
            "https://example.test:8443/",
            "https://user:secret@example.test/",
            "https://example.test\\@internal/",
            "https://example.test/\nheader",
            "https://example.local/",
        ):
            with self.subTest(url=url), self.assertRaises(ChatError):
                transport.safe_url(url)
        self.assertEqual(
            transport.safe_url("https://example.test/über#fragment"),
            "https://example.test/%C3%BCber",
        )

    def test_dns_must_be_public_for_every_returned_address(self):
        def address(ip):
            return socket.AF_INET, socket.SOCK_STREAM, 6, "", (ip, 443)

        for ip in (
            "127.0.0.1",
            "10.0.0.1",
            "169.254.169.254",
            "192.168.1.1",
            "0.0.0.0",
            "100.64.0.1",
        ):
            with (
                self.subTest(ip=ip),
                patch("socket.getaddrinfo", return_value=[address("93.184.216.34"), address(ip)]),
                self.assertRaises(ChatError),
            ):
                transport.public_addresses("example.test", 443, 2)

    def test_http_uses_pinned_address_and_handles_closed_content_length_response(self):
        sock = Mock()
        sock.makefile.return_value = io.BytesIO(
            b"HTTP/1.1 200 OK\r\nContent-Length: 2\r\nContent-Type: application/json\r\nConnection: close\r\n\r\n{}"
        )
        addresses = [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("93.184.216.34", 80))]
        with (
            patch.dict(os.environ, {"FEMAKTIV_OFFLINE_CHECKS": "0"}),
            patch("chats.transport.public_addresses", return_value=addresses),
            patch("chats.transport.socket.socket", return_value=sock),
        ):
            status, _, data = transport.request(
                "http://example.test/path", budget=transport.Budget()
            )
        self.assertEqual((status, data), (200, b"{}"))
        sock.connect.assert_called_once_with(("93.184.216.34", 80))
        self.assertIn(b"Host: example.test", sock.sendall.call_args.args[0])

    def test_limits_and_offline_guard_prevent_external_work(self):
        for kind, limit in (("model", 2), ("search", 2), ("page", 3)):
            budget = transport.Budget()
            for _ in range(limit):
                budget.consume(kind)
            with self.assertRaises(ChatError):
                budget.consume(kind)
        with self.assertRaises(ChatError):
            transport.Budget(seconds=-1).remaining()
        with (
            patch.dict(os.environ, {"FEMAKTIV_OFFLINE_CHECKS": "1"}),
            patch("socket.socket") as sock,
            self.assertRaises(ChatError),
        ):
            transport.request("https://example.test/", budget=transport.Budget())
        sock.assert_not_called()

    def test_redirected_api_request_is_not_followed_with_authorization(self):
        with (
            patch(
                "chats.transport.request",
                return_value=(302, {"location": "https://evil.example.test"}, b""),
            ) as request,
            self.assertRaises(ChatError),
        ):
            transport.request_json(
                "https://example.test/",
                budget=transport.Budget(),
                headers={"Authorization": "Bearer fictional"},
                payload={},
            )
        self.assertEqual(request.call_count, 1)

    def test_oversized_or_compressed_responses_are_rejected(self):
        addresses = [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("93.184.216.34", 80))]
        for headers, body in (
            (b"Content-Length: 5\r\n", b"12345"),
            (b"Content-Encoding: gzip\r\nContent-Length: 2\r\n", b"{}"),
        ):
            sock = Mock()
            sock.makefile.return_value = io.BytesIO(
                b"HTTP/1.1 200 OK\r\n" + headers + b"\r\n" + body
            )
            with (
                patch.dict(os.environ, {"FEMAKTIV_OFFLINE_CHECKS": "0"}),
                patch("chats.transport.public_addresses", return_value=addresses),
                patch("chats.transport.socket.socket", return_value=sock),
                self.assertRaises(ChatError),
            ):
                transport.request("http://example.test/", budget=transport.Budget(), max_bytes=3)
