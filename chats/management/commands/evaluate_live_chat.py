"""Explicit paid smoke evaluation using only fictional, predefined examples."""

import json
import os
import re
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from chats import provider, service
from chats.errors import ChatError
from chats.transport import Budget

CASES = [
    (
        "nutrition-en",
        "en",
        "",
        "Fictional example: I am a woman in Germany with hypertension and an allergy to milk protein. I have fifteen minutes to make lunch and want more protein and fibre with less salt. Please suggest practical food combinations.",
        [
            r"hypertension|blood pressure|blutdruck",
            r"milk|dairy|milch",
            r"allerg",
            r"fifteen|15|fünfzehn",
        ],
    ),
    (
        "nutrition-de",
        "de",
        "",
        "Fiktives Beispiel: Ich bin eine Frau in Deutschland mit Bluthochdruck und einer Milcheiweißallergie. Ich habe fünfzehn Minuten fürs Mittagessen und möchte mehr Protein und Ballaststoffe bei weniger Salz. Bitte schlage praktische Lebensmittelkombinationen vor.",
        [
            r"hypertension|blood pressure|blutdruck",
            r"milk|dairy|milch",
            r"allerg",
            r"fifteen|15|fünfzehn",
        ],
    ),
    (
        "care-en",
        "en",
        "Berlin",
        "Fictional example: My older mother is still in hospital with a broken leg. She lives alone, cannot manage stairs and is expected home next week. I need local care advice and help preparing a call in German; I prefer English. The separate locality is Berlin.",
        [r"mother|mutter", r"broken|fractur|bruch|gebroch", r"alone|allein", r"stairs|trepp"],
    ),
    (
        "care-de",
        "de",
        "Berlin",
        "Fiktives Beispiel: Meine ältere Mutter liegt mit einem gebrochenen Bein noch im Krankenhaus. Sie lebt allein, schafft keine Treppen und soll nächste Woche nach Hause. Ich suche eine örtliche Pflegeberatung und Formulierungen für ein Gespräch auf Deutsch. Der separate Ort ist Berlin.",
        [r"mother|mutter", r"broken|fractur|bruch|gebroch", r"alone|allein", r"stairs|trepp"],
    ),
]


class Command(BaseCommand):
    help = "Opt-in live evaluation of fictional chat cases (up to 8 model calls and 4 searches)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--allow-provider-calls",
            action="store_true",
            help="Explicitly allow paid Anymize and Brave calls.",
        )
        parser.add_argument(
            "--output", default=str(settings.BASE_DIR / ".local" / "live-chat-evaluation.json")
        )

    def handle(self, *args, **options):
        if not options["allow_provider_calls"]:
            raise CommandError(
                "No calls made. Supply --allow-provider-calls to run the fictional live evaluation."
            )
        if os.environ.get("FEMAKTIV_OFFLINE_CHECKS") == "1":
            raise CommandError(
                "No calls made. External services are disabled during automated checks."
            )
        if settings.FEMAKTIV_AI_MODE != "live":
            raise CommandError("No calls made. Configure FEMAKTIV_AI_MODE=live first.")
        report = {
            "checked_at": timezone.now().isoformat(),
            "model": settings.ANYMIZE_MODEL,
            "cases": [],
            "limitations": "Metadata and structured fact checks do not establish anonymization accuracy or clinical correctness. Review final answer usefulness separately.",
        }
        try:
            if settings.ANYMIZE_MODEL not in provider.available_models(Budget()):
                raise ChatError("not_configured", 503)
            report["model_available"] = True
            for name, language, locality, content, facts in CASES:
                item = {"case": name}
                report["cases"].append(item)
                captured = []
                try:
                    reply = service.generate_reply(
                        history=[{"role": "user", "content": content}],
                        context=[],
                        language=language,
                        locality=locality,
                        intake_observer=captured.append,
                    )
                    combined = " ".join(captured[0]["facts"]).casefold()
                    item.update(
                        {
                            "structured_output": True,
                            "anonymization_metadata": True,
                            "essential_facts": all(
                                re.search(pattern, combined) for pattern in facts
                            ),
                            "kind": reply.kind,
                            "has_citations": bool(reply.citations),
                            "lookup_status": reply.lookup_status,
                            "reply_for_human_review": reply.content,
                        }
                    )
                    item["passed"] = (
                        item["essential_facts"] and item["has_citations"] and reply.kind == "answer"
                    )
                    if locality:
                        item["passed"] = item["passed"] and reply.lookup_status == "verified"
                    if not item["passed"]:
                        break  # No automatic paid retries, including evaluation failures.
                except ChatError as error:
                    item.update({"passed": False, "error_code": error.code})
                    break
        except ChatError as error:
            report["error_code"] = error.code
        report["passed"] = len(report["cases"]) == len(CASES) and all(
            item.get("passed") for item in report["cases"]
        )
        output = Path(options["output"])
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
        self.stdout.write(f"Fictional evaluation report: {output}")
        self.stdout.write(report["limitations"])
        if not report["passed"]:
            raise CommandError(
                "Live evaluation did not pass. See the safe report; no automatic retry was made."
            )
        self.stdout.write(
            self.style.SUCCESS(
                "Model, structured output, metadata, essential facts, citations and contact lookup checks passed."
            )
        )
