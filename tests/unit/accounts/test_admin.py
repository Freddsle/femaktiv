from django.contrib import admin
from django.test import RequestFactory, TestCase

from accounts.admin import AccountAdmin
from accounts.models import User


class AccountAdminTests(TestCase):
    def setUp(self):
        self.admin = AccountAdmin(User, admin.site)
        self.request = RequestFactory().get("/en/admin/accounts/user/add/")
        self.request.user = User.objects.create_superuser(
            "admin@example.com", "Start-quietly-314!", display_name="Admin"
        )

    def test_admin_add_form_uses_email_and_saves_a_hashed_password(self):
        form_class = self.admin.get_form(self.request)
        form = form_class(
            data={
                "email": "LENA@Example.COM",
                "display_name": "Lena",
                "password1": "Start-quietly-314!",
                "password2": "Start-quietly-314!",
            }
        )
        self.assertNotIn("username", form.fields)
        self.assertTrue(form.is_valid(), form.errors)
        user = form.save()
        self.assertEqual(user.email, "lena@example.com")
        self.assertTrue(user.check_password("Start-quietly-314!"))
        self.assertFalse(user.is_staff)
        self.assertFalse(user.live_chat_enabled)

    def test_admin_change_form_uses_custom_user_model(self):
        form_class = self.admin.get_form(self.request, obj=self.request.user)
        form = form_class(instance=self.request.user)
        self.assertEqual(form._meta.model, User)
        self.assertNotIn("username", form.fields)
        self.assertIn("display_name", form.fields)
        self.assertIn("live_chat_enabled", form.fields)

    def test_operator_can_approve_live_access_in_admin(self):
        self.client.force_login(self.request.user)
        tester = User.objects.create_user(
            "tester@example.com", "Start-quietly-314!", display_name="Tester"
        )
        response = self.client.post(
            f"/en/admin/accounts/user/{tester.pk}/change/",
            {
                "email": tester.email,
                "display_name": tester.display_name,
                "is_active": "on",
                "live_chat_enabled": "on",
                "date_joined_0": tester.date_joined.strftime("%Y-%m-%d"),
                "date_joined_1": tester.date_joined.strftime("%H:%M:%S"),
            },
        )
        self.assertEqual(response.status_code, 302)
        tester.refresh_from_db()
        self.assertTrue(tester.live_chat_enabled)
        self.assertFalse(tester.is_staff)
