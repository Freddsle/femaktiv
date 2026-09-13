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

MEDICAL_REFERRALS = ["none", "urgent", "emergency"]


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
        "medical_referral": {"type": "string", "enum": MEDICAL_REFERRALS},
        "intro": text_schema(600, 0),
        "facts": {"type": "array", "items": text_schema(500), "maxItems": 24},
        "questions": {"type": "array", "items": text_schema(350), "maxItems": 3},
        "evidence_topics": {
            "type": "array",
            "items": {"type": "string", "enum": TOPICS},
            "uniqueItems": True,
            "maxItems": len(TOPICS),
        },
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
            "medical_referral": {"type": "string", "enum": MEDICAL_REFERRALS},
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
    error = next(Draft202012Validator(schema).iter_errors(value), None)
    if error is not None:
        raise ChatError(
            "invalid_reply", failure_reason="schema_validation", validation_rule=error.validator
        )
    return value


def validate_prose(text):
    if not text.strip():
        raise ChatError("invalid_reply", failure_reason="empty_prose")
    # Source URLs come from application-owned citation records. Identifier
    # masking and any restoration belong to Anymize, not this validator.
    if re.search(r"https?://|www\.", text, re.I):
        raise ChatError("invalid_reply", failure_reason="invalid_prose")
    return text
