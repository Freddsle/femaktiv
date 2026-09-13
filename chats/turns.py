"""Durable reservations; external work happens after the reservation commits."""

import hashlib
import json

from django.contrib.auth import get_user_model
from django.db import IntegrityError, OperationalError, transaction
from django.http import JsonResponse
from django.urls import reverse
from django.utils import timezone, translation
from django.utils.translation import gettext as _

from notes.forms import PersonalNoteForm

from . import context, provider, service, usage
from .errors import ChatError
from .models import Chat, ChatTurn, Message, MessageContextSnapshot
from .transport import Budget


def error_response(error, *, terminal=False, chat=None):
    return JsonResponse(
        {
            "mode": "live",
            "status": "failed" if terminal else "rejected",
            "error": {"code": error.code, "message": str(error.message), "terminal": terminal},
            "active_context": context.public_context(chat) if chat else None,
        },
        status=error.status,
    )


def serialize(message):
    citations = message.citations
    indexed = {source["id"]: source for source in citations}
    paragraphs = [
        {
            **paragraph,
            "citations": [
                indexed[source_id] for source_id in paragraph["source_ids"] if source_id in indexed
            ],
        }
        for paragraph in message.paragraphs
    ]
    return {
        "id": str(message.id),
        "role": message.role,
        "content": message.content,
        "created_at": message.created_at.isoformat(),
        "mode": message.mode,
        "kind": message.kind,
        "paragraphs": paragraphs,
        "citations": citations,
        "urgent_help": message.urgent_help,
        "lookup_status": message.lookup_status,
        "saved_note": (
            {
                "id": str(message.saved_note_id),
                "title": message.saved_note.title,
                "url": reverse("notes:edit", kwargs={"pk": message.saved_note_id}),
            }
            if message.saved_note_id
            else None
        ),
        "context": [
            {"title": note.title, "body": note.body} for note in message.context_snapshots.all()
        ],
    }


def expire(chat):
    chat.turns.filter(status=ChatTurn.Status.PROCESSING, expires_at__lte=timezone.now()).update(
        status=ChatTurn.Status.FAILED,
        error_code="deadline_exceeded",
        error_status=504,
        content="",
        note_copies=[],
    )


def result(chat, turn, *, status=200):
    if turn.status == ChatTurn.Status.PROCESSING:
        return JsonResponse(
            {
                "mode": "live",
                "status": "processing",
                "client_request_id": str(turn.client_request_id),
                "chat": {"id": str(chat.pk)},
                "active_context": context.public_context(chat),
            },
            status=202,
        )
    if turn.status == ChatTurn.Status.FAILED:
        return error_response(
            ChatError(turn.error_code, turn.error_status), terminal=True, chat=chat
        )
    pair = list(
        chat.messages.filter(client_request_id=turn.client_request_id)
        .select_related("saved_note")
        .prefetch_related("context_snapshots")
    )
    if len(pair) != 2:
        return error_response(ChatError("provider_unavailable", 503), terminal=True)
    return JsonResponse(
        {
            "mode": "live",
            "status": "completed",
            "client_request_id": str(turn.client_request_id),
            "kind": next(
                message.kind for message in pair if message.role == Message.Role.ASSISTANT
            ),
            "user_message": serialize(
                next(message for message in pair if message.role == Message.Role.USER)
            ),
            "assistant_message": serialize(
                next(message for message in pair if message.role == Message.Role.ASSISTANT)
            ),
            "chat": {"id": str(chat.pk), "title": chat.title},
            "active_context": context.public_context(chat),
        },
        status=status,
    )


def fingerprint(content, note_ids):
    payload = json.dumps([content, sorted(str(value) for value in note_ids)], ensure_ascii=False)
    return hashlib.sha256(payload.encode()).hexdigest()


def reserve(*, owner, pk, request_id, content, note_ids, language):
    with transaction.atomic():
        usage.lock_gate()
        account = get_user_model().objects.select_for_update().filter(pk=owner.pk).first()
        if account is None or not account.is_active:
            raise ChatError("not_found", 404)
        chat = Chat.objects.select_for_update().filter(pk=pk, owner=owner).first()
        if chat is None:
            raise ChatError("not_found", 404)
        expire(chat)
        digest = fingerprint(content, note_ids)
        previous = chat.turns.filter(client_request_id=request_id).first()
        if previous:
            if previous.fingerprint != digest:
                raise ChatError("request_conflict", 409)
            return result(chat, previous)
        if chat.messages.filter(client_request_id=request_id).exists():
            raise ChatError("request_conflict", 409)
        if chat.turns.filter(status=ChatTurn.Status.PROCESSING).exists():
            raise ChatError("chat_busy", 409)
        if not account.live_chat_enabled:
            raise ChatError("live_access_denied", 403)
        provider.require_configuration()
        allowance = usage.reserve(account)
        history, copies = context.prepare(chat, content=content, note_ids=note_ids)
        turn = ChatTurn.objects.create(
            chat=chat,
            usage=allowance,
            client_request_id=request_id,
            fingerprint=digest,
            content=content,
            note_copies=copies,
            context_version=chat.context_version,
            language=language,
            expires_at=allowance.expires_at,
        )
        return chat, turn, history


def fail(turn_id, error):
    ChatTurn.objects.filter(pk=turn_id, status=ChatTurn.Status.PROCESSING).update(
        status=ChatTurn.Status.FAILED,
        error_code=error.code,
        error_status=error.status,
        content="",
        note_copies=[],
    )


def failed_result(turn, error):
    try:
        fail(turn.pk, error)
        chat = Chat.objects.filter(pk=turn.chat_id).first()
        if chat is None:
            return error_response(ChatError("not_found", 404), terminal=True)
        latest = chat.turns.get(pk=turn.pk)
        return result(chat, latest)
    except ChatTurn.DoesNotExist:
        return error_response(ChatError("not_found", 404), terminal=True)
    except IntegrityError, OperationalError:
        # Persistence is ambiguous. Keep the id so the next deliberate send recovers
        # the original reservation instead of initiating another provider request.
        return error_response(ChatError("provider_unavailable", 503))


def recover_reservation(owner, pk, request_id, content, note_ids):
    try:
        chat = Chat.objects.filter(pk=pk, owner=owner).first()
        if chat:
            previous = chat.turns.filter(client_request_id=request_id).first()
            if previous:
                if previous.fingerprint != fingerprint(content, note_ids):
                    return error_response(ChatError("request_conflict", 409))
                return result(chat, previous)
        return error_response(ChatError("chat_busy", 409))
    except IntegrityError, OperationalError:
        return error_response(ChatError("provider_unavailable", 503))


def save_reply(chat_id, turn_id, reply):
    with transaction.atomic():
        chat = Chat.objects.select_for_update().filter(pk=chat_id).first()
        if chat is None:
            raise ChatError("not_found", 404)
        expire(chat)
        turn = chat.turns.get(pk=turn_id)
        if turn.status != ChatTurn.Status.PROCESSING:
            return result(chat, turn)
        if chat.context_version != turn.context_version:
            raise ChatError("context_changed", 409)
        ensure_active(turn.pk)
        saved_note = None
        paragraphs = list(reply.paragraphs)
        reply_content = reply.content
        if reply.note_to_save is not None:
            form = PersonalNoteForm(
                {"title": reply.note_to_save.title, "body": reply.note_to_save.body}
            )
            if not form.is_valid():
                raise ChatError("invalid_reply")
            saved_note = form.save(commit=False)
            saved_note.owner_id = chat.owner_id
            saved_note.save()
            with translation.override(turn.language):
                receipt = _("Your note has been saved.")
            if not paragraphs and reply_content:
                paragraphs.append({"text": reply_content, "kind": "suggestion", "source_ids": []})
            paragraphs.append({"text": receipt, "kind": "suggestion", "source_ids": []})
            reply_content = "\n\n".join(paragraph["text"] for paragraph in paragraphs)
        first_message = not chat.messages.exists()
        user_message = Message.objects.create(
            chat=chat,
            role=Message.Role.USER,
            content=turn.content,
            mode="live",
            language=turn.language,
            client_request_id=turn.client_request_id,
            context_version=turn.context_version,
        )
        # These are copies of the exact input, even if a source note changed during inference.
        MessageContextSnapshot.objects.bulk_create(
            [
                MessageContextSnapshot(
                    message=user_message,
                    original_note_id=note["original_note_id"],
                    title=note["title"],
                    body=note["body"],
                )
                for note in turn.note_copies
            ]
        )
        Message.objects.create(
            chat=chat,
            role=Message.Role.ASSISTANT,
            content=reply_content,
            mode="live",
            language=turn.language,
            client_request_id=turn.client_request_id,
            context_version=turn.context_version,
            kind=reply.kind,
            paragraphs=paragraphs,
            citations=reply.citations,
            urgent_help=reply.urgent_help,
            lookup_status=reply.lookup_status,
            saved_note=saved_note,
        )
        if first_message:
            chat.title = " ".join(turn.content.split())[:70]
        chat.save(update_fields=["title", "updated_at"])
        turn.status = ChatTurn.Status.COMPLETED
        turn.content, turn.note_copies = "", []
        turn.save(update_fields=["status", "content", "note_copies"])
        return result(chat, turn, status=201)


def ensure_active(turn_id):
    state = (
        ChatTurn.objects.filter(pk=turn_id)
        .values(
            "status",
            "context_version",
            "chat__context_version",
            "expires_at",
            "error_code",
            "error_status",
            "chat__owner__live_chat_enabled",
            "chat__owner__is_active",
        )
        .first()
    )
    if state is None:
        raise ChatError("not_found", 404)
    if not state["chat__owner__live_chat_enabled"] or not state["chat__owner__is_active"]:
        raise ChatError("live_access_denied", 403)
    if state["status"] == ChatTurn.Status.FAILED:
        raise ChatError(state["error_code"], state["error_status"])
    if (
        state["status"] != ChatTurn.Status.PROCESSING
        or state["context_version"] != state["chat__context_version"]
    ):
        raise ChatError("context_changed", 409)
    if state["expires_at"] <= timezone.now():
        raise ChatError("deadline_exceeded", 504)


def submit(*, owner, pk, request_id, content, note_ids, language):
    turn = None
    try:
        reservation = reserve(
            owner=owner,
            pk=pk,
            request_id=request_id,
            content=content,
            note_ids=note_ids,
            language=language,
        )
        if isinstance(reservation, JsonResponse):
            return reservation
        chat, turn, history = reservation
        budget = Budget(
            seconds=max(0, (turn.expires_at - timezone.now()).total_seconds()),
            active_check=lambda: ensure_active(turn.pk),
        )
        reply = service.generate_reply(
            history=history,
            context=[service.ContextNote(note["title"], note["body"]) for note in turn.note_copies],
            language=language,
            budget=budget,
        )
        budget.remaining()
        return save_reply(chat.pk, turn.pk, reply)
    except ChatError as error:
        if turn:
            return failed_result(turn, error)
        return error_response(error)
    except IntegrityError, OperationalError:
        # A racing reservation may have won. Recover only; never repeat external work.
        if turn:
            return failed_result(turn, ChatError("provider_unavailable", 503))
        return recover_reservation(owner, pk, request_id, content, note_ids)
    except Exception:
        # Do not expose or log provider payloads through framework exception reporting.
        if turn:
            return failed_result(turn, ChatError("provider_unavailable", 503))
        return error_response(ChatError("provider_unavailable", 503))
    finally:
        if turn is not None:
            usage.finish(turn.usage_id)
