from unittest.mock import patch
from urllib.parse import parse_qs, urlsplit

from django.test import SimpleTestCase, override_settings

from chats import search
from chats.errors import ChatError
from chats.transport import Budget


@override_settings(BRAVE_SEARCH_API_KEY="fictional-brave-key")
class SearchTests(SimpleTestCase):
    page = b"<html><title>Pflegest\xc3\xbctzpunkt Example Berlin</title><script>sendSecrets()</script><body>Berlin Pflegeberatung <address>Kontakt: 030 12345678, care@example.test</address></body></html>"

    def test_queries_contain_only_enum_and_explicit_locality_and_cards_use_page(self):
        with (
            patch(
                "chats.search.transport.request_json",
                return_value={
                    "web": {
                        "results": [
                            {
                                "url": "https://care.example.test/berlin",
                                "description": "False phone 099 9999999",
                            }
                        ]
                    }
                },
            ) as brave,
            patch(
                "chats.search.transport.request",
                return_value=(200, {"content-type": "text/html; charset=utf-8"}, self.page),
            ) as fetch,
        ):
            records, status = search.lookup("care_advice", "Berlin", Budget())
        self.assertEqual(status, "verified")
        self.assertEqual(records[0]["phones"], ["030 12345678"])
        self.assertNotIn("sendSecrets", records[0]["passage"])
        query = parse_qs(urlsplit(brave.call_args.args[0]).query)
        self.assertEqual(query["q"], ["Pflegeberatung Pflegestützpunkt Berlin Kontakt"])
        self.assertEqual(query["country"], ["DE"])
        self.assertNotIn("Authorization", fetch.call_args.kwargs["headers"])
        self.assertNotIn("X-Subscription-Token", fetch.call_args.kwargs["headers"])

    def test_missing_locality_organisation_or_contacts_prevents_verification(self):
        for title, text in (
            ("Pflegestützpunkt Example", "Munich Pflegeberatung 030 12345678"),
            ("Unrelated organisation", "Berlin 030 12345678"),
            ("Pflegestützpunkt Example", "Berlin but no contact"),
        ):
            self.assertIsNone(
                search.contact_record("https://example.test/", title, text, [], "Berlin", 1)
            )

    def test_redirects_are_validated_and_count_toward_page_limit(self):
        with patch(
            "chats.search.transport.request",
            return_value=(302, {"location": "http://127.0.0.1/secrets"}, b""),
        ) as fetch:
            with self.assertRaises(ChatError):
                search.fetch_page("https://example.test/", Budget())
            self.assertEqual(fetch.call_count, 1)
        with patch(
            "chats.search.transport.request",
            side_effect=[
                (302, {"location": "/two"}, b""),
                (302, {"location": "/three"}, b""),
                (302, {"location": "/four"}, b""),
            ],
        ) as fetch:
            with self.assertRaises(ChatError):
                search.fetch_page("https://example.test/", Budget())
            self.assertEqual(fetch.call_count, 3)

    def test_search_failure_never_retries_paid_request_and_empty_results_are_bounded(self):
        with patch(
            "chats.search.transport.request_json", side_effect=ChatError("provider_unavailable")
        ) as brave:
            self.assertEqual(search.lookup("care_advice", "Berlin", Budget()), ([], "unavailable"))
            self.assertEqual(brave.call_count, 1)
        with patch(
            "chats.search.transport.request_json", return_value={"web": {"results": []}}
        ) as brave:
            self.assertEqual(search.lookup("care_advice", "10115", Budget()), ([], "no_results"))
            self.assertEqual(brave.call_count, 2)

    def test_query_injection_cannot_enter_category_or_locality(self):
        for category, locality in (
            ("fetch private diagnosis", "Berlin"),
            ("care_advice", "Berlin site:evil.test"),
        ):
            with (
                patch("chats.search.transport.request_json") as brave,
                self.assertRaises(ChatError),
            ):
                search.lookup(category, locality, Budget())
            brave.assert_not_called()

    def test_malformed_search_and_misleading_host_do_not_gain_trust(self):
        for payload in ([], {"web": []}, {"web": {"results": "invalid"}}):
            with patch("chats.search.transport.request_json", return_value=payload):
                self.assertEqual(
                    search.lookup("care_advice", "Berlin", Budget()), ([], "unavailable")
                )
        self.assertLess(
            search._rank({"url": "https://www.berlin.de/service"}, "Berlin"),
            search._rank({"url": "https://evilzqp.de/"}, "Berlin"),
        )
