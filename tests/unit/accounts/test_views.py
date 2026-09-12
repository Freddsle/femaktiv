import re

from django.contrib.auth.tokens import default_token_generator
from django.core import mail
from django.test import Client, TestCase, override_settings
from django.urls import reverse
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from django.utils.translation import override

from accounts.models import User
from notes.models import PersonalNote


@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
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
            },
        )
        self.assertRedirects(response, reverse("chats:list"), fetch_redirect_response=False)
        user = User.objects.get(email="lena@example.com")
        self.assertEqual(int(self.client.session["_auth_user_id"]), user.pk)
        self.assertNotEqual(self.client.session.session_key, previous_session_key)
        self.assertFalse(user.is_staff)
        self.assertFalse(user.is_superuser)

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
                "password": "different",
            },
        )
        self.assertRedirects(response, reverse("accounts:settings"))
        self.user.refresh_from_db()
        self.assertEqual(self.user.display_name, "Hana updated")
        self.assertEqual(self.user.email, "hana@example.com")
        self.assertFalse(self.user.is_staff)
        self.assertTrue(self.user.check_password(self.password))
        self.assertIn("no-store", response.headers["Cache-Control"])

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
