from django.db import IntegrityError, transaction
from django.test import TestCase

from accounts.models import User


class UserTests(TestCase):
    def test_manager_normalizes_email_and_hashes_password(self):
        user = User.objects.create_user(
            "  Hana@Example.COM  ", "Start-quietly-314!", display_name="Hana"
        )
        self.assertEqual(user.email, "hana@example.com")
        self.assertTrue(user.check_password("Start-quietly-314!"))
        self.assertFalse(user.is_staff)
        self.assertFalse(user.is_superuser)
        self.assertEqual(User.objects.get_by_natural_key("HANA@EXAMPLE.COM"), user)

    def test_email_is_required(self):
        for email in ["", "  ", None]:
            with self.assertRaises(ValueError):
                User.objects.create_user(email, "Start-quietly-314!")

    def test_email_case_cannot_create_duplicate_account(self):
        User.objects.create_user("hana@example.com", "Start-quietly-314!")
        with self.assertRaises(IntegrityError), transaction.atomic():
            User.objects.create_user("HANA@EXAMPLE.COM", "Start-quietly-314!")

    def test_database_prevents_case_insensitive_duplicate_even_without_save(self):
        User.objects.create_user("hana@example.com", "Start-quietly-314!")
        other = User.objects.create_user("other@example.com", "Start-quietly-314!")
        with self.assertRaises(IntegrityError), transaction.atomic():
            User.objects.filter(pk=other.pk).update(email="HANA@example.com")

    def test_superuser_creation_enforces_privileges(self):
        user = User.objects.create_superuser(
            "admin@example.com", "Start-quietly-314!", display_name="Admin"
        )
        self.assertTrue(user.is_staff)
        self.assertTrue(user.is_superuser)
        with self.assertRaises(ValueError):
            User.objects.create_superuser("invalid@example.com", is_staff=False)
        with self.assertRaises(ValueError):
            User.objects.create_superuser("invalid@example.com", is_superuser=False)
