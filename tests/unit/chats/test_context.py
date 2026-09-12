from django.test import SimpleTestCase

from chats.context import validate_locality
from chats.errors import ChatError


class LocalityTests(SimpleTestCase):
    def test_only_explicit_city_or_postcode_formats(self):
        for value in ("Berlin", "München", "Frankfurt (Oder)", "10115", ""):
            self.assertEqual(validate_locality(value), value)
        for value in (
            "10115 Berlin",
            "My Street 12",
            "mail@example.test",
            "Berlin site:evil.test",
            "https://example.test",
            "1234",
            "1" * 81,
            None,
        ):
            with self.subTest(value=value), self.assertRaises(ChatError):
                validate_locality(value)
