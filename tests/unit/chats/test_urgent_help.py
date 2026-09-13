from django.test import SimpleTestCase
from django.utils import translation

from chats.urgent_help import panel


class UrgentHelpTests(SimpleTestCase):
    def test_national_numbers_are_fixed_and_country_is_conditional_in_both_languages(self):
        for language, heading, emergency, on_call in (
            ("en", "If you are in Germany", "Emergency services", "Medical on-call service"),
            (
                "de",
                "Wenn du in Deutschland bist",
                "Rettungsdienst",
                "Ärztlicher Bereitschaftsdienst",
            ),
        ):
            with self.subTest(language=language), translation.override(language):
                result = panel()
            self.assertEqual(result["heading"], heading)
            self.assertEqual(
                [(contact["number"], contact["label"]) for contact in result["contacts"]],
                [("112", emergency), ("116117", on_call)],
            )
            self.assertEqual(
                [contact["source_url"] for contact in result["contacts"]],
                ["https://gesund.bund.de/notfallnummern", "https://www.116117.de/de/englisch.php"],
            )
            self.assertIn(
                "not life-threatening" if language == "en" else "nicht lebensbedrohlichen",
                result["contacts"][1]["description"],
            )
            self.assertIn(
                "in German" if language == "en" else "auf Deutsch",
                result["contacts"][1]["description"],
            )
