"""Versioned schemas shared by provider requests and server validation."""

import re

from jsonschema import Draft202012Validator

from .errors import ChatError

TOPICS = [
    "salt",
    "protein",
    "fibre",
    "dash",
    "discharge",
    "care_support",
    "iron",
    "b12",
    "calcium",
    "vitamin_d",
]
SERVICE_CATEGORIES = {
    "care_advice": "Pflegeberatung Pflegestützpunkt",
    "hospital_discharge": "Entlassmanagement Krankenhaus Sozialdienst",
    "home_care": "ambulante Pflege Beratung",
    "household_help": "Haushaltshilfe Pflegeberatung",
    "rehabilitation": "Rehabilitation Beratung",
}


def object_schema(properties):
    return {
        "type": "object",
        "properties": properties,
        "required": list(properties),
        "additionalProperties": False,
    }


def text_schema(limit, minimum=1):
    return {"type": "string", "minLength": minimum, "maxLength": limit}


INTAKE_SCHEMA = object_schema(
    {
        "topic": {"type": "string", "enum": ["general", "nutrition", "care"]},
        "decision": {"type": "string", "enum": ["answer", "clarification", "urgent"]},
        "intro": text_schema(600, 0),
        "facts": {"type": "array", "items": text_schema(500), "maxItems": 24},
        "questions": {"type": "array", "items": text_schema(350), "maxItems": 3},
        "evidence_topics": {
            "type": "array",
            "items": {"type": "string", "enum": TOPICS},
            "uniqueItems": True,
            "maxItems": len(TOPICS),
        },
        "needs_local_services": {"type": "boolean"},
        "service_category": {"type": "string", "enum": list(SERVICE_CATEGORIES)},
    }
)


def answer_schema(source_ids):
    references = {"type": "array", "items": {"type": "string"}, "uniqueItems": True, "maxItems": 4}
    if source_ids:
        references["items"]["enum"] = list(source_ids)
    else:
        references["maxItems"] = 0
    return object_schema(
        {
            "paragraphs": {
                "type": "array",
                "minItems": 1,
                "maxItems": 10,
                "items": object_schema(
                    {
                        "text": text_schema(1800),
                        "kind": {
                            "type": "string",
                            "enum": ["explanation", "suggestion", "question"],
                        },
                        "source_ids": references,
                    }
                ),
            },
        }
    )


def validate(value, schema):
    # Error objects include instance data: deliberately never format or log them.
    if not Draft202012Validator(schema).is_valid(value):
        raise ChatError("invalid_reply")
    return value


def validate_prose(text):
    if not text.strip() or re.search(
        r"\[\[|\[(?:PERSON|NAME|LOCATION|ADDRESS|EMAIL|PHONE|ORG)[_ :\d][^\]]*\]|https?://|www\.|\b\S+@\S+|(?:\d[ ()+./-]*){9,}",
        text,
        re.I,
    ):
        raise ChatError("invalid_reply")
    return text
