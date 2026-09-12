from django.contrib.auth import get_user_model
from django.test import TestCase

from chats import context
from chats.errors import ChatError
from chats.models import Chat


class ContextTests(TestCase):
    def setUp(self):
        owner = get_user_model().objects.create_user(
            email="context@example.test", password="test-pass-419!", display_name="Owner"
        )
        self.chat = Chat.objects.create(owner=owner, locality="Berlin", context_version=1)

    def test_retired_locality_action_is_rejected_without_mutation(self):
        with self.assertRaises(ChatError) as raised:
            context.update(self.chat, {"action": "locality", "locality": "Hamburg"})
        self.assertEqual(raised.exception.code, "invalid_context")
        self.chat.refresh_from_db()
        self.assertEqual(self.chat.locality, "Berlin")
        self.assertEqual(self.chat.context_version, 1)

    def test_legacy_locality_is_excluded_from_active_context(self):
        self.assertNotIn("locality", context.public_context(self.chat))
