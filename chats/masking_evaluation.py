"""Offline checks of operator-supplied anonymizer exports for fixed fictional text.

Anymize's anonymous-chat endpoint does not document a masked-input inspection
response with ZDR. This deliberately never uses a generated answer as a proxy
for that input, accesses saved jobs, or changes the production account setting.
"""

import re
import unicodedata

PROVENANCE = "operator-supplied-anymize-anonymizer-export"
MAX_EXPORT_BYTES = 64_000
LIMITATIONS = (
    "The operator supplies actual anonymizer exports for predefined fictional inputs; "
    "their provenance is not independently attested. These checks measure only these "
    "samples, not every identifier, clinical correctness, legal correctness, or the exact "
    "input of a production anonymous-chat call. ZDR remains enabled for production; "
    "the documented ZDR chat response does not expose its masked input for inspection. "
    "Do not disable production ZDR to obtain exports."
)

# Each check includes useful fragments, so merely removing punctuation, the
# country prefix, or one component of a person's name cannot count as masking.
IDENTIFIERS = {
    "personal_names": ("Leonie", "Testfeld", "Markus", "Mustermann"),
    "street_address": ("Fiktivweg",),
    "birth_date": ("1970-05-13", "1970"),
    "email": ("leonie.testfeld@example.invalid",),
    "phone": ("+49 30 23125000", "23125000"),
    "iban": ("DE89 3704 0044 0532 0130 00", "0532013000"),
    "identity_number": ("T22000129",),
    "legal_case_number": ("12 C 345/26", "345/26"),
    "contract_number": ("FA-2026-7319", "2026-7319"),
}

CASES = (
    {
        "case": "privacy-en",
        "language": "en",
        "text": (
            "Fictional evaluation only. My mother Leonie Testfeld was born on 1970-05-13 "
            "and lives at Fiktivweg 17. Her email is leonie.testfeld@example.invalid, "
            "phone +49 30 23125000, IBAN DE89 3704 0044 0532 0130 00 and identity "
            "document number T22000129. Her lawyer Markus Mustermann handles case "
            "12 C 345/26 and contract FA-2026-7319. The reply deadline is 14 days after "
            "receiving the letter. My mother has hypertension and an allergy to milk "
            "protein. Avoiding fish is a preference, not an allergy. She has a broken "
            "leg, lives alone, cannot manage stairs and needs help after hospital "
            "discharge. I can cook for fifteen minutes and prefer English, but need "
            "help preparing a call in German."
        ),
        "facts": {
            "mother_role": r"my mother",
            "lawyer_role": r"her lawyer",
            "condition": r"has hypertension",
            "milk_protein_allergy": r"allergy to milk protein",
            "preference_not_allergy": r"avoiding fish is a preference, not an allergy",
            "injury": r"broken leg",
            "lives_alone": r"lives alone",
            "stairs_constraint": r"cannot manage stairs",
            "care_need": r"needs help after hospital discharge",
            "cooking_time": r"cook for fifteen minutes",
            "language_need": r"prefer english, but need help preparing a call in german",
            "relevant_deadline": r"14 days after receiving the letter",
        },
    },
    {
        "case": "privacy-de",
        "language": "de",
        "text": (
            "Nur ein fiktives Prüfbeispiel. Meine Mutter Leonie Testfeld wurde am "
            "1970-05-13 geboren und wohnt im Fiktivweg 17. Ihre E-Mail lautet "
            "leonie.testfeld@example.invalid, ihre Telefonnummer +49 30 23125000, "
            "ihre IBAN DE89 3704 0044 0532 0130 00 und ihre Ausweisnummer T22000129. "
            "Ihr Anwalt Markus Mustermann betreut das Aktenzeichen 12 C 345/26 und "
            "den Vertrag FA-2026-7319. Die Antwortfrist beträgt 14 Tage nach Erhalt "
            "des Briefes. Meine Mutter hat Bluthochdruck und eine Allergie gegen "
            "Milcheiweiß. Fisch zu vermeiden ist eine Vorliebe, keine Allergie. Sie "
            "hat ein gebrochenes Bein, lebt allein, schafft keine Treppen und braucht "
            "Hilfe nach der Krankenhausentlassung. Ich habe fünfzehn Minuten zum "
            "Kochen und bevorzuge Englisch, brauche aber Hilfe für ein Telefonat "
            "auf Deutsch."
        ),
        "facts": {
            "mother_role": r"meine mutter",
            "lawyer_role": r"ihr anwalt",
            "condition": r"hat bluthochdruck",
            "milk_protein_allergy": r"allergie gegen milcheiweiß",
            "preference_not_allergy": r"fisch zu vermeiden ist eine vorliebe, keine allergie",
            "injury": r"gebrochenes bein",
            "lives_alone": r"lebt allein",
            "stairs_constraint": r"schafft keine treppen",
            "care_need": r"braucht hilfe nach der krankenhausentlassung",
            "cooking_time": r"fünfzehn minuten zum kochen",
            "language_need": r"bevorzuge englisch, brauche aber hilfe für ein telefonat auf deutsch",
            "relevant_deadline": r"14 tage nach erhalt des briefes",
        },
    },
)

PLACEHOLDER = re.compile(r"\[\[[A-Za-z_ÄÖÜäöüß-]{2,40}-[A-Za-z0-9]{3,64}\]\]")


class MaskingExportError(ValueError):
    """Only a fixed error code is exposed, never operator-supplied content."""


def export_inputs():
    return {
        "schema_version": 1,
        "fictional_only": True,
        "cases": [{key: case[key] for key in ("case", "language", "text")} for case in CASES],
    }


def _compact(text):
    return "".join(
        char for char in unicodedata.normalize("NFKC", text).casefold() if char.isalnum()
    )


def _plain(text):
    return " ".join(unicodedata.normalize("NFKC", text).casefold().split())


def _only_source_text_or_placeholders(text, original):
    """Prevent arbitrary new export content from entering the review report.

    An anonymizer replaces spans; it does not compose new prose. Preserve the
    actual masked text only if all unmasked fragments occur in source order.
    """
    original = _plain(original)
    offset = 0
    for fragment in PLACEHOLDER.split(text):
        fragment = _plain(fragment)
        if not fragment:
            continue
        location = original.find(fragment, offset)
        if location < 0:
            return False
        offset = location + len(fragment)
    return True


def evaluate_export(document):
    if (
        not isinstance(document, dict)
        or document.get("schema_version") != 1
        or document.get("provenance") != PROVENANCE
        or not isinstance(document.get("cases"), list)
        or len(document["cases"]) != len(CASES)
    ):
        raise MaskingExportError("invalid_masking_export")
    by_name = {}
    for item in document["cases"]:
        if (
            not isinstance(item, dict)
            or not isinstance(item.get("case"), str)
            or item["case"] in by_name
        ):
            raise MaskingExportError("invalid_masking_export")
        by_name[item["case"]] = item
    if set(by_name) != {case["case"] for case in CASES}:
        raise MaskingExportError("invalid_masking_export")
    results = []
    for case in CASES:
        exported = by_name[case["case"]].get("anonymizer_export")
        if (
            not isinstance(exported, dict)
            or exported.get("status") != "completed"
            or exported.get("original_text") != case["text"]
            or not isinstance(exported.get("anonymized_text_raw"), str)
            or not 1 <= len(exported["anonymized_text_raw"]) <= 12_000
        ):
            raise MaskingExportError("invalid_masking_export")
        text = exported["anonymized_text_raw"]
        compact = _compact(text)
        removals = {
            category: not any(_compact(value) in compact for value in values)
            for category, values in IDENTIFIERS.items()
        }
        facts = {
            name: bool(re.search(pattern.casefold(), _plain(text)))
            for name, pattern in case["facts"].items()
        }
        faithful = _only_source_text_or_placeholders(text, case["text"])
        item = {
            "case": case["case"],
            "identifier_removal": removals,
            "essential_facts": facts,
            "only_source_text_or_placeholders": faithful,
            "passed": faithful and all(removals.values()) and all(facts.values()),
        }
        if faithful:
            item["masked_text_for_human_review"] = text
        results.append(item)
    return {
        "status": "passed" if all(item["passed"] for item in results) else "failed",
        "passed": all(item["passed"] for item in results),
        "provenance": PROVENANCE,
        "provenance_independently_attested": False,
        "cases": results,
        "limitations": LIMITATIONS,
    }
