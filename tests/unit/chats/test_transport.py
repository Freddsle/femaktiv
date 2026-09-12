import io
import os
import socket
from unittest.mock import Mock, patch

from django.test import SimpleTestCase

from chats import transport
from chats.errors import ChatError


class TransportTests(SimpleTestCase):
    def test_diagnostics_accept_only_bounded_status_and_fixed_reason(self):
        for status in (100, 200, 429, 599):
            with self.subTest(status=status):
                error = ChatError(
                    "provider_unavailable", provider_http_status=status, failure_reason="http_error"
                )
                self.assertEqual(error.provider_http_status, status)
                self.assertEqual(error.failure_reason, "http_error")
        for status in (None, True, False, 99, 600, 200.0, "401", [], {}):
            with self.subTest(status=status):
                error = ChatError("provider_unavailable", provider_http_status=status)
                self.assertIsNone(error.provider_http_status)
        for reason in (None, True, 1, [], {}, "FICTIONAL_PRIVATE_PROVIDER_TEXT"):
            with self.subTest(reason=reason):
                error = ChatError("provider_unavailable", failure_reason=reason)
                self.assertIsNone(error.failure_reason)
                self.assertEqual(error.args, ("provider_unavailable",))

    def test_http_errors_report_status_without_provider_content_or_retry(self):
        private_text = "FICTIONAL_PRIVATE_PROVIDER_TEXT"
        for status in (400, 401, 402, 403, 404, 429, 500):
            with (
                self.subTest(status=status),
                patch(
                    "chats.transport.request",
                    return_value=(
                        status,
                        {"x-request-id": private_text},
                        ('{"message":"' + private_text + '"}').encode(),
                    ),
                ) as request,
                self.assertRaises(ChatError) as caught,
            ):
                transport.request_json(
                    "https://example.test/",
                    budget=transport.Budget(),
                    headers={"Authorization": "Bearer " + private_text},
                    payload={},
                )
            error = caught.exception
            self.assertEqual(error.provider_http_status, status)
            self.assertEqual(error.failure_reason, "http_error")
            self.assertEqual(
                error.code, "rate_limited" if status == 429 else "provider_unavailable"
            )
            self.assertEqual(error.status, 429 if status == 429 else 503)
            self.assertNotIn(
                private_text, str(error) + repr(error) + error.message + repr(vars(error))
            )
            request.assert_called_once()

    def test_malformed_json_reports_only_safe_diagnostics(self):
        for body in (b"FICTIONAL_PRIVATE_PROVIDER_TEXT", b"\xff\xfe\x00"):
            with (
                self.subTest(body=body),
                patch("chats.transport.request", return_value=(200, {}, body)) as request,
                self.assertRaises(ChatError) as caught,
            ):
                transport.request_json(
                    "https://example.test/", budget=transport.Budget(), headers={}
                )
            self.assertEqual(caught.exception.code, "invalid_reply")
            self.assertEqual(caught.exception.provider_http_status, 200)
            self.assertEqual(caught.exception.failure_reason, "invalid_json")
            self.assertNotIn("FICTIONAL_PRIVATE", repr(vars(caught.exception)))
            request.assert_called_once()

    def test_dns_and_connection_errors_are_distinguishable_and_safe(self):
        with (
            patch("socket.getaddrinfo", side_effect=OSError("FICTIONAL_PRIVATE_DNS_TEXT")),
            self.assertRaises(ChatError) as caught,
        ):
            transport.public_addresses("example.test", 443, 2)
        self.assertEqual(caught.exception.failure_reason, "dns_error")
        self.assertIsNone(caught.exception.provider_http_status)
        self.assertNotIn("FICTIONAL_PRIVATE", repr(vars(caught.exception)))

        addresses = [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("93.184.216.34", 80))]
        for failure, reason in (
            (OSError("FICTIONAL_PRIVATE_CONNECTION_TEXT"), "connection_error"),
            (TimeoutError("FICTIONAL_PRIVATE_TIMEOUT_TEXT"), "timeout"),
        ):
            sock = Mock()
            sock.connect.side_effect = failure
            with (
                self.subTest(reason=reason),
                patch.dict(os.environ, {"FEMAKTIV_OFFLINE_CHECKS": "0"}),
                patch("chats.transport.public_addresses", return_value=addresses),
                patch("chats.transport.socket.socket", return_value=sock),
                self.assertRaises(ChatError) as caught,
            ):
                transport.request("http://example.test/", budget=transport.Budget())
            self.assertEqual(caught.exception.failure_reason, reason)
            self.assertIsNone(caught.exception.provider_http_status)
            self.assertNotIn("FICTIONAL_PRIVATE", repr(vars(caught.exception)))
            sock.connect.assert_called_once()

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
        budget = transport.Budget()
        budget.consume("model")
        budget.consume("model")
        with self.assertRaises(ChatError):
            budget.consume("model")
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
        for headers, body, reason in (
            (b"Content-Length: 5\r\n", b"12345", "response_too_large"),
            (b"Content-Encoding: gzip\r\nContent-Length: 2\r\n", b"{}", "unsupported_encoding"),
        ):
            sock = Mock()
            sock.makefile.return_value = io.BytesIO(
                b"HTTP/1.1 200 OK\r\n" + headers + b"\r\n" + body
            )
            with (
                patch.dict(os.environ, {"FEMAKTIV_OFFLINE_CHECKS": "0"}),
                patch("chats.transport.public_addresses", return_value=addresses),
                patch("chats.transport.socket.socket", return_value=sock),
                self.assertRaises(ChatError) as caught,
            ):
                transport.request("http://example.test/", budget=transport.Budget(), max_bytes=3)
            self.assertEqual(caught.exception.provider_http_status, 200)
            self.assertEqual(caught.exception.failure_reason, reason)
