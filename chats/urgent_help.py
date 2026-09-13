"""Application-owned German national numbers, source-checked 2026-09-13.

Sources establish service boundaries, not automated medical triage accuracy.
Translate at creation time so saved replies retain their original language.
"""

from django.utils.translation import gettext as _


def panel():
    return {
        "heading": _("If you are in Germany"),
        "contacts": [
            {
                "number": "112",
                "label": _("Emergency services"),
                "description": _(
                    "Call immediately if someone's life is in danger or lasting harm is possible."
                ),
                "source_title": "gesund.bund.de",
                "source_url": "https://gesund.bund.de/notfallnummern",
            },
            {
                "number": "116117",
                "label": _("Medical on-call service"),
                "description": _(
                    "For urgent problems that are not life-threatening, when medical practices are closed and treatment cannot wait until they reopen. Telephone advice is in German."
                ),
                "source_title": "116117.de",
                "source_url": "https://www.116117.de/de/englisch.php",
            },
        ],
    }
