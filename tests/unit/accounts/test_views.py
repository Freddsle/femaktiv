import re
import uuid
from datetime import timedelta
from unittest.mock import patch

from django.contrib.auth.hashers import make_password
from django.contrib.auth.tokens import default_token_generator
from django.core import mail
from django.test import Client, TestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from django.utils.translation import override

from accounts.forms import AccountSettingsForm
from accounts.models import User
from chats.models import ActiveNote, Chat, ChatTurn, Message, MessageContextSnapshot
from notes.models import PersonalNote


@override_settings(
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend", FEMAKTIV_SIGNUP_ENABLED=True
)
class AccountViewsTests(TestCase):
    password = "Start-quietly-314!"

    def setUp(self):
        self.user = User.objects.create_user("hana@example.com", self.password, display_name="Hana")

    def test_signup_creates_normalized_account_and_session_without_privileges(self):
        session = self.client.session
        session["guest_preference"] = "en"
        session.save()
        previous_session_key = session.session_key
        response = self.client.post(
            reverse("accounts:signup"),
            {
                "email": "LENA@Example.COM",
                "display_name": "Lena",
                "password1": self.password,
                "password2": self.password,
                "is_staff": "true",
                "is_superuser": "true",
                "live_chat_enabled": "true",
            },
        )
        self.assertRedirects(response, reverse("chats:list"), fetch_redirect_response=False)
        user = User.objects.get(email="lena@example.com")
        self.assertEqual(int(self.client.session["_auth_user_id"]), user.pk)
        self.assertNotEqual(self.client.session.session_key, previous_session_key)
        self.assertFalse(user.is_staff)
        self.assertFalse(user.is_superuser)
        self.assertFalse(user.live_chat_enabled)

    def test_signup_rejects_duplicate_email_and_weak_password(self):
        response = self.client.post(
            reverse("accounts:signup"),
            {
                "email": "HANA@EXAMPLE.COM",
                "display_name": "Another",
                "password1": self.password,
                "password2": self.password,
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("email", response.context["form"].errors)
        response = self.client.post(
            reverse("accounts:signup"),
            {
                "email": "new@example.com",
                "display_name": "New",
                "password1": "123",
                "password2": "123",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("password2", response.context["form"].errors)
        self.assertEqual(User.objects.count(), 1)

    def test_login_accepts_mixed_case_email_and_blocks_external_next(self):
        response = self.client.post(
            reverse("accounts:login") + "?next=https://example.org/",
            {
                "username": "HANA@EXAMPLE.COM",
                "password": self.password,
            },
        )
        self.assertRedirects(response, reverse("chats:list"), fetch_redirect_response=False)
        self.assertIn("_auth_user_id", self.client.session)

    def test_inactive_user_cannot_log_in(self):
        self.user.is_active = False
        self.user.save()
        response = self.client.post(
            reverse("accounts:login"),
            {
                "username": self.user.email,
                "password": self.password,
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_logout_requires_post_and_preserves_saved_notes(self):
        note = PersonalNote.objects.create(
            owner=self.user, title="Preferences", body="No mushrooms."
        )
        self.client.force_login(self.user)
        self.assertEqual(self.client.get(reverse("accounts:logout")).status_code, 405)
        self.assertIn("_auth_user_id", self.client.session)
        self.assertEqual(self.client.post(reverse("accounts:logout")).status_code, 302)
        self.assertNotIn("_auth_user_id", self.client.session)
        self.assertTrue(PersonalNote.objects.filter(pk=note.pk).exists())

    def test_signup_and_logout_require_csrf(self):
        client = Client(enforce_csrf_checks=True)
        self.assertEqual(client.post(reverse("accounts:signup"), {}).status_code, 403)
        client.force_login(self.user)
        self.assertEqual(client.post(reverse("accounts:logout")).status_code, 403)

    def test_settings_only_changes_display_name(self):
        self.client.force_login(self.user)
        response = self.client.post(
            reverse("accounts:settings"),
            {
                "display_name": "Hana updated",
                "email": "attacker@example.com",
                "is_staff": "true",
                "is_superuser": "true",
                "live_chat_enabled": "true",
                "password": "different",
            },
        )
        self.assertRedirects(response, reverse("accounts:settings"))
        self.user.refresh_from_db()
        self.assertEqual(self.user.display_name, "Hana updated")
        self.assertEqual(self.user.email, "hana@example.com")
        self.assertFalse(self.user.is_staff)
        self.assertFalse(self.user.live_chat_enabled)
        self.assertTrue(self.user.check_password(self.password))
        self.assertIn("no-store", response.headers["Cache-Control"])

    def test_profile_edit_preserves_concurrent_live_revocation_and_authentication_changes(self):
        self.user.live_chat_enabled = True
        self.user.save(update_fields=["live_chat_enabled"])
        self.client.force_login(self.user)
        original_validation = AccountSettingsForm.is_valid
        replacement_password = make_password("Recently-reset-618!")

        def revoke_after_validation(form):
            valid = original_validation(form)
            User.objects.filter(pk=self.user.pk).update(
                live_chat_enabled=False,
                email="updated-email@example.com",
                password=replacement_password,
            )
            return valid

        with patch.object(
            AccountSettingsForm, "is_valid", autospec=True, side_effect=revoke_after_validation
        ):
            response = self.client.post(
                reverse("accounts:settings"), {"display_name": "New display name"}
            )
        self.assertRedirects(response, reverse("accounts:settings"), fetch_redirect_response=False)
        self.user.refresh_from_db()
        self.assertEqual(self.user.display_name, "New display name")
        self.assertFalse(self.user.live_chat_enabled)
        self.assertEqual(self.user.email, "updated-email@example.com")
        self.assertEqual(self.user.password, replacement_password)

    def test_password_change_keeps_session_and_uses_new_password(self):
        self.client.force_login(self.user)
        response = self.client.post(
            reverse("accounts:password_change"),
            {
                "old_password": self.password,
                "new_password1": "New-quietly-2718!",
                "new_password2": "New-quietly-2718!",
            },
        )
        self.assertRedirects(response, reverse("accounts:password_change_done"))
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password("New-quietly-2718!"))
        self.assertEqual(self.client.get(reverse("accounts:settings")).status_code, 200)

    def test_recovery_sends_local_reset_url_and_does_not_reveal_unknown_accounts(self):
        response = self.client.post(reverse("accounts:password_reset"), {"email": self.user.email})
        self.assertRedirects(response, reverse("accounts:password_reset_done"))
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("femaktiv", mail.outbox[0].subject)
        self.assertRegex(mail.outbox[0].body, r"http://testserver/en/accounts/password/reset/")
        unknown = self.client.post(
            reverse("accounts:password_reset"), {"email": "unknown@example.com"}
        )
        self.assertEqual(unknown.status_code, response.status_code)
        self.assertEqual(unknown.url, response.url)
        self.assertEqual(len(mail.outbox), 1)

    def test_recovery_token_resets_password_and_cannot_be_reused(self):
        old_session = Client()
        old_session.force_login(self.user)
        token = default_token_generator.make_token(self.user)
        url = reverse(
            "accounts:password_reset_confirm",
            kwargs={
                "uidb64": urlsafe_base64_encode(force_bytes(self.user.pk)),
                "token": token,
            },
        )
        response = self.client.get(url)
        self.assertEqual(response.status_code, 302)
        self.assertIn("set-password", response.url)
        response = self.client.post(
            response.url,
            {
                "new_password1": "New-quietly-2718!",
                "new_password2": "New-quietly-2718!",
            },
        )
        self.assertRedirects(response, reverse("accounts:password_reset_complete"))
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password("New-quietly-2718!"))
        self.assertFalse(default_token_generator.check_token(self.user, token))
        self.assertEqual(old_session.get(reverse("accounts:settings")).status_code, 302)
        self.assertNotIn("_auth_user_id", old_session.session)

    def test_german_reset_email_contains_german_route(self):
        with override("de"):
            response = self.client.post(
                reverse("accounts:password_reset"), {"email": self.user.email}
            )
        self.assertEqual(response.status_code, 302)
        self.assertIn("/de/accounts/password/reset/", mail.outbox[0].body)
        self.assertIsNotNone(re.search(r"femaktiv", mail.outbox[0].subject))

    def test_settings_requires_authentication(self):
        self.assertEqual(self.client.get(reverse("accounts:settings")).status_code, 302)


@override_settings(FEMAKTIV_SIGNUP_ENABLED=False)
class ClosedSignupTests(TestCase):
    def test_registration_is_closed_in_both_languages_without_creating_accounts(self):
        for language in ("en", "de"):
            with self.subTest(language=language), override(language):
                url = reverse("accounts:signup")
                for method in (self.client.get, self.client.post):
                    response = method(
                        url,
                        {
                            "email": "tester@example.com",
                            "display_name": "Tester",
                            "password1": "Start-quietly-314!",
                            "password2": "Start-quietly-314!",
                        },
                    )
                    self.assertEqual(response.status_code, 403)
                    self.assertTemplateUsed(response, "accounts/signup_closed.html")
                    self.assertContains(response, reverse("accounts:login"), status_code=403)
                    self.assertNotContains(response, 'name="password1"', status_code=403)
                    self.assertIn("no-store", response.headers["Cache-Control"])
        self.assertFalse(User.objects.exists())


class DeletePrivateDataTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user(
            "owner@example.com", "Start-quietly-314!", display_name="Owner"
        )
        self.other = User.objects.create_user(
            "other@example.com", "Start-quietly-314!", display_name="Other"
        )
        self.owner_chat, self.owner_note = self.create_saved_data(self.owner)
        self.other_chat, self.other_note = self.create_saved_data(self.other)
        self.url = reverse("accounts:delete_private_data")
        self.client.force_login(self.owner)

    @staticmethod
    def create_saved_data(owner):
        note = PersonalNote.objects.create(owner=owner, title="Preferences", body="No milk.")
        chat = Chat.objects.create(owner=owner, title="Food", context_version=1)
        message = Message.objects.create(
            chat=chat,
            role=Message.Role.USER,
            content="Saved private text",
            mode="live",
            language="en",
            client_request_id=uuid.uuid4(),
            context_version=1,
        )
        MessageContextSnapshot.objects.create(
            message=message,
            source_note=note,
            original_note_id=note.pk,
            title=note.title,
            body=note.body,
        )
        ActiveNote.objects.create(
            chat=chat,
            source_note=note,
            original_note_id=note.pk,
            title=note.title,
            body=note.body,
        )
        ChatTurn.objects.create(
            chat=chat,
            client_request_id=uuid.uuid4(),
            fingerprint="a" * 64,
            content="Pending private text",
            note_copies=[{"title": note.title, "body": note.body}],
            context_version=1,
            language="en",
            expires_at=timezone.now() + timedelta(seconds=60),
        )
        return chat, note

    def test_review_is_non_destructive_and_requires_explicit_confirmation(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'name="confirm"')
        self.assertIn("no-store", response.headers["Cache-Control"])
        response = self.client.post(self.url)
        self.assertEqual(response.status_code, 400)
        self.assertIn("confirm", response.context["form"].errors)
        self.assertTrue(Chat.objects.filter(pk=self.owner_chat.pk).exists())
        self.assertTrue(PersonalNote.objects.filter(pk=self.owner_note.pk).exists())

    def test_deletion_removes_all_owners_copies_and_pending_turns_but_keeps_other_accounts(self):
        response = self.client.post(self.url, {"confirm": "on", "owner": self.other.pk})
        self.assertRedirects(response, reverse("accounts:settings"))
        for model in (Chat, PersonalNote, Message, MessageContextSnapshot, ActiveNote, ChatTurn):
            with self.subTest(model=model.__name__):
                self.assertEqual(model.objects.count(), 1)
        self.assertTrue(Chat.objects.filter(pk=self.other_chat.pk).exists())
        self.assertTrue(PersonalNote.objects.filter(pk=self.other_note.pk).exists())
        self.assertEqual(User.objects.count(), 2)
        self.assertEqual(int(self.client.session["_auth_user_id"]), self.owner.pk)

    def test_deletion_is_atomic_when_note_deletion_fails(self):
        with patch("accounts.views.PersonalNote.objects.filter") as note_filter:
            note_filter.return_value.delete.side_effect = RuntimeError("Simulated storage failure")
            with self.assertRaises(RuntimeError):
                self.client.post(self.url, {"confirm": "on"})
        self.assertTrue(Chat.objects.filter(pk=self.owner_chat.pk).exists())
        self.assertTrue(PersonalNote.objects.filter(pk=self.owner_note.pk).exists())
        self.assertEqual(Message.objects.count(), 2)
        self.assertEqual(ChatTurn.objects.count(), 2)

    def test_deletion_requires_authentication_and_csrf(self):
        anonymous = Client()
        self.assertEqual(anonymous.get(self.url).status_code, 302)
        self.assertEqual(anonymous.post(self.url, {"confirm": "on"}).status_code, 302)
        csrf_client = Client(enforce_csrf_checks=True)
        csrf_client.force_login(self.owner)
        self.assertEqual(csrf_client.post(self.url, {"confirm": "on"}).status_code, 403)
        self.assertTrue(Chat.objects.filter(pk=self.owner_chat.pk).exists())
        response = csrf_client.get(self.url)
        self.assertEqual(response.status_code, 200)
        response = csrf_client.post(
            self.url,
            {"confirm": "on", "csrfmiddlewaretoken": csrf_client.cookies["csrftoken"].value},
        )
        self.assertEqual(response.status_code, 302)
        self.assertFalse(Chat.objects.filter(pk=self.owner_chat.pk).exists())
