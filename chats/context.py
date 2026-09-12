"""Explicit, chat-scoped context. Caller holds the chat lock for mutations."""

import unicodedata
from uuid import UUID

from django.utils import timezone

from notes.models import PersonalNote

from .errors import ChatError
from .models import ActiveNote, ChatTurn

MAX_CONTEXT_CHARACTERS = 60_000


def public_context(chat):
    return {
        "version": chat.context_version,
        "started_at": chat.context_started_at.isoformat() if chat.context_started_at else None,
        "locality": chat.locality,
        "notes": [
            {
                "id": str(note.original_note_id),
                "title": note.title,
                "body": note.body,
                "can_refresh": note.source_note_id is not None,
            }
            for note in chat.active_notes.all()
        ],
    }


def start_segment(chat):
    chat.context_version += 1
    chat.context_started_at = timezone.now()
    chat.save(update_fields=["context_version", "context_started_at", "locality", "updated_at"])
    invalidate_pending(chat)


def invalidate_pending(chat):
    chat.turns.filter(status=ChatTurn.Status.PROCESSING).update(
        status=ChatTurn.Status.FAILED,
        error_code="context_changed",
        error_status=409,
        content="",
        note_copies=[],
    )


def validate_locality(value):
    if not isinstance(value, str):
        raise ChatError("invalid_locality", 400)
    value = " ".join(unicodedata.normalize("NFC", value).split())
    if not value:
        return ""
    if len(value) > 80:
        raise ChatError("invalid_locality", 400)
    if value.isascii() and value.isdigit() and len(value) == 5:
        return value
    if not all(character.isalpha() or character in " -'’()." for character in value):
        raise ChatError("invalid_locality", 400)
    if not any(character.isalpha() for character in value):
        raise ChatError("invalid_locality", 400)
    return value


def update(chat, payload):
    if not isinstance(payload, dict):
        raise ChatError("invalid_context", 400)
    action = payload.get("action")
    if action == "locality" and set(payload) == {"action", "locality"}:
        locality = validate_locality(payload["locality"])
        if locality == chat.locality:
            return False
        first_locality = not chat.locality
        chat.locality = locality
        if first_locality:
            # Filling a clarification must not erase the question it clarifies.
            chat.save(update_fields=["locality", "updated_at"])
            invalidate_pending(chat)
            return False
    elif action == "reset" and set(payload) == {"action"}:
        pass
    elif action in {"remove", "refresh"} and set(payload) == {"action", "note_id"}:
        try:
            note_id = UUID(payload["note_id"])
        except ValueError, TypeError, AttributeError:
            raise ChatError("invalid_context", 400) from None
        active = chat.active_notes.filter(original_note_id=note_id).first()
        if active is None:
            raise ChatError("not_found", 404)
        if action == "remove":
            active.delete()
        else:
            note = PersonalNote.objects.filter(pk=active.source_note_id, owner=chat.owner).first()
            if note is None:
                raise ChatError("not_found", 404)
            active.title, active.body = note.title, note.body
            active.save(update_fields=["title", "body"])
    else:
        raise ChatError("invalid_context", 400)
    start_segment(chat)
    return True


def prepare(chat, *, content, note_ids):
    if not chat.context_version:
        start_segment(chat)
    existing = {note.original_note_id for note in chat.active_notes.all()}
    missing = set(note_ids) - existing
    if len(existing | missing) > 5:
        raise ChatError("note_limit", 400)
    selected = list(PersonalNote.objects.filter(owner=chat.owner, pk__in=missing))
    if len(selected) != len(missing):
        raise ChatError("not_found", 404)
    ActiveNote.objects.bulk_create(
        [
            ActiveNote(
                chat=chat,
                source_note=note,
                original_note_id=note.pk,
                title=note.title,
                body=note.body,
            )
            for note in selected
        ]
    )
    copies = [
        {"original_note_id": str(note.original_note_id), "title": note.title, "body": note.body}
        for note in chat.active_notes.all()
    ]
    history = list(
        chat.messages.filter(context_version=chat.context_version, mode="live")
        .order_by("created_at", "id")
        .values("role", "content")
    )
    history.append({"role": "user", "content": content})
    size = sum(len(message["content"]) for message in history)
    size += sum(len(note["title"]) + len(note["body"]) for note in copies)
    if size > MAX_CONTEXT_CHARACTERS:
        raise ChatError("context_too_large", 413)
    return history, copies
