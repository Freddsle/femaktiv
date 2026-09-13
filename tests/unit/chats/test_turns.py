import json
from datetime import timedelta
from unittest.mock import patch
from uuid import uuid4

from django.contrib.auth import get_user_model
from django.db import OperationalError, connection
from django.test import Client, TransactionTestCase, override_settings
from django.utils import timezone

from chats import turns, usage
from chats.errors import ChatError
from chats.models import ActiveNote, Chat, ChatTurn, Message
from chats.service import ChatReply, ContextNote
from notes.models import PersonalNote

from .fixtures import LIVE_SETTINGS, answer, intake


@override_settings(**LIVE_SETTINGS)
class LiveTurnTests(TransactionTestCase):
    def setUp(self):
        self.owner = get_user_model().objects.create_user(
            email="owner@example.test",
            password="test-pass-419!",
            display_name="Never send this identity",
            live_chat_enabled=True,
        )
        self.other = get_user_model().objects.create_user(
            email="other@example.test", password="test-pass-419!", display_name="Other"
        )
        self.chat = Chat.objects.create(owner=self.owner, title="Private title")
        self.note = PersonalNote.objects.create(
            owner=self.owner,
            title="Food restrictions",
            body="Milk allergy, hypertension, fifteen minutes.",
        )
        self.unrelated = PersonalNote.objects.create(
            owner=self.owner, title="Unrelated", body="Unrelated private secret"
        )
        self.client.force_login(self.owner)
        self.url = f"/en/api/chats/{self.chat.pk}/messages/"
        self.provider = patch(
            "chats.provider.complete",
            side_effect=lambda **kw: (
                intake() if kw["name"] == "femaktiv_intake" else answer(kw["language"])
            ),
        )
        self.mock = self.provider.start()
        self.addCleanup(self.provider.stop)

    def payload(self, **changes):
        return {
            "content": "Help with lunch",
            "note_ids": [str(self.note.pk)],
            "client_request_id": str(uuid4()),
            **changes,
        }

    def send(self, payload=None):
        return self.client.post(
            self.url, data=json.dumps(payload or self.payload()), content_type="application/json"
        )

    def context(self, **data):
        return self.client.post(
            f"/en/api/chats/{self.chat.pk}/context/",
            json.dumps(data),
            content_type="application/json",
        )

    def status(self, request_id):
        return self.client.get(f"/en/api/chats/{self.chat.pk}/turns/{request_id}/")

    def test_multiple_turns_both_languages_keep_constraints_and_citations(self):
        for language in ("en", "de"):
            with self.subTest(language=language):
                self.url = f"/{language}/api/chats/{self.chat.pk}/messages/"
                first = self.send()
                self.assertEqual(first.status_code, 201)
                followup = self.send(self.payload(content="Another idea please", note_ids=[]))
                self.assertEqual(followup.status_code, 201)
                result = followup.json()
                self.assertEqual(result["mode"], "live")
                self.assertEqual(
                    result["assistant_message"]["citations"][0]["url"],
                    "https://www.dge.de/gesunde-ernaehrung/gut-essen-und-trinken/dge-empfehlungen/",
                )
                self.assertEqual(result["user_message"]["context"][0]["body"], self.note.body)
                raw = self.mock.call_args.kwargs["messages"][1]["content"]
                self.assertIn("Milk allergy", raw)
                self.assertNotIn(self.owner.email, raw)
                self.assertNotIn(self.owner.display_name, raw)
                self.assertNotIn(self.unrelated.body, raw)
                self.assertNotIn(self.chat.title, raw)
                self.assertIn("private", followup.headers["Cache-Control"])
                self.assertIn(
                    "no-store", self.status(result["client_request_id"]).headers["Cache-Control"]
                )

    def test_network_runs_outside_transaction_and_duplicates_reuse_reservation(self):
        payload = self.payload()

        def generate(**kwargs):
            self.assertFalse(connection.in_atomic_block)
            self.assertEqual(ChatTurn.objects.get().status, "processing")
            self.assertEqual(self.send(payload).status_code, 202)
            self.assertEqual(self.status(payload["client_request_id"]).status_code, 202)
            self.assertEqual(self.send(self.payload()).status_code, 409)
            return ChatReply("Ready", "live")

        with patch("chats.turns.service.generate_reply", side_effect=generate) as call:
            result = self.send(payload)
            self.assertEqual(result.status_code, 201)
            self.assertEqual(self.send(payload).json(), result.json())
            self.assertEqual(self.status(payload["client_request_id"]).json(), result.json())
            self.assertEqual(call.call_count, 1)
        self.assertEqual(Message.objects.count(), 2)
        reservation = ChatTurn.objects.get()
        self.assertEqual(reservation.content, "")
        self.assertEqual(reservation.note_copies, [])
        self.assertEqual(self.send({**payload, "content": "changed"}).status_code, 409)

    def test_urgent_panel_is_saved_and_recovered_without_reclassification(self):
        self.mock.side_effect = lambda **kwargs: intake(decision="urgent")
        payload = self.payload(content="My mum fell and hurt her skull.", note_ids=[])
        response = self.send(payload)
        self.assertEqual(response.status_code, 201)
        original = response.json()
        saved = Message.objects.get(role=Message.Role.ASSISTANT)
        self.assertEqual(saved.urgent_help, original["assistant_message"]["urgent_help"])
        self.assertEqual(saved.urgent_help["heading"], "If you are in Germany")
        self.assertEqual(original["user_message"]["urgent_help"], {})
        self.assertEqual(self.send(payload).json(), original)
        self.assertEqual(self.status(payload["client_request_id"]).json(), original)
        page = self.client.get(f"/de/chats/{self.chat.pk}/")
        self.assertContains(page, "If you are in Germany")
        self.assertContains(page, 'href="tel:112"')
        self.assertEqual(self.mock.call_count, 1)
        self.client.force_login(self.other)
        self.assertEqual(self.status(payload["client_request_id"]).status_code, 404)
        self.assertEqual(self.client.get(f"/en/chats/{self.chat.pk}/").status_code, 404)

    def test_followup_saves_mothers_information_in_owned_notes_in_both_languages(self):
        for language, report, request, title, body, confirmation in (
            (
                "en",
                "My mum fell and hurt her skull, does she need to go to the hospital?",
                "Please save this info in my notes, its about my mother.",
                "Mother — fall",
                "My mother fell and hurt her skull. I asked whether she needs hospital assessment.",
                "Your note has been saved.",
            ),
            (
                "de",
                "Meine Mutter ist gestürzt und hat sich am Kopf verletzt. Muss sie ins Krankenhaus?",
                "Bitte speichere das in meinen Notizen. Es geht um meine Mutter.",
                "Mutter — Sturz",
                "Meine Mutter ist gestürzt und hat sich am Kopf verletzt. Ich habe gefragt, ob sie ins Krankenhaus muss.",
                "Deine Notiz wurde gespeichert.",
            ),
        ):
            with self.subTest(language=language):
                self.chat = Chat.objects.create(owner=self.owner)
                self.url = f"/{language}/api/chats/{self.chat.pk}/messages/"
                self.mock.reset_mock()
                self.mock.side_effect = [
                    intake(decision="urgent", topic="care", facts=[report]),
                    intake(
                        decision="save_note",
                        topic="care",
                        facts=[report],
                        evidence_topics=[],
                        note_action={"action": "create", "title": title, "body": body},
                    ),
                ]
                original_count = PersonalNote.objects.count()
                first = self.send(self.payload(content=report, note_ids=[]))
                self.assertEqual(first.status_code, 201)
                self.assertIsNone(first.json()["assistant_message"]["saved_note"])
                self.assertEqual(PersonalNote.objects.count(), original_count)

                response = self.send(self.payload(content=request, note_ids=[]))
                self.assertEqual(response.status_code, 201)
                data = response.json()
                note = PersonalNote.objects.get(owner=self.owner, title=title)
                self.assertEqual(PersonalNote.objects.count(), original_count + 1)
                self.assertEqual(note.body, body)
                self.assertEqual(data["assistant_message"]["content"], confirmation)
                self.assertEqual(
                    data["assistant_message"]["saved_note"],
                    {
                        "id": str(note.pk),
                        "title": title,
                        "url": f"/{language}/notes/{note.pk}/edit/",
                    },
                )
                self.assertIsNone(data["user_message"]["saved_note"])
                self.assertEqual(data["active_context"]["notes"], [])
                self.assertFalse(ActiveNote.objects.filter(chat=self.chat).exists())
                self.assertEqual(self.mock.call_count, 2)
                model_context = json.loads(self.mock.call_args.kwargs["messages"][1]["content"])
                self.assertEqual(
                    [
                        entry["content"]
                        for entry in model_context["conversation"]
                        if entry["role"] == "user"
                    ],
                    [report, request],
                )
                self.assertContains(self.client.get(f"/{language}/notes/"), title)
                self.assertContains(self.client.get(f"/{language}/notes/{note.pk}/edit/"), body)
                self.assertContains(
                    self.client.get(f"/{language}/chats/{self.chat.pk}/"),
                    f'href="/{language}/notes/{note.pk}/edit/"',
                )

    def test_saved_note_retries_status_and_deletion_do_not_recreate_it(self):
        self.mock.side_effect = lambda **kwargs: intake(
            decision="save_note",
            note_action={
                "action": "create",
                "title": "Mother — fall",
                "body": "My mother fell and hurt her skull.",
            },
        )
        payload = self.payload(
            content="Save a note: my mother fell and hurt her skull.", note_ids=[]
        )
        initial_count = PersonalNote.objects.count()
        response = self.send(payload)
        self.assertEqual(response.status_code, 201)
        original = response.json()
        for recovered in (self.send(payload), self.status(payload["client_request_id"])):
            self.assertEqual(recovered.json(), original)
        self.assertEqual(PersonalNote.objects.count(), initial_count + 1)
        self.assertEqual(Message.objects.count(), 2)
        self.assertEqual(self.mock.call_count, 1)
        saved_message = Message.objects.get(role=Message.Role.ASSISTANT)
        note = saved_message.saved_note
        self.assertEqual(str(note.pk), original["assistant_message"]["saved_note"]["id"])

        self.other.is_staff = self.other.is_superuser = True
        self.other.save()
        self.client.force_login(self.other)
        self.assertEqual(self.send(payload).status_code, 404)
        self.assertEqual(self.status(payload["client_request_id"]).status_code, 404)
        self.assertEqual(self.client.get(f"/en/notes/{note.pk}/edit/").status_code, 404)
        self.assertNotContains(self.client.get("/en/notes/"), note.title)
        self.assertFalse(PersonalNote.objects.filter(owner=self.other).exists())

        self.client.force_login(self.owner)
        self.assertEqual(self.client.post(f"/en/notes/{note.pk}/delete/").status_code, 302)
        saved_message.refresh_from_db()
        self.assertIsNone(saved_message.saved_note_id)
        for recovered in (self.send(payload), self.status(payload["client_request_id"])):
            self.assertIsNone(recovered.json()["assistant_message"]["saved_note"])
        self.assertNotContains(
            self.client.get(f"/en/chats/{self.chat.pk}/"),
            f'href="/en/notes/{note.pk}/edit/"',
        )
        self.assertEqual(PersonalNote.objects.count(), initial_count)
        self.assertEqual(self.mock.call_count, 1)

    def test_note_write_failure_rolls_back_messages_and_never_confirms_saved(self):
        self.mock.side_effect = lambda **kwargs: intake(
            decision="save_note",
            note_action={"action": "create", "title": "Mother", "body": "My mother fell."},
        )
        payload = self.payload(content="Save a note about my mother's fall.", note_ids=[])
        initial_count = PersonalNote.objects.count()
        with patch.object(
            PersonalNote, "save", side_effect=OperationalError("private note content")
        ):
            response = self.send(payload)
        self.assertEqual(response.status_code, 503)
        self.assertNotIn("private note content", response.content.decode())
        self.assertNotIn("Your note has been saved", response.content.decode())
        self.assertFalse(Message.objects.exists())
        self.assertEqual(PersonalNote.objects.count(), initial_count)
        self.assertEqual(ChatTurn.objects.get().status, "failed")
        self.assertEqual(self.send(payload).json(), response.json())
        self.assertEqual(self.mock.call_count, 1)

    def test_deleting_completed_chat_preserves_its_saved_personal_note(self):
        self.mock.side_effect = lambda **kwargs: intake(
            decision="save_note",
            note_action={"action": "create", "title": "Mother", "body": "My mother fell."},
        )
        response = self.send(self.payload(content="Save a note: my mother fell.", note_ids=[]))
        self.assertEqual(response.status_code, 201)
        note_id = response.json()["assistant_message"]["saved_note"]["id"]
        self.assertEqual(self.client.post(f"/en/chats/{self.chat.pk}/delete/").status_code, 302)
        self.assertFalse(Message.objects.exists())
        self.assertFalse(ChatTurn.objects.exists())
        self.assertEqual(PersonalNote.objects.get(pk=note_id).owner_id, self.owner.pk)
        self.assertContains(self.client.get(f"/en/notes/{note_id}/edit/"), "My mother fell.")

    def test_later_turn_write_failure_rolls_back_created_note_and_messages(self):
        original_save = ChatTurn.save

        def fail_completion(turn, *args, **kwargs):
            if turn.status == ChatTurn.Status.COMPLETED:
                raise OperationalError("private note content")
            return original_save(turn, *args, **kwargs)

        initial_count = PersonalNote.objects.count()
        with (
            patch(
                "chats.turns.service.generate_reply",
                return_value=ChatReply(
                    "",
                    "live",
                    note_to_save=ContextNote("Mother", "My mother fell."),
                ),
            ),
            patch.object(ChatTurn, "save", fail_completion),
        ):
            response = self.send(self.payload(note_ids=[]))
        self.assertEqual(response.status_code, 503)
        self.assertFalse(Message.objects.exists())
        self.assertEqual(PersonalNote.objects.count(), initial_count)
        self.assertEqual(ChatTurn.objects.get().status, "failed")

    def test_late_note_save_cannot_outlive_reset_or_private_data_deletion(self):
        for action in ("reset", "delete", "delete_all"):
            with self.subTest(action=action):
                self.chat = Chat.objects.create(owner=self.owner)
                _, turn, _ = turns.reserve(
                    owner=self.owner,
                    pk=self.chat.pk,
                    request_id=uuid4(),
                    content="Save a note about my mother.",
                    note_ids=[],
                    language="en",
                )
                chat_id = self.chat.pk
                initial_count = PersonalNote.objects.count()
                reply = ChatReply(
                    "",
                    "live",
                    note_to_save=ContextNote("Mother", "My mother fell."),
                )
                if action == "reset":
                    self.assertEqual(self.context(action="reset").status_code, 200)
                    response = turns.save_reply(chat_id, turn.pk, reply)
                    self.assertEqual(response.status_code, 409)
                else:
                    if action == "delete_all":
                        self.assertEqual(
                            self.client.post(
                                "/en/accounts/settings/delete-data/", {"confirm": "on"}
                            ).status_code,
                            302,
                        )
                        initial_count = 0
                    else:
                        self.chat.delete()
                    with self.assertRaises(ChatError) as caught:
                        turns.save_reply(chat_id, turn.pk, reply)
                    self.assertEqual(caught.exception.code, "not_found")
                self.assertEqual(PersonalNote.objects.count(), initial_count)
                self.assertFalse(Message.objects.exists())
                usage.finish(turn.usage_id)
        self.mock.assert_not_called()

    def test_failed_paid_request_is_terminal_and_duplicate_never_retries(self):
        for code in ("privacy_failed", "invalid_reply", "deadline_exceeded"):
            payload = self.payload()
            with patch(
                "chats.turns.service.generate_reply", side_effect=ChatError(code)
            ) as generate:
                result = self.send(payload)
                self.assertEqual(result.json()["error"]["code"], code)
                self.assertTrue(result.json()["error"]["terminal"])
                self.assertEqual(self.send(payload).json(), result.json())
                self.assertEqual(generate.call_count, 1)
        self.assertEqual(Message.objects.count(), 0)
        self.assertFalse(ChatTurn.objects.exclude(content="").exists())
        self.assertFalse(ChatTurn.objects.exclude(note_copies=[]).exists())

    def test_expired_reservation_cannot_restart_or_save(self):
        payload = self.payload()
        _, turn, _ = turns.reserve(
            owner=self.owner,
            pk=self.chat.pk,
            request_id=payload["client_request_id"],
            content=payload["content"],
            note_ids=[self.note.pk],
            language="en",
        )
        ChatTurn.objects.filter(pk=turn.pk).update(expires_at=timezone.now() - timedelta(seconds=1))
        self.assertEqual(self.status(payload["client_request_id"]).status_code, 504)
        self.assertEqual(self.send(payload).status_code, 504)
        initial_note_count = PersonalNote.objects.count()
        self.assertEqual(
            turns.save_reply(
                self.chat.pk,
                turn.pk,
                ChatReply(
                    "Late",
                    "live",
                    note_to_save=ContextNote("Mother", "My mother fell."),
                ),
            ).status_code,
            504,
        )
        self.mock.assert_not_called()
        self.assertFalse(Message.objects.exists())
        self.assertEqual(PersonalNote.objects.count(), initial_note_count)

    def test_pair_rolls_back_on_save_failure_but_reservation_remains_failed(self):
        with patch(
            "chats.turns.MessageContextSnapshot.objects.bulk_create",
            side_effect=OperationalError("private data must never be echoed"),
        ):
            result = self.send()
        self.assertEqual(result.status_code, 503)
        self.assertNotIn("private data must", result.content.decode())
        self.assertFalse(Message.objects.exists())
        self.assertEqual(ChatTurn.objects.get().status, "failed")

    def test_delete_during_inference_does_not_resurrect_chat(self):
        def generate(**kwargs):
            self.client.post(f"/en/chats/{self.chat.pk}/delete/")
            return ChatReply("Late", "live")

        with patch("chats.turns.service.generate_reply", side_effect=generate):
            self.assertEqual(self.send().status_code, 404)
        self.assertFalse(Chat.objects.exists())
        self.assertFalse(ChatTurn.objects.exists())
        self.assertFalse(Message.objects.exists())

    def test_context_change_discards_in_progress_reply(self):
        def generate(**kwargs):
            self.assertEqual(
                self.context(action="remove", note_id=str(self.note.pk)).status_code, 200
            )
            return ChatReply("Reply derived from removed note", "live")

        with patch("chats.turns.service.generate_reply", side_effect=generate):
            response = self.send()
        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.json()["error"]["code"], "context_changed")
        self.assertFalse(Message.objects.exists())
        self.assertFalse(ActiveNote.objects.exists())

    def test_removal_during_intake_stops_later_external_stages(self):
        def model(**kwargs):
            self.assertEqual(kwargs["name"], "femaktiv_intake")
            self.context(action="remove", note_id=str(self.note.pk))
            return intake(topic="care")

        self.mock.side_effect = model
        response = self.send()
        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.json()["error"]["code"], "context_changed")
        self.assertEqual(self.mock.call_count, 1)
        self.assertFalse(Message.objects.exists())

    def test_reset_during_intake_discards_reply_and_keeps_active_note_copies(self):
        def model(**kwargs):
            self.assertEqual(kwargs["name"], "femaktiv_intake")
            self.assertEqual(self.context(action="reset").status_code, 200)
            return intake()

        self.mock.side_effect = model
        response = self.send()
        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.json()["error"]["code"], "context_changed")
        self.assertEqual(self.mock.call_count, 1)
        self.assertFalse(Message.objects.exists())
        self.assertEqual(ActiveNote.objects.get().body, self.note.body)

    def test_deletion_during_intake_stops_answer_composition(self):
        def model(**kwargs):
            self.assertEqual(kwargs["name"], "femaktiv_intake")
            self.chat.delete()
            return intake(topic="care")

        self.mock.side_effect = model
        response = self.send()
        self.assertEqual(response.status_code, 404)
        self.assertEqual(self.mock.call_count, 1)
        self.assertFalse(Message.objects.exists())

    def test_copies_survive_source_changes_but_refresh_removes_old_derived_context(self):
        self.send()
        old_body = self.note.body
        self.note.body = "New declared preference"
        self.note.save()
        self.send(self.payload(note_ids=[]))
        self.assertEqual(ActiveNote.objects.get().body, old_body)
        self.assertEqual(self.context(action="refresh", note_id=str(self.note.pk)).status_code, 200)
        self.send(self.payload(content="Use refreshed note", note_ids=[]))
        raw = self.mock.call_args.kwargs["messages"][1]["content"]
        self.assertNotIn(old_body, raw)
        self.assertNotIn("Another idea", raw)
        self.assertIn(self.note.body, raw)
        self.assertEqual(Message.objects.count(), 6)
        self.note.delete()
        self.send(self.payload(content="Continue", note_ids=[]))
        self.assertEqual(ActiveNote.objects.get().body, "New declared preference")
        self.assertIsNone(ActiveNote.objects.get().source_note_id)

    def test_remove_excludes_raw_and_derived_history_from_next_request(self):
        self.send()
        self.assertEqual(self.context(action="remove", note_id=str(self.note.pk)).status_code, 200)
        self.send(self.payload(content="Start fresh", note_ids=[]))
        intake_call = self.mock.call_args_list[-2].kwargs["messages"][1]["content"]
        self.assertNotIn("Milk allergy", intake_call)
        self.assertNotIn("lentil", intake_call)
        self.assertNotIn("Help with lunch", intake_call)
        self.assertEqual(Message.objects.count(), 4)
        self.assertContains(self.client.get(f"/en/chats/{self.chat.pk}/"), "Milk allergy")

    def test_historical_placeholder_messages_never_enter_first_live_context(self):
        with override_settings(FEMAKTIV_AI_MODE="placeholder"):
            self.send(self.payload(content="Old private history", note_ids=[]))
        self.send(self.payload(content="New live start", note_ids=[]))
        raw = self.mock.call_args.kwargs["messages"][1]["content"]
        self.assertNotIn("Old private history", raw)
        self.assertEqual(Message.objects.filter(mode="placeholder").count(), 1)

    def test_reset_excludes_old_messages_from_future_inference(self):
        self.send(
            self.payload(content="Mother needs support after hospital discharge", note_ids=[])
        )
        reset = self.context(action="reset")
        self.assertTrue(reset.json()["history_reset"])
        self.send(self.payload(content="New request", note_ids=[]))
        self.assertNotIn(
            "Mother needs support", self.mock.call_args_list[-2].kwargs["messages"][1]["content"]
        )
        self.assertEqual(Message.objects.count(), 4)

    def test_retired_locality_action_is_rejected_and_legacy_value_is_not_sent(self):
        self.chat.locality = "Berlin"
        self.chat.save(update_fields=["locality"])
        response = self.context(action="locality", locality="Hamburg")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["error"]["code"], "invalid_context")
        result = self.send(self.payload(note_ids=[]))
        self.assertEqual(result.status_code, 201)
        self.assertNotIn("locality", result.json()["active_context"])
        for call in self.mock.call_args_list:
            self.assertNotIn("Berlin", call.kwargs["messages"][1]["content"])
        self.chat.refresh_from_db()
        self.assertEqual(self.chat.locality, "Berlin")

    def test_error_keeps_active_copies_visible_for_removal(self):
        with patch("chats.turns.service.generate_reply", side_effect=ChatError("privacy_failed")):
            response = self.send()
        self.assertEqual(response.json()["active_context"]["notes"][0]["id"], str(self.note.pk))

    def test_context_is_isolated_between_chats_and_large_history_is_not_truncated(self):
        self.send()
        other_chat = Chat.objects.create(owner=self.owner, title="Other")
        self.url = f"/en/api/chats/{other_chat.pk}/messages/"
        result = self.send(self.payload(note_ids=[]))
        self.assertEqual(result.json()["active_context"]["notes"], [])
        other_chat.refresh_from_db()
        Message.objects.create(
            chat=other_chat,
            role="user",
            content="x" * 60000,
            mode="live",
            context_version=other_chat.context_version,
            language="en",
            client_request_id=uuid4(),
        )
        count = self.mock.call_count
        result = self.send(self.payload(note_ids=[]))
        self.assertEqual(result.status_code, 413)
        self.assertEqual(self.mock.call_count, count)

    def test_new_private_endpoints_enforce_owner_staff_csrf_and_authentication(self):
        payload = self.payload()
        self.send(payload)
        self.other.is_staff = self.other.is_superuser = True
        self.other.save()
        self.client.force_login(self.other)
        self.assertEqual(self.status(payload["client_request_id"]).status_code, 404)
        self.assertEqual(self.context(action="reset").status_code, 404)
        self.assertEqual(self.send().status_code, 404)
        self.client.logout()
        self.assertEqual(self.status(payload["client_request_id"]).status_code, 401)
        self.assertEqual(self.context(action="reset").status_code, 401)
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.owner)
        self.assertEqual(
            client.post(
                f"/en/api/chats/{self.chat.pk}/context/",
                json.dumps({"action": "reset"}),
                content_type="application/json",
            ).status_code,
            403,
        )

    @override_settings(ANYMIZE_ZDR_CONFIRMED=False)
    def test_live_configuration_failure_never_substitutes_placeholder(self):
        self.assertEqual(self.send().status_code, 503)
        self.mock.assert_not_called()
        self.assertFalse(Message.objects.exists())
        self.assertFalse(ChatTurn.objects.exists())
