"""The only model adapter. Private text always uses the anonymous route."""

import json
from copy import deepcopy

from django.conf import settings

from . import transport
from .contracts import validate
from .errors import ChatError

BASE_URL = "https://app.anymize.ai/api/v1/llm"
ANONYMOUS_URL = "https://app.anymize.ai/api/v1/llm-anonymous/chat/completions"


def wire_schema(schema):
    """Send supported structural constraints; enforce the full schema locally."""
    # OpenAI Structured Outputs documents a subset of JSON Schema. String length
    # and uniqueness checks remain in our validator, never removed from acceptance.
    result = {
        key: deepcopy(value)
        for key, value in schema.items()
        if key not in {"minLength", "maxLength", "uniqueItems"}
    }
    for key in ("properties", "$defs"):
        if key in result:
            result[key] = {name: wire_schema(child) for name, child in result[key].items()}
    if "items" in result:
        result["items"] = wire_schema(result["items"])
    if "anyOf" in result:
        result["anyOf"] = [wire_schema(child) for child in result["anyOf"]]
    return result


def require_configuration():
    if not all(
        (
            settings.ANYMIZE_API_KEY,
            settings.ANYMIZE_MODEL,
            settings.ANYMIZE_ZDR_CONFIRMED,
            settings.ANYMIZE_FALLBACKS_DISABLED_CONFIRMED,
        )
    ):
        raise ChatError("not_configured", 503)


def available_models(budget):
    require_configuration()
    result = transport.request_json(
        BASE_URL + "/models",
        budget=budget,
        headers={"Authorization": f"Bearer {settings.ANYMIZE_API_KEY}"},
    )
    if not isinstance(result, dict) or not isinstance(result.get("data"), list):
        raise ChatError("invalid_reply")
    return {
        item["id"]
        for item in result["data"]
        if isinstance(item, dict) and isinstance(item.get("id"), str)
    }


def complete(*, messages, schema, name, language, budget):
    require_configuration()
    budget.consume("model")
    result = transport.request_json(
        ANONYMOUS_URL,
        budget=budget,
        headers={"Authorization": f"Bearer {settings.ANYMIZE_API_KEY}"},
        payload={
            "model": settings.ANYMIZE_MODEL,
            "messages": messages,
            "language": language,
            "stream": False,
            "max_tokens": 3000,
            "response_format": {
                "type": "json_schema",
                "json_schema": {"name": name, "strict": True, "schema": wire_schema(schema)},
            },
        },
    )
    if (
        not isinstance(result, dict)
        or not isinstance(result.get("_anymize"), dict)
        or result["_anymize"].get("anonymized") is not True
    ):
        raise ChatError("privacy_failed")
    choices = result.get("choices")
    if not isinstance(choices, list) or not choices or not isinstance(choices[0], dict):
        raise ChatError("invalid_reply", failure_reason="invalid_message")
    choice = choices[0]
    if choice.get("finish_reason") == "length":
        raise ChatError("invalid_reply", failure_reason="completion_truncated")
    message = choice.get("message")
    if isinstance(message, dict) and message.get("tool_calls"):
        raise ChatError("invalid_reply", failure_reason="unexpected_tool_call")
    if choice.get("finish_reason") != "stop":
        raise ChatError("invalid_reply", failure_reason="unexpected_completion")
    if not isinstance(message, dict):
        raise ChatError("invalid_reply", failure_reason="invalid_message")
    text = message.get("content")
    if not isinstance(text, str) or len(text) > 24000:
        raise ChatError("invalid_reply", failure_reason="invalid_message")
    try:
        output = json.loads(text)
    except ValueError, RecursionError:
        raise ChatError("invalid_reply", failure_reason="invalid_model_json") from None
    budget.remaining()
    return validate(output, schema)
