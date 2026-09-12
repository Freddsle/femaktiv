import uuid
from datetime import timedelta
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import LiveServerTestCase, override_settings
from django.utils import timezone
from django.utils.translation import gettext, override
from playwright.sync_api import expect

from chats.models import ActiveNote, Chat, ChatTurn, LiveUsage, Message, MessageContextSnapshot
from notes.models import PersonalNote
from tests.unit.chats.fixtures import LIVE_SETTINGS

from . import test_platform


@override_settings(FEMAKTIV_SIGNUP_ENABLED=False)
class PrivacyBrowserTests(LiveServerTestCase):
    database_value = test_platform.PlatformBrowserTests.database_value
    goto = test_platform.PlatformBrowserTests.goto
    login = test_platform.PlatformBrowserTests.login
    new_chat = test_platform.PlatformBrowserTests.new_chat
    no_overflow = test_platform.PlatformBrowserTests.no_overflow

    def setUp(self):
        self.expected_http_errors = {}
        test_platform.PlatformBrowserTests.setUp(self)

    def record_response(self, response):
        key = (response.status, response.url, response.request.method)
        if self.expected_http_errors.get(key, 0):
            self.expected_http_errors[key] -= 1
        else:
            test_platform.PlatformBrowserTests.record_response(self, response)

    def expect_http_error(self, status, path, method="GET"):
        key = (status, self.live_server_url + path, method)
        self.expected_http_errors[key] = self.expected_http_errors.get(key, 0) + 1

    def tearDown(self):
        try:
            test_platform.PlatformBrowserTests.tearDown(self)
        finally:
            self.assertFalse(
                any(self.expected_http_errors.values()), "An expected HTTP error was not observed"
            )

    def translated(self, text, language):
        with override(language):
            translated = gettext(text)
        if language == "de":
            self.assertNotEqual(translated, text, "German privacy controls must be translated")
        return translated

    @staticmethod
    def create_saved_data(owner):
        note = PersonalNote.objects.create(
            owner=owner, title="Fictional food preferences", body="Milk allergy, warm meals."
        )
        chat = Chat.objects.create(owner=owner, title="Fictional food chat", context_version=1)
        message = Message.objects.create(
            chat=chat,
            role=Message.Role.USER,
            content="Fictional saved question",
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
        MessageContextSnapshot.objects.create(
            message=message,
            source_note=None,
            original_note_id=uuid.uuid4(),
            title="Deleted original note",
            body="Historical fictional note copy",
        )
        ActiveNote.objects.create(
            chat=chat,
            source_note=note,
            original_note_id=note.pk,
            title=note.title,
            body=note.body,
        )
        allowance = LiveUsage.objects.create(
            owner=owner, expires_at=timezone.now() + timedelta(seconds=60)
        )
        ChatTurn.objects.create(
            chat=chat,
            usage=allowance,
            client_request_id=uuid.uuid4(),
            fingerprint="f" * 64,
            content="Fictional pending question",
            note_copies=[{"title": note.title, "body": note.body}],
            context_version=1,
            language="en",
            expires_at=allowance.expires_at,
        )
        return chat, note

    def test_closed_signup_both_languages_and_widths(self):
        initial_count = self.database_value(get_user_model().objects.count)
        for language in ("en", "de"):
            for width in (390, 1440):
                with self.subTest(language=language, width=width):
                    self.page.set_viewport_size(
                        {"width": width, "height": 844 if width == 390 else 1000}
                    )
                    path = f"/{language}/accounts/signup/"
                    self.expect_http_error(403, path)
                    response = self.goto(path)
                    self.assertEqual(response.status, 403)
                    expect(self.page.locator("html")).to_have_attribute("lang", language)
                    expect(self.page.locator(".auth-card h2")).to_have_text(
                        self.translated("Registration is closed", language)
                    )
                    expect(self.page.locator("#id_email")).to_have_count(0)
                    expect(
                        self.page.locator(".auth-card a[href$='/accounts/login/']")
                    ).to_be_visible()
                    self.no_overflow()
        self.assertEqual(self.database_value(get_user_model().objects.count), initial_count)

    def test_delete_review_cancel_and_confirmation_both_languages_and_widths(self):
        def create_other():
            other = get_user_model().objects.create_user(
                email="other-browser@example.test",
                password="Other-browser-451!",
                display_name="Other tester",
            )
            self.create_saved_data(other)
            return other.pk

        other_id = self.database_value(create_other)
        self.login()
        for language in ("en", "de"):
            for width in (390, 1440):
                with self.subTest(language=language, width=width):
                    chat, note = self.database_value(lambda: self.create_saved_data(self.user))
                    usage_before = self.database_value(LiveUsage.objects.count)
                    self.page.set_viewport_size(
                        {"width": width, "height": 844 if width == 390 else 1000}
                    )
                    settings_path = f"/{language}/accounts/settings/"
                    delete_path = settings_path + "delete-data/"
                    self.goto(settings_path)
                    self.no_overflow()
                    delete_link = self.page.locator("main a[href$='/settings/delete-data/']")
                    expect(delete_link).to_have_text(
                        self.translated("Delete my chats and notes", language)
                    )
                    delete_link.focus()
                    self.page.keyboard.press("Enter")
                    self.page.wait_for_url(self.live_server_url + delete_path)
                    expect(self.page.locator("main h1")).to_have_text(
                        self.translated("Delete all your chats and notes?", language)
                    )
                    expect(self.page.locator("#id_confirm")).not_to_be_checked()
                    self.no_overflow()
                    self.page.locator("main form a[href$='/accounts/settings/']").focus()
                    self.page.keyboard.press("Enter")
                    self.page.wait_for_url(self.live_server_url + settings_path)
                    self.assertTrue(
                        self.database_value(lambda: Chat.objects.filter(pk=chat.pk).exists())
                    )
                    self.assertTrue(
                        self.database_value(
                            lambda: PersonalNote.objects.filter(pk=note.pk).exists()
                        )
                    )
                    self.page.locator("main a[href$='/settings/delete-data/']").focus()
                    self.page.keyboard.press("Enter")
                    self.page.wait_for_url(self.live_server_url + delete_path)
                    self.page.locator("#id_confirm").focus()
                    self.page.keyboard.press("Space")
                    expect(self.page.locator("#id_confirm")).to_be_checked()
                    self.page.keyboard.press("Tab")
                    expect(self.page.locator("main form button[type=submit]")).to_be_focused()
                    self.no_overflow()
                    self.page.screenshot(
                        path=str(self.screenshot_dir / f"privacy-{language}-{width}.png"),
                        full_page=True,
                    )
                    self.page.keyboard.press("Enter")
                    self.page.wait_for_url(self.live_server_url + settings_path)
                    expect(self.page.locator("main h1")).to_have_text(
                        self.translated("Account settings", language)
                    )
                    self.assertEqual(self.database_value(LiveUsage.objects.count), usage_before)
                    self.assertFalse(
                        self.database_value(lambda: Chat.objects.filter(owner=self.user).exists())
                    )
                    self.assertFalse(
                        self.database_value(
                            lambda: PersonalNote.objects.filter(owner=self.user).exists()
                        )
                    )
                    for model, count in (
                        (Chat, 1),
                        (PersonalNote, 1),
                        (Message, 1),
                        (MessageContextSnapshot, 2),
                        (ActiveNote, 1),
                        (ChatTurn, 1),
                    ):
                        self.assertEqual(self.database_value(model.objects.count), count)
                    self.assertTrue(
                        self.database_value(lambda: Chat.objects.filter(owner_id=other_id).exists())
                    )
                    self.assertEqual(self.database_value(get_user_model().objects.count), 2)

    @override_settings(**LIVE_SETTINGS)
    def test_unapproved_live_access_keeps_draft_without_provider_calls(self):
        self.database_value(
            lambda: get_user_model().objects.filter(pk=self.user.pk).update(live_chat_enabled=False)
        )
        self.login()
        self.new_chat()
        chat_path = self.page.url.removeprefix(self.live_server_url)
        message_path = chat_path.replace("/chats/", "/api/chats/") + "messages/"
        self.expect_http_error(403, message_path, "POST")
        with (
            patch("chats.provider.complete") as provider,
            patch("chats.transport.request") as network,
        ):
            self.page.locator("#chat-content").fill(
                "Keep this fictional draft while access is pending."
            )
            self.page.locator("#chat-form [type=submit]").click()
            expect(self.page.locator("#chat-status")).to_contain_text("approved testers")
            expect(self.page.locator("#chat-content")).to_have_value(
                "Keep this fictional draft while access is pending."
            )
            expect(self.page.locator("#chat-form [type=submit]")).to_be_enabled()
            provider.assert_not_called()
            network.assert_not_called()
        self.assertEqual(self.database_value(Message.objects.count), 0)
        self.assertEqual(self.database_value(ChatTurn.objects.count), 0)
        self.assertEqual(self.database_value(LiveUsage.objects.count), 0)
