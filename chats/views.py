import json
from uuid import UUID

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import RequestDataTooBig
from django.db import IntegrityError, OperationalError, transaction
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.translation import gettext as _
from django.views.decorators.http import require_GET, require_POST

from notes.models import PersonalNote

from . import context, turns
from .errors import ChatError
from .models import Chat, Message, MessageContextSnapshot
from .service import ContextNote, generate_reply


def _workspace(request, chat=None):
    entries = (
        list(chat.messages.select_related("saved_note").prefetch_related("context_snapshots"))
        if chat
        else []
    )
    for entry in entries:
        serialized = turns.serialize(entry)
        entry.display_paragraphs = serialized["paragraphs"]
        entry.display_saved_note = serialized["saved_note"]
    return render(
        request,
        "chats/workspace.html",
        {
            "section": "chats",
            "chats": Chat.objects.filter(owner=request.user),
            "current_chat": chat,
            "chat_messages": entries,
            "notes": PersonalNote.objects.filter(owner=request.user),
            "live_mode": settings.FEMAKTIV_AI_MODE == "live",
            "active_context": context.public_context(chat) if chat else None,
        },
    )


@login_required
def chat_list(request):
    return _workspace(request)


@login_required
@require_POST
def create(request):
    chat = Chat.objects.create(owner=request.user, title=_("New chat"))
    return redirect("chats:detail", pk=chat.pk)


@login_required
def detail(request, pk):
    return _workspace(request, get_object_or_404(Chat, pk=pk, owner=request.user))


@login_required
@require_POST
def rename(request, pk):
    chat = get_object_or_404(Chat, pk=pk, owner=request.user)
    title = request.POST.get("title", "").strip()
    if not title or len(title) > 120:
        messages.error(request, _("Choose a title between 1 and 120 characters."))
    else:
        chat.title = title
        chat.save(update_fields=["title", "updated_at"])
        messages.success(request, _("Chat renamed."))
    return redirect("chats:detail", pk=chat.pk)


@login_required
def delete(request, pk):
    chat = get_object_or_404(Chat, pk=pk, owner=request.user)
    if request.method == "POST":
        chat.delete()
        messages.success(request, _("Chat and attached copies deleted."))
        return redirect("chats:list")
    return render(request, "chats/confirm_delete.html", {"chat": chat, "section": "chats"})


def _error(code, message, status=400):
    return JsonResponse({"error": {"code": code, "message": message}}, status=status)


def _serialize(message):
    return {
        "id": str(message.id),
        "role": message.role,
        "content": message.content,
        "created_at": message.created_at.isoformat(),
        "mode": message.mode,
        "context": [{"title": s.title, "body": s.body} for s in message.context_snapshots.all()],
    }


def _turn_response(chat, user_message, assistant_message, status):
    return JsonResponse(
        {
            "mode": assistant_message.mode,
            "status": "completed",
            "kind": "answer",
            "user_message": _serialize(user_message),
            "assistant_message": _serialize(assistant_message),
            "chat": {"id": str(chat.id), "title": chat.title},
        },
        status=status,
    )


def _existing_turn(chat, request_id, content, note_ids):
    previous = list(
        chat.messages.filter(client_request_id=request_id).prefetch_related("context_snapshots")
    )
    if not previous:
        return None
    user_message = next(m for m in previous if m.role == Message.Role.USER)
    if user_message.content != content or {
        s.original_note_id for s in user_message.context_snapshots.all()
    } != set(note_ids):
        return _error(
            "request_conflict",
            _("This request was already used for another message. Refresh and try again."),
            409,
        )
    assistant_message = next(m for m in previous if m.role == Message.Role.ASSISTANT)
    return _turn_response(chat, user_message, assistant_message, 200)


@require_POST
def send_message(request, pk):
    if not request.user.is_authenticated:
        return _error(
            "authentication_required", _("Please log in again to send your message."), 401
        )
    try:
        payload = json.loads(request.body)
        if not isinstance(payload, dict) or set(payload) != {
            "content",
            "note_ids",
            "client_request_id",
        }:
            raise ValueError
        if (
            not isinstance(payload["content"], str)
            or not 1 <= len(payload["content"].strip()) <= 4000
        ):
            raise ValueError
        content = payload["content"].strip()
        if not isinstance(payload["note_ids"], list) or len(payload["note_ids"]) > 5:
            raise ValueError
        request_id = UUID(payload["client_request_id"])
        note_ids = [UUID(value) for value in payload["note_ids"]]
        if len(set(note_ids)) != len(note_ids):
            raise ValueError
    except RequestDataTooBig:
        return _error("body_too_large", _("This message is too large."), 413)
    except ValueError, TypeError, AttributeError:
        return _error(
            "invalid_input",
            _("Write a message of up to 4,000 characters and select no more than five notes."),
        )

    if settings.FEMAKTIV_AI_MODE == "live":
        return turns.submit(
            owner=request.user,
            pk=pk,
            request_id=request_id,
            content=content,
            note_ids=note_ids,
            language=request.LANGUAGE_CODE,
        )

    try:
        with transaction.atomic():
            chat = Chat.objects.select_for_update().filter(pk=pk, owner=request.user).first()
            if chat is None:
                return _error("not_found", _("This chat is not available."), 404)
            previous = _existing_turn(chat, request_id, content, note_ids)
            if previous is not None:
                return previous
            selected = {
                n.pk: n for n in PersonalNote.objects.filter(owner=request.user, pk__in=note_ids)
            }
            if len(selected) != len(note_ids):
                return _error(
                    "not_found",
                    _("One of the selected notes is no longer available. Update your selection."),
                    404,
                )
            notes = [selected[note_id] for note_id in note_ids]
            context = [ContextNote(n.title, n.body) for n in notes]
            history = list(chat.messages.order_by("created_at", "id").values("role", "content"))
            history.append({"role": "user", "content": content})
            reply = generate_reply(history=history, context=context, language=request.LANGUAGE_CODE)
            first_message = not chat.messages.exists()
            user_message = Message.objects.create(
                chat=chat,
                role=Message.Role.USER,
                content=content,
                language=request.LANGUAGE_CODE,
                client_request_id=request_id,
            )
            MessageContextSnapshot.objects.bulk_create(
                [
                    MessageContextSnapshot(
                        message=user_message,
                        source_note=n,
                        original_note_id=n.pk,
                        title=n.title,
                        body=n.body,
                    )
                    for n in notes
                ]
            )
            assistant_message = Message.objects.create(
                chat=chat,
                role=Message.Role.ASSISTANT,
                content=reply.content,
                mode=reply.mode,
                language=request.LANGUAGE_CODE,
                client_request_id=request_id,
            )
            if first_message:
                chat.title = " ".join(content.split())[:70]
            chat.save(update_fields=["title", "updated_at"])
            return _turn_response(chat, user_message, assistant_message, 201)
    except IntegrityError:
        chat = Chat.objects.filter(pk=pk, owner=request.user).first()
        if chat:
            previous = _existing_turn(chat, request_id, content, note_ids)
            if previous is not None:
                return previous
        return _error(
            "conflict", _("This conversation changed. Refresh the page and try again."), 409
        )
    except OperationalError:
        return _error(
            "temporarily_unavailable",
            _("Your message could not be saved right now. Please try again."),
            503,
        )


@require_GET
def turn_status(request, pk, request_id):
    if not request.user.is_authenticated:
        return _error(
            "authentication_required", _("Please log in again to send your message."), 401
        )
    chat = Chat.objects.filter(pk=pk, owner=request.user).first()
    if chat is None:
        return turns.error_response(ChatError("not_found", 404))
    turns.expire(chat)
    turn = chat.turns.filter(client_request_id=request_id).first()
    if turn is None:
        return turns.error_response(ChatError("not_found", 404))
    return turns.result(chat, turn)


@require_POST
def update_context(request, pk):
    if not request.user.is_authenticated:
        return _error(
            "authentication_required", _("Please log in again to send your message."), 401
        )
    try:
        payload = json.loads(request.body)
        with transaction.atomic():
            chat = Chat.objects.select_for_update().filter(pk=pk, owner=request.user).first()
            if chat is None:
                raise ChatError("not_found", 404)
            history_reset = context.update(chat, payload)
            return JsonResponse(
                {
                    "status": "updated",
                    "active_context": context.public_context(chat),
                    "history_reset": history_reset,
                }
            )
    except RequestDataTooBig, ValueError, TypeError:
        return turns.error_response(ChatError("invalid_context", 400))
    except ChatError as error:
        return turns.error_response(error)
    except IntegrityError, OperationalError:
        return turns.error_response(ChatError("chat_busy", 409))
