"""Synthetic anonymizer fixtures exercise checks, not live masking accuracy."""

import re
from copy import deepcopy

from django.test import SimpleTestCase

from chats import masking_evaluation as evaluation

REPLACEMENTS = {
    "personal_names": ("Leonie Testfeld", "Markus Mustermann"),
    "street_address": ("Fiktivweg 17",),
    "birth_date": ("1970-05-13",),
    "email": ("leonie.testfeld@example.invalid",),
    "phone": ("+49 30 23125000",),
    "iban": ("DE89 3704 0044 0532 0130 00",),
    "identity_number": ("T22000129",),
    "legal_case_number": ("12 C 345/26",),
    "contract_number": ("FA-2026-7319",),
}


def fictional_export(*, unmasked_category=None):
    cases = []
    for case in evaluation.CASES:
        text = case["text"]
        for category, values in REPLACEMENTS.items():
            if category != unmasked_category:
                for value in values:
                    text = text.replace(value, f"[[{category}-ABC123]]")
        cases.append(
            {
                "case": case["case"],
                "anonymizer_export": {
                    "status": "completed",
                    "original_text": case["text"],
                    "anonymized_text_raw": text,
                },
            }
        )
    return {"schema_version": 1, "provenance": evaluation.PROVENANCE, "cases": cases}


class MaskingEvaluationTests(SimpleTestCase):
    def test_fixed_bilingual_inputs_are_not_claimed_as_results(self):
        result = evaluation.export_inputs()
        self.assertTrue(result["fictional_only"])
        self.assertEqual({item["language"] for item in result["cases"]}, {"en", "de"})
        self.assertNotIn("passed", result)
        self.assertNotIn("anonymized_text_raw", str(result))

    def test_preserves_actual_masked_output_with_honest_provenance(self):
        supplied = fictional_export()
        result = evaluation.evaluate_export(supplied)
        self.assertTrue(result["passed"])
        self.assertFalse(result["provenance_independently_attested"])
        for item, source in zip(result["cases"], supplied["cases"], strict=True):
            self.assertTrue(all(item["essential_facts"].values()))
            self.assertTrue(all(item["identifier_removal"].values()))
            self.assertEqual(
                item["masked_text_for_human_review"],
                source["anonymizer_export"]["anonymized_text_raw"],
            )

    def test_each_identifier_category_must_be_removed_in_both_languages(self):
        for category in REPLACEMENTS:
            with self.subTest(category=category):
                result = evaluation.evaluate_export(fictional_export(unmasked_category=category))
                self.assertFalse(result["passed"])
                for item in result["cases"]:
                    self.assertFalse(item["identifier_removal"][category])

    def test_punctuation_or_country_prefix_changes_do_not_hide_a_leak(self):
        document = fictional_export()
        for item in document["cases"]:
            item["anonymizer_export"]["anonymized_text_raw"] += (
                " 030-2312-5000 DE89370400440532013000 12C34526"
            )
        result = evaluation.evaluate_export(document)
        for item in result["cases"]:
            for category in ("phone", "iban", "legal_case_number"):
                self.assertFalse(item["identifier_removal"][category])
            self.assertNotIn("masked_text_for_human_review", item)

    def test_every_essential_fact_must_survive_masking(self):
        for position, case in enumerate(evaluation.CASES):
            for name, pattern in case["facts"].items():
                with self.subTest(case=case["case"], fact=name):
                    document = fictional_export()
                    exported = document["cases"][position]["anonymizer_export"]
                    exported["anonymized_text_raw"] = re.sub(
                        pattern,
                        "[[Overmasked-ABC123]]",
                        exported["anonymized_text_raw"],
                        flags=re.IGNORECASE,
                    )
                    result = evaluation.evaluate_export(document)
                    self.assertFalse(result["passed"])
                    self.assertFalse(result["cases"][position]["essential_facts"][name])

    def test_unknown_added_content_is_not_copied_into_report(self):
        document = fictional_export()
        secret = "arbitrary-private-provider-content"
        document["cases"][0]["anonymizer_export"]["anonymized_text_raw"] += secret
        result = evaluation.evaluate_export(document)
        self.assertFalse(result["passed"])
        self.assertNotIn(secret, str(result))
        self.assertNotIn("masked_text_for_human_review", result["cases"][0])

    def test_rejects_generated_answers_instead_of_anonymizer_exports(self):
        document = fictional_export()
        document["provenance"] = "model-echo"
        with self.assertRaises(evaluation.MaskingExportError):
            evaluation.evaluate_export(document)

    def test_requires_complete_matching_fictional_exports(self):
        bad = [None, {}, {"schema_version": 1, "provenance": evaluation.PROVENANCE, "cases": []}]
        for key, value in (
            ("status", "processing"),
            ("anonymized_text_raw", None),
            ("anonymized_text_raw", ""),
            ("anonymized_text_raw", "x" * 12_001),
            ("original_text", "Some real user information"),
        ):
            document = fictional_export()
            document["cases"][0]["anonymizer_export"][key] = value
            bad.append(document)
        document = fictional_export()
        document["cases"][1] = deepcopy(document["cases"][0])
        bad.append(document)
        for document in bad:
            with self.subTest(document=document), self.assertRaises(evaluation.MaskingExportError):
                evaluation.evaluate_export(document)
