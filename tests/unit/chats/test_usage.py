from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
from datetime import timezone as dt_timezone
from importlib import import_module
from threading import Barrier
from unittest.mock import patch
from uuid import uuid4

from django.apps import apps
from django.db import close_old_connections, connection
from django.test import Client, TransactionTestCase, override_settings
from django.utils import timezone

from accounts.models import User
from chats import turns, usage
from chats.errors import ChatError
from chats.models import Chat, ChatTurn, LiveUsage, LiveUsageGate, Message
from chats.service import ChatReply
from notes.models import PersonalNote
from tests.unit.chats.fixtures import LIVE_SETTINGS


@override_settings(**LIVE_SETTINGS)
class UsageTests(TransactionTestCase):
    def setUp(self):
        self.owner = User.objects.create_user(
            "usage@example.test", None, display_name="Fictional", live_chat_enabled=True
        )
        self.other = User.objects.create_user(
            "other-usage@example.test", None, display_name="Other", live_chat_enabled=True
        )
        self.chat = Chat.objects.create(owner=self.owner, title="Fictional chat")
        self.reply = patch(
            "chats.turns.service.generate_reply", return_value=ChatReply("Ready", "live")
        )
        self.provider = self.reply.start()
        self.addCleanup(self.reply.stop)

    def submit(self, *, owner=None, chat=None, request_id=None, content="Fictional request"):
        return turns.submit(
            owner=owner or self.owner,
            pk=(chat or self.chat).pk,
            request_id=request_id or uuid4(),
            content=content,
            note_ids=[],
            language="en",
        )

    def reserve(self, chat=None):
        return turns.reserve(
            owner=self.owner,
            pk=(chat or self.chat).pk,
            request_id=uuid4(),
            content="Fictional request",
            note_ids=[],
            language="en",
        )

    def seed(self, *, owner=None, created_at=None, pending=False, expires_at=None):
        now = timezone.now()
        return LiveUsage.objects.create(
            owner=owner or self.owner,
            created_at=created_at or now,
            expires_at=expires_at or now + timedelta(seconds=60),
            finished_at=None if pending else now,
        )

    def test_unapproved_or_inactive_accounts_cannot_reserve_even_with_stale_user(self):
        for field in ("live_chat_enabled", "is_active"):
            with self.subTest(field=field):
                User.objects.filter(pk=self.owner.pk).update(**{field: False})
                self.assertIn(self.submit().status_code, (403, 404))
                self.assertFalse(LiveUsage.objects.exists())
                User.objects.filter(pk=self.owner.pk).update(**{field: True})
        self.provider.assert_not_called()

    @override_settings(FEMAKTIV_LIVE_USER_HOURLY_LIMIT=1)
    def test_paid_failure_and_chat_deletion_cannot_reset_allowance(self):
        self.provider.side_effect = ChatError("privacy_failed")
        request_id = uuid4()
        first = self.submit(request_id=request_id)
        self.assertEqual(first.status_code, 502)
        self.assertEqual(self.submit(request_id=request_id).content, first.content)
        self.assertEqual(self.provider.call_count, 1)
        self.assertEqual(LiveUsage.objects.count(), 1)
        self.assertIsNotNone(LiveUsage.objects.get().finished_at)
        self.chat.delete()
        other_chat = Chat.objects.create(owner=self.owner, title="Fresh chat")
        self.assertEqual(self.submit(chat=other_chat).status_code, 429)
        self.assertEqual(LiveUsage.objects.count(), 1)
        self.assertFalse(ChatTurn.objects.exists())
        self.assertEqual(self.provider.call_count, 1)

    def test_completed_duplicate_reuses_result_without_new_allowance(self):
        request_id = uuid4()
        response = self.submit(request_id=request_id)
        self.assertEqual(response.status_code, 201)
        self.assertEqual(self.submit(request_id=request_id).content, response.content)
        self.assertEqual(self.provider.call_count, 1)
        self.assertEqual(LiveUsage.objects.count(), 1)

    @override_settings(FEMAKTIV_LIVE_DAILY_LIMIT=1)
    def test_global_allowance_survives_account_and_chat_deletion(self):
        self.assertEqual(self.submit().status_code, 201)
        self.owner.delete()
        self.assertIsNone(LiveUsage.objects.get().owner_id)
        other_chat = Chat.objects.create(owner=self.other, title="Other owner")
        self.assertEqual(self.submit(owner=self.other, chat=other_chat).status_code, 429)
        self.assertEqual(self.provider.call_count, 1)

    @override_settings(FEMAKTIV_LIVE_USER_HOURLY_LIMIT=1, FEMAKTIV_LIVE_DAILY_LIMIT=3)
    def test_rolling_hour_does_not_reset_at_clock_hour(self):
        now = datetime(2026, 9, 12, 12, 1, tzinfo=dt_timezone.utc)
        self.seed(created_at=now - timedelta(minutes=2))
        with patch("chats.usage.timezone.now", return_value=now):
            self.assertEqual(self.submit().status_code, 429)
        LiveUsage.objects.update(created_at=now - timedelta(hours=1))
        with patch("chats.usage.timezone.now", return_value=now):
            self.assertEqual(self.submit().status_code, 201)

    @override_settings(FEMAKTIV_LIVE_DAILY_LIMIT=1)
    def test_daily_allowance_resets_at_utc_midnight_and_hourly_still_applies(self):
        now = datetime(2026, 9, 13, 0, 1, tzinfo=dt_timezone.utc)
        self.seed(owner=self.other, created_at=now - timedelta(minutes=2))
        with patch("chats.usage.timezone.now", return_value=now):
            self.assertEqual(self.submit().status_code, 201)
            self.assertEqual(self.submit().status_code, 429)

    def test_one_account_lease_survives_deleting_active_chat(self):
        _, turn, _ = self.reserve()
        self.chat.delete()
        replacement = Chat.objects.create(owner=self.owner, title="Replacement")
        self.assertEqual(self.submit(chat=replacement).status_code, 409)
        self.provider.assert_not_called()
        usage.finish(turn.usage_id)
        self.assertEqual(self.submit(chat=replacement).status_code, 201)
        self.assertEqual(LiveUsage.objects.count(), 2)

    def test_deleted_chat_lease_expires_after_worker_crash(self):
        _, turn, _ = self.reserve()
        self.chat.delete()
        LiveUsage.objects.filter(pk=turn.usage_id).update(
            expires_at=timezone.now() - timedelta(seconds=1)
        )
        self.assertEqual(
            self.submit(chat=Chat.objects.create(owner=self.owner, title="Next")).status_code, 201
        )

    def test_second_chat_is_busy_but_completed_other_accounts_can_send(self):
        _, turn, _ = self.reserve()
        second = Chat.objects.create(owner=self.owner, title="Same owner")
        self.assertEqual(self.submit(chat=second).status_code, 409)
        other_chat = Chat.objects.create(owner=self.other, title="Other owner")
        self.assertEqual(self.submit(owner=self.other, chat=other_chat).status_code, 201)
        usage.finish(turn.usage_id)
        self.assertEqual(self.submit(chat=second).status_code, 201)

    def test_context_invalidated_worker_keeps_lease_until_external_work_finishes(self):
        other_chat = Chat.objects.create(owner=self.owner, title="Second")

        def generate(**kwargs):
            from chats.context import start_segment

            start_segment(self.chat)
            self.assertEqual(self.submit(chat=other_chat).status_code, 409)
            return ChatReply("Obsolete", "live")

        self.provider.side_effect = generate
        self.assertEqual(self.submit().status_code, 409)
        self.assertIsNotNone(LiveUsage.objects.get().finished_at)
        self.assertFalse(Message.objects.exists())

    def test_bulk_delete_during_inference_preserves_lease_and_discards_late_reply(self):
        PersonalNote.objects.create(owner=self.owner, title="Fictional", body="Private context")
        client = Client()
        client.force_login(self.owner)

        def generate(**kwargs):
            response = client.post("/en/accounts/settings/delete-data/", {"confirm": "on"})
            self.assertEqual(response.status_code, 302)
            self.assertFalse(Chat.objects.filter(owner=self.owner).exists())
            self.assertFalse(PersonalNote.objects.filter(owner=self.owner).exists())
            self.assertTrue(
                LiveUsage.objects.filter(owner=self.owner, finished_at__isnull=True).exists()
            )
            fresh = Chat.objects.create(owner=self.owner, title="Created after deletion")
            self.assertEqual(self.submit(chat=fresh).status_code, 409)
            return ChatReply("Late reply", "live")

        self.provider.side_effect = generate
        self.assertEqual(self.submit().status_code, 404)
        self.assertFalse(Message.objects.exists())
        self.assertFalse(ChatTurn.objects.exists())
        self.assertIsNotNone(LiveUsage.objects.get().finished_at)

    def test_approval_revoked_during_intake_stops_next_provider_stage(self):
        from tests.unit.chats.fixtures import intake

        self.reply.stop()

        def model(**kwargs):
            User.objects.filter(pk=self.owner.pk).update(live_chat_enabled=False)
            return intake()

        with patch("chats.provider.complete", side_effect=model) as model_call:
            response = self.submit()
        self.assertEqual(response.status_code, 403)
        self.assertEqual(model_call.call_count, 1)
        self.assertFalse(Message.objects.exists())
        self.assertIsNotNone(LiveUsage.objects.get().finished_at)

    def test_invalid_preparation_rolls_back_allowance(self):
        with self.assertRaises(ChatError):
            turns.reserve(
                owner=self.owner,
                pk=self.chat.pk,
                request_id=uuid4(),
                content="Fictional",
                note_ids=[uuid4()],
                language="en",
            )
        self.assertFalse(LiveUsage.objects.exists())
        self.assertFalse(ChatTurn.objects.exists())

    @override_settings(FEMAKTIV_LIVE_DAILY_LIMIT=1)
    def test_concurrent_accounts_cannot_spend_same_last_allowance(self):
        # Seed gate to exercise the ordinary concurrent-admission path.
        LiveUsageGate.objects.get_or_create(pk=1)
        other_chat = Chat.objects.create(owner=self.other, title="Other")
        barrier = Barrier(2)

        def send(owner, chat):
            close_old_connections()
            try:
                barrier.wait(timeout=5)
                return self.submit(owner=owner, chat=chat).status_code
            finally:
                close_old_connections()

        with ThreadPoolExecutor(max_workers=2) as pool:
            jobs = [
                pool.submit(send, self.owner, self.chat),
                pool.submit(send, self.other, other_chat),
            ]
            statuses = [job.result(timeout=10) for job in jobs]
        self.assertEqual(LiveUsage.objects.count(), 1)
        self.assertEqual(self.provider.call_count, 1)
        # SQLite's shared in-memory test database can reject a contending writer
        # immediately. Existing reservation recovery returns 409 (or 503 if the
        # recovery read also contends); neither branch starts another paid call.
        self.assertTrue(all(status in (201, 409, 429, 503) for status in statuses), statuses)

    def test_migration_preserves_historical_usage_and_running_lease(self):
        now = timezone.now()
        finished = ChatTurn.objects.create(
            chat=self.chat,
            client_request_id=uuid4(),
            fingerprint="a" * 64,
            status="completed",
            context_version=1,
            language="en",
            expires_at=now,
        )
        pending = ChatTurn.objects.create(
            chat=self.chat,
            client_request_id=uuid4(),
            fingerprint="b" * 64,
            status="processing",
            context_version=1,
            language="en",
            expires_at=now + timedelta(seconds=60),
        )
        migration = import_module(
            "chats.migrations.0003_liveusagegate_liveusage_chatturn_usage_and_more"
        )
        with connection.schema_editor(atomic=False) as editor:
            migration.preserve_usage(apps, editor)
        finished.refresh_from_db()
        pending.refresh_from_db()
        self.assertEqual(finished.usage.created_at, finished.created_at)
        self.assertIsNotNone(finished.usage.finished_at)
        self.assertIsNone(pending.usage.finished_at)
        self.assertEqual(pending.usage.expires_at, pending.expires_at)
        self.chat.delete()
        self.assertEqual(LiveUsage.objects.count(), 2)
