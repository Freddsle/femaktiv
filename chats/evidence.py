"""Small, versioned, source-backed library; no user data in retrieval."""

import json
from functools import lru_cache

from django.conf import settings

from .transport import safe_url


@lru_cache(maxsize=1)
def library():
    document = json.loads((settings.BASE_DIR / "content" / "evidence.json").read_text())
    if document["version"] != 1:
        raise ValueError("Unsupported evidence library version")
    records = document["records"]
    ids = set()
    for record in records:
        if (
            record["id"] in ids
            or not record["passage"]
            or not record["applicability"]
            or not record["limitations"]
            or not record["organisation"]
        ):
            raise ValueError("Invalid evidence record")
        ids.add(record["id"])
        record["url"] = safe_url(record["url"])
        record["library_version"] = document["version"]
    return records


def retrieve(topic, topics):
    selected = set(topics)
    if topic == "nutrition" and not selected:
        selected = {"protein", "fibre"}
    if topic == "care":
        selected.add("care_support")
    return [dict(record) for record in library() if selected.intersection(record["topics"])]


def snapshot(record):
    # Store complete source provenance and the exact supporting passage with the reply.
    return dict(record)
