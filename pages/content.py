"""Read-only bilingual examples, independent of presentation and private data."""

import json
from functools import lru_cache

from django.conf import settings
from django.utils.translation import get_language


@lru_cache(maxsize=1)
def _load():
    return json.loads((settings.BASE_DIR / "content" / "examples.json").read_text())


def examples():
    language = "de" if get_language() == "de" else "en"
    return _load()[language]
