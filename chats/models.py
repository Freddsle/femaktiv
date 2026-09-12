import uuid

from django.conf import settings
from django.db import models


class Chat(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="chats"
    )
    title = models.CharField(max_length=120)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

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
