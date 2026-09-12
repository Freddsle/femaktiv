from datetime import date

from django.test import SimpleTestCase

from chats import evidence


class EvidenceTests(SimpleTestCase):
    def test_sources_have_provenance_and_population_limits(self):
        for record in evidence.library():
            with self.subTest(source=record["id"]):
                self.assertTrue(record["url"].startswith("https://"))
                self.assertEqual(date.fromisoformat(record["checked_date"]), date(2026, 9, 12))
                self.assertTrue(record["section"])
                self.assertTrue(record["applicability"])
                self.assertTrue(record["limitations"])
                self.assertEqual(record["library_version"], 1)
        dge = next(record for record in evidence.library() if record["id"] == "dge-food")
        self.assertIn("18–65", dge["applicability"])

    def test_special_nutrients_are_retrieved_only_when_requested(self):
        ordinary = evidence.retrieve("nutrition", ["protein", "fibre", "salt"])
        self.assertFalse(any(record["id"].startswith("nih-") for record in ordinary))
        b12 = evidence.retrieve("nutrition", ["b12"])
        self.assertEqual({record["id"] for record in b12}, {"nih-b12", "efsa-reference-values"})
        self.assertEqual(evidence.retrieve("general", []), [])
