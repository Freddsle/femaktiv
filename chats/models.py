import uuid

from django.conf import settings
from django.db import models
from django.utils import timezone


class Chat(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="chats"
    )
    title = models.CharField(max_length=120)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    context_version = models.PositiveIntegerField(default=0)
    context_started_at = models.DateTimeField(null=True, blank=True)
    locality = models.CharField(max_length=80, blank=True)

    class Meta:
        ordering = ["-updated_at"]


class Message(models.Model):
    class Role(models.TextChoices):
        USER = "user"
        ASSISTANT = "assistant"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    chat = models.ForeignKey(Chat, on_delete=models.CASCADE, related_name="messages")
    role = models.CharField(max_length=12, choices=Role.choices)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    mode = models.CharField(max_length=20, blank=True)
    language = models.CharField(max_length=2, choices=settings.LANGUAGES)
    client_request_id = models.UUIDField()
    context_version = models.PositiveIntegerField(default=0)
    kind = models.CharField(max_length=20, default="answer")
    paragraphs = models.JSONField(default=list, blank=True)
    citations = models.JSONField(default=list, blank=True)
    urgent_help = models.JSONField(default=dict, blank=True)
    lookup_status = models.CharField(max_length=24, default="not_requested")

    class Meta:
        ordering = ["created_at", "id"]
        constraints = [
            models.UniqueConstraint(
                fields=["chat", "client_request_id", "role"], name="unique_chat_turn_role"
            ),
        ]


class MessageContextSnapshot(models.Model):
    message = models.ForeignKey(Message, on_delete=models.CASCADE, related_name="context_snapshots")
    source_note = models.ForeignKey(
        "notes.PersonalNote", on_delete=models.SET_NULL, null=True, blank=True
    )
    original_note_id = models.UUIDField()
    title = models.CharField(max_length=120)
    body = models.TextField()

    class Meta:
        ordering = ["id"]
        constraints = [
            models.UniqueConstraint(
                fields=["message", "original_note_id"], name="unique_message_note_snapshot"
            ),
        ]


class ActiveNote(models.Model):
    """An explicitly attached copy, independent of subsequent source-note edits."""

    chat = models.ForeignKey(Chat, on_delete=models.CASCADE, related_name="active_notes")
    source_note = models.ForeignKey(
        "notes.PersonalNote", on_delete=models.SET_NULL, null=True, blank=True
    )
    original_note_id = models.UUIDField()
    title = models.CharField(max_length=120)
    body = models.TextField()
    attached_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["attached_at", "id"]
        constraints = [
            models.UniqueConstraint(
                fields=["chat", "original_note_id"], name="unique_active_chat_note"
            )
        ]


class LiveUsageGate(models.Model):
    """One database row serializes quota admission across all application workers."""

    id = models.PositiveSmallIntegerField(primary_key=True, default=1, editable=False)
    revision = models.PositiveBigIntegerField(default=0)


class LiveUsage(models.Model):
    """Content-free paid reservation accounting; chat deletion never removes it."""

    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(default=timezone.now, db_index=True)
    expires_at = models.DateTimeField()
    finished_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        indexes = [models.Index(fields=["owner", "created_at"])]


class ChatTurn(models.Model):
    class Status(models.TextChoices):
        PROCESSING = "processing"
        COMPLETED = "completed"
        FAILED = "failed"

    chat = models.ForeignKey(Chat, on_delete=models.CASCADE, related_name="turns")
    usage = models.OneToOneField(LiveUsage, on_delete=models.SET_NULL, null=True, editable=False)
    client_request_id = models.UUIDField()
    fingerprint = models.CharField(max_length=64)
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.PROCESSING)
    content = models.TextField(blank=True)
    note_copies = models.JSONField(default=list, blank=True)
    context_version = models.PositiveIntegerField()
    language = models.CharField(max_length=2, choices=settings.LANGUAGES)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    error_code = models.CharField(max_length=40, blank=True)
    error_status = models.PositiveSmallIntegerField(default=502)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["chat", "client_request_id"], name="unique_chat_reservation"
            ),
            models.UniqueConstraint(
                fields=["chat"],
                condition=models.Q(status="processing"),
                name="one_processing_turn_per_chat",
            ),
        ]
