from unittest.mock import patch

from django.test import Client, TestCase
from django.urls import reverse

from accounts.models import User
from notes.forms import PersonalNoteForm
from notes.models import PersonalNote


class NoteViewsTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.owner = User.objects.create_user(
            "hana@example.com", "Start-quietly-314!", display_name="Hana"
        )
        cls.other = User.objects.create_user(
            "other@example.com", "Start-quietly-314!", is_staff=True
        )
        cls.note = PersonalNote.objects.create(
            owner=cls.owner, title="Only mine", body="Private preferences."
        )
        cls.other_note = PersonalNote.objects.create(
            owner=cls.other, title="Other person's", body="Never include me."
        )

    def setUp(self):
        self.client.force_login(self.owner)

    def test_list_only_contains_own_notes_and_is_not_cached(self):
        response = self.client.get(reverse("notes:list"))
        self.assertContains(response, self.note.title)
        self.assertNotContains(response, self.other_note.body)
        self.assertEqual(list(response.context["notes"]), [self.note])
        self.assertIn("no-store", response.headers["Cache-Control"])

    def test_create_assigns_owner_from_session(self):
        response = self.client.post(
            reverse("notes:create"),
            {
                "title": "Food",
                "body": "No mushrooms.",
                "owner": self.other.pk,
            },
        )
        self.assertRedirects(response, reverse("notes:list"))
        note = PersonalNote.objects.get(title="Food")
        self.assertEqual(note.owner, self.owner)

    def test_empty_and_oversized_input_is_rejected(self):
        for payload in [{"title": "   ", "body": " "}, {"title": "x" * 121, "body": "x" * 10001}]:
            response = self.client.post(reverse("notes:create"), payload)
            self.assertEqual(response.status_code, 200)
            self.assertIn("title", response.context["form"].errors)
            self.assertIn("body", response.context["form"].errors)
        self.assertEqual(PersonalNote.objects.count(), 2)

    def test_edit_updates_text_without_changing_owner(self):
        response = self.client.post(
            reverse("notes:edit", args=[self.note.pk]),
            {
                "title": "Updated",
                "body": "Neue Wünsche.",
                "owner": self.other.pk,
            },
        )
        self.assertRedirects(response, reverse("notes:list"))
        self.note.refresh_from_db()
        self.assertEqual(self.note.title, "Updated")
        self.assertEqual(self.note.body, "Neue Wünsche.")
        self.assertEqual(self.note.owner, self.owner)

    def test_foreign_notes_return_404_for_read_edit_and_delete(self):
        for name in ["notes:edit", "notes:delete"]:
            url = reverse(name, args=[self.other_note.pk])
            self.assertEqual(self.client.get(url).status_code, 404)
            self.assertEqual(
                self.client.post(url, {"title": "Stolen", "body": "Overwritten"}).status_code, 404
            )
        self.other_note.refresh_from_db()
        self.assertEqual(self.other_note.title, "Other person's")

    def test_edit_cannot_restore_a_note_deleted_after_form_validation(self):
        original_validation = PersonalNoteForm.is_valid

        def delete_after_validation(form):
            valid = original_validation(form)
            PersonalNote.objects.filter(owner=self.owner).delete()
            return valid

        with patch.object(
            PersonalNoteForm, "is_valid", autospec=True, side_effect=delete_after_validation
        ):
            response = self.client.post(
                reverse("notes:edit", args=[self.note.pk]),
                {"title": "Updated private title", "body": "Text that must stay deleted."},
            )
        self.assertEqual(response.status_code, 404)
        self.assertFalse(PersonalNote.objects.filter(owner=self.owner).exists())
        self.other_note.refresh_from_db()
        self.assertEqual(self.other_note.body, "Never include me.")

    def test_staff_privileges_do_not_allow_foreign_notes(self):
        self.client.force_login(self.other)
        self.assertEqual(
            self.client.get(reverse("notes:edit", args=[self.note.pk])).status_code, 404
        )
        self.assertEqual(
            self.client.post(reverse("notes:delete", args=[self.note.pk])).status_code, 404
        )

    def test_delete_requires_confirmation_post(self):
        url = reverse("notes:delete", args=[self.note.pk])
        self.assertEqual(self.client.get(url).status_code, 200)
        self.assertTrue(PersonalNote.objects.filter(pk=self.note.pk).exists())
        self.assertRedirects(self.client.post(url), reverse("notes:list"))
        self.assertFalse(PersonalNote.objects.filter(pk=self.note.pk).exists())

    def test_note_text_is_escaped(self):
        self.note.body = "<script>alert('private')</script>"
        self.note.save()
        response = self.client.get(reverse("notes:edit", args=[self.note.pk]))
        self.assertContains(response, "&lt;script&gt;")
        self.assertNotContains(response, "<script>alert")

    def test_notes_require_authentication(self):
        self.client.logout()
        for name, args in [
            ("notes:list", []),
            ("notes:create", []),
            ("notes:edit", [self.note.pk]),
            ("notes:delete", [self.note.pk]),
        ]:
            self.assertEqual(self.client.get(reverse(name, args=args)).status_code, 302)

    def test_note_mutations_require_csrf(self):
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.owner)
        for name, args in [
            ("notes:create", []),
            ("notes:edit", [self.note.pk]),
            ("notes:delete", [self.note.pk]),
        ]:
            self.assertEqual(
                client.post(
                    reverse(name, args=args), {"title": "No token", "body": "Blocked"}
                ).status_code,
                403,
            )
