from uuid import UUID

from django.core.exceptions import ValidationError
from django.test import TestCase

from accounts.models import User
from notes.models import PersonalNote


class PersonalNoteTests(TestCase):
    def test_notes_persist_as_owned_text_with_uuid_and_timestamps(self):
        user = User.objects.create_user("hana@example.com", "Start-quietly-314!")
        note = PersonalNote.objects.create(owner=user, title="Vorlieben", body="Keine Pilze.")
        saved = PersonalNote.objects.get(pk=note.pk)
        self.assertIsInstance(saved.pk, UUID)
        self.assertEqual(saved.owner, user)
        self.assertEqual(saved.body, "Keine Pilze.")
        self.assertIsNotNone(saved.created_at)
        self.assertIsNotNone(saved.updated_at)

    def test_text_limits_are_validated(self):
        user = User.objects.create_user("hana@example.com", "Start-quietly-314!")
        note = PersonalNote(owner=user, title="x" * 121, body="x" * 10001)
        with self.assertRaises(ValidationError) as error:
            note.full_clean()
        self.assertEqual(set(error.exception.message_dict), {"title", "body"})
