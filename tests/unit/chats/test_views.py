import json
from unittest.mock import patch
from uuid import uuid4

from django.contrib.auth import get_user_model
from django.db import OperationalError
from django.test import Client, TestCase

from chats.models import Chat, Message, MessageContextSnapshot
from notes.models import PersonalNote


class ChatTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.owner = get_user_model().objects.create_user(
            email="owner@example.test", password="a-long-random-pass-352!", display_name="Owner"
        )
        cls.other = get_user_model().objects.create_user(
            email="other@example.test", password="another-long-pass-489!", display_name="Other"
        )
        cls.chat = Chat.objects.create(owner=cls.owner, title="A private conversation")
        cls.note = PersonalNote.objects.create(
            owner=cls.owner, title="My preferences", body="I prefer warm lunches."
        )
        cls.foreign_note = PersonalNote.objects.create(
            owner=cls.other, title="Private", body="Not shared"
        )

    def setUp(self):
        self.client.force_login(self.owner)
        self.url = f"/en/api/chats/{self.chat.pk}/messages/"

    def payload(self, **overrides):
        return {
            "content": "Help me organise my week.",
            "note_ids": [str(self.note.pk)],
            "client_request_id": str(uuid4()),
            **overrides,
        }

    def send(self, payload=None, **kwargs):
        return self.client.post(
            self.url,
            json.dumps(payload or self.payload()),
            content_type="application/json",
            **kwargs,
        )

    def test_turn_persists_and_is_honestly_labelled(self):
        with patch(
            "socket.socket.connect", side_effect=AssertionError("Unexpected network request")
        ):
            response = self.send()
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()["mode"], "placeholder")
        self.assertEqual(
            response.json()["user_message"]["context"],
            [{"title": self.note.title, "body": self.note.body}],
        )
        self.assertIn("not connected", response.json()["assistant_message"]["content"])
        self.assertEqual(Message.objects.filter(chat=self.chat).count(), 2)
        self.client.logout()
        self.client.force_login(self.owner)
        self.assertEqual(Message.objects.filter(chat=self.chat).count(), 2)

    def test_duplicate_request_returns_original_turn(self):
        payload = self.payload()
        first = self.send(payload)
        second = self.send(payload)
        self.assertEqual(first.status_code, 201)
        self.assertEqual(second.status_code, 200)
        self.assertEqual(first.json(), second.json())
        self.assertEqual(Message.objects.count(), 2)
        self.assertEqual(MessageContextSnapshot.objects.count(), 1)

    def test_reused_request_id_with_changed_text_is_rejected(self):
        payload = self.payload()
        self.send(payload)
        response = self.send({**payload, "content": "Different request"})
        self.assertEqual(response.status_code, 409)
        self.assertEqual(Message.objects.count(), 2)

    def test_snapshots_survive_note_edit_and_delete(self):
        payload = self.payload()
        self.send(payload)
        self.note.body = "Changed later"
        self.note.save()
        self.assertEqual(MessageContextSnapshot.objects.get().body, "I prefer warm lunches.")
        self.note.delete()
        snapshot = MessageContextSnapshot.objects.get()
        self.assertIsNone(snapshot.source_note_id)
        self.assertEqual(snapshot.body, "I prefer warm lunches.")
        self.assertEqual(self.send(payload).status_code, 200)

    def test_only_selected_notes_are_attached(self):
        response = self.send(self.payload(note_ids=[]))
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()["user_message"]["context"], [])
        self.assertEqual(MessageContextSnapshot.objects.count(), 0)

    def test_foreign_or_missing_notes_abort_entire_turn(self):
        for note_id in (self.foreign_note.pk, uuid4()):
            with self.subTest(note_id=note_id):
                response = self.send(self.payload(note_ids=[str(self.note.pk), str(note_id)]))
                self.assertEqual(response.status_code, 404)
                self.assertEqual(Message.objects.count(), 0)
                self.assertEqual(MessageContextSnapshot.objects.count(), 0)

    def test_chat_owner_is_checked_for_every_private_operation(self):
        self.client.force_login(self.other)
        for suffix in ("", "delete/"):
            self.assertEqual(self.client.get(f"/en/chats/{self.chat.pk}/{suffix}").status_code, 404)
        for suffix, data in (("rename/", {"title": "Changed"}), ("delete/", {})):
            self.assertEqual(
                self.client.post(f"/en/chats/{self.chat.pk}/{suffix}", data).status_code, 404
            )
        self.assertEqual(self.send().status_code, 404)
        self.assertEqual(Message.objects.count(), 0)

    def test_staff_has_no_private_chat_bypass(self):
        self.other.is_staff = True
        self.other.is_superuser = True
        self.other.save()
        self.client.force_login(self.other)
        self.assertEqual(self.send().status_code, 404)

    def test_unauthenticated_api_returns_json(self):
        self.client.logout()
        response = self.send()
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json()["error"]["code"], "authentication_required")

    def test_invalid_contracts_are_rejected_without_partial_data(self):
        base = self.payload()
        invalid = [
            {},
            {**base, "owner": self.other.pk},
            {**base, "content": " "},
            {**base, "content": "x" * 4001},
            {**base, "content": 5},
            {**base, "note_ids": "all"},
            {**base, "note_ids": [str(self.note.pk)] * 2},
            {**base, "note_ids": [str(uuid4()) for _ in range(6)]},
            {**base, "client_request_id": "bad-id"},
            {**base, "note_ids": [2]},
        ]
        for payload in invalid:
            with self.subTest(payload=payload):
                response = self.client.post(
                    self.url, json.dumps(payload), content_type="application/json"
                )
                self.assertEqual(response.status_code, 400)
        self.assertEqual(Message.objects.count(), 0)

    def test_oversized_body_and_invalid_json(self):
        self.assertEqual(
            self.client.post(self.url, "x" * 70000, content_type="application/json").status_code,
            413,
        )
        self.assertEqual(
            self.client.post(self.url, "{", content_type="application/json").status_code, 400
        )

    def test_csrf_is_required(self):
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.owner)
        response = client.post(
            self.url, json.dumps(self.payload()), content_type="application/json"
        )
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()["error"]["code"], "csrf_failed")
        self.assertEqual(Message.objects.count(), 0)

    def test_database_failure_rolls_back_turn(self):
        with patch(
            "chats.views.MessageContextSnapshot.objects.bulk_create",
            side_effect=OperationalError("busy"),
        ):
            response = self.send()
        self.assertEqual(response.status_code, 503)
        self.assertEqual(Message.objects.count(), 0)

    def test_language_comes_from_url_and_old_messages_are_preserved(self):
        english = self.send().json()["assistant_message"]["content"]
        self.url = f"/de/api/chats/{self.chat.pk}/messages/"
        german = self.send().json()["assistant_message"]["content"]
        self.assertNotEqual(english, german)
        self.assertEqual(
            Message.objects.filter(role="assistant", language="en").get().content, english
        )
        self.assertEqual(
            Message.objects.filter(role="assistant", language="de").get().content, german
        )

    def test_delete_chat_removes_snapshots_but_keeps_source_note(self):
        self.send()
        response = self.client.post(f"/en/chats/{self.chat.pk}/delete/")
        self.assertEqual(response.status_code, 302)
        self.assertEqual(Message.objects.count(), 0)
        self.assertEqual(MessageContextSnapshot.objects.count(), 0)
        self.assertTrue(PersonalNote.objects.filter(pk=self.note.pk).exists())

    def test_private_response_cannot_be_shared_cached(self):
        response = self.send()
        self.assertIn("private", response.headers["Cache-Control"])
        self.assertIn("no-store", response.headers["Cache-Control"])
