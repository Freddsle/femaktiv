"""The only model adapter. Private text always uses the anonymous route."""

import json

from django.conf import settings

from . import transport
from .contracts import validate
from .errors import ChatError

BASE_URL = "https://app.anymize.ai/api/v1/llm"
ANONYMOUS_URL = "https://app.anymize.ai/api/v1/llm-anonymous/chat/completions"


def require_configuration():
    if not all(
        (
            settings.ANYMIZE_API_KEY,
            settings.ANYMIZE_MODEL,
            settings.BRAVE_SEARCH_API_KEY,
            settings.ANYMIZE_ZDR_CONFIRMED,
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
                "json_schema": {"name": name, "strict": True, "schema": schema},
            },
        },
    )
    if (
        not isinstance(result, dict)
        or not isinstance(result.get("_anymize"), dict)
        or result["_anymize"].get("anonymized") is not True
    ):
        raise ChatError("privacy_failed")
    try:
        choice = result["choices"][0]
        if choice.get("finish_reason") != "stop" or choice["message"].get("tool_calls"):
            raise ValueError
        text = choice["message"]["content"]
        if not isinstance(text, str) or len(text) > 24000:
            raise ValueError
        output = json.loads(text)
    except KeyError, IndexError, TypeError, ValueError, AttributeError:
        raise ChatError("invalid_reply") from None
    budget.remaining()
    return validate(output, schema)
