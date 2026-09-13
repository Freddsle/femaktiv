"""Fictional offline provider fixtures. These are not live quality evaluations."""

LIVE_SETTINGS = {
    "FEMAKTIV_AI_MODE": "live",
    "ANYMIZE_API_KEY": "fictional-anymize-key",
    "ANYMIZE_MODEL": "fictional-model",
    "ANYMIZE_ZDR_CONFIRMED": True,
    "ANYMIZE_FALLBACKS_DISABLED_CONFIRMED": True,
}


def intake(**changes):
    return {
        "topic": "nutrition",
        "decision": "answer",
        "medical_referral": "none",
        "intro": "",
        "facts": ["The user has hypertension", "Milk allergy", "Fifteen minutes for cooking"],
        "questions": [],
        "evidence_topics": ["protein", "fibre", "dash", "salt"],
        **changes,
    }


def answer(language="en", care=False):
    if care:
        text = "Ask the hospital social service about the discharge plan. German: Welche Unterstützung ist nach der Entlassung möglich? English: What support is possible after discharge?"
        if language == "de":
            text = "Frage den Sozialdienst nach dem Entlassplan: Welche Unterstützung ist nach der Entlassung möglich?"
        return {
            "medical_referral": "none",
            "paragraphs": [{"text": text, "kind": "explanation", "source_ids": ["bund-discharge"]}],
        }
    return {
        "medical_referral": "none",
        "paragraphs": [
            {
                "text": "Lentils provide protein and fibre."
                if language == "en"
                else "Linsen liefern Protein und Ballaststoffe.",
                "kind": "explanation",
                "source_ids": ["dge-food"],
            },
            {
                "text": "Try a quick lentil bowl with vegetables, without milk."
                if language == "en"
                else "Probiere eine schnelle Linsenschale mit Gemüse, ohne Milch.",
                "kind": "suggestion",
                "source_ids": [],
            },
        ],
    }
