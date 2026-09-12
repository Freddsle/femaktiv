import os
import shutil
from concurrent.futures import ThreadPoolExecutor

from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import LiveServerTestCase
from playwright.sync_api import expect, sync_playwright

from chats.models import Chat, Message


class PlatformBrowserTests(LiveServerTestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            email="browser@example.test", password="Browser-tests-419!", display_name="Alex"
        )
        self.playwright = sync_playwright().start()
        executable = (
            os.environ.get("FEMAKTIV_BROWSER_EXECUTABLE")
            or shutil.which("google-chrome")
            or shutil.which("chromium")
        )
        launch_options = {"headless": True}
        if executable:
            launch_options["executable_path"] = executable
        self.browser = self.playwright.chromium.launch(**launch_options)
        self.screenshot_dir = settings.BASE_DIR / ".local/screenshots"
        self.screenshot_dir.mkdir(parents=True, exist_ok=True)
        self.context = self.browser.new_context(
            viewport={"width": 1440, "height": 1000}, locale="de-DE"
        )
        self.page = self.context.new_page()
        self.page.set_default_timeout(7000)
        self.errors = []
        self.page.on("pageerror", lambda error: self.errors.append(str(error)))
        self.page.on("response", self.record_response)

    def record_response(self, response):
        if response.status >= 400:
            self.errors.append(f"HTTP {response.status}: {response.url}")

    def tearDown(self):
        self.page.screenshot(
            path=str(self.screenshot_dir / "last-browser-page.png"), full_page=True
        )
        self.context.close()
        self.browser.close()
        self.playwright.stop()
        self.assertEqual(self.errors, [], "Unexpected JavaScript errors")

    def database_value(self, callback):
        # Playwright's synchronous bridge has a running event loop on this thread.
        # Keep ORM assertions outside it without disabling Django's async safeguards.
        with ThreadPoolExecutor(max_workers=1) as executor:
            return executor.submit(callback).result()

    def goto(self, path):
        return self.page.goto(self.live_server_url + path)

    def login(self):
        self.goto("/en/accounts/login/")
        self.page.locator("#id_username").fill("browser@example.test")
        self.page.locator("#id_password").fill("Browser-tests-419!")
        self.page.locator("main form button[type=submit]").click()
        self.page.wait_for_url("**/en/chats/")

    def new_chat(self):
        self.page.locator("#chat-sidebar form button[type=submit]").click()
        self.page.wait_for_url("**/en/chats/*/")
        expect(self.page.locator("#chat-form")).to_be_visible()

    def no_overflow(self):
        self.assertTrue(
            self.page.evaluate("document.documentElement.scrollWidth <= window.innerWidth + 1")
        )

    def test_account_notes_chat_and_language_journey(self):
        self.goto("/en/accounts/signup/")
        self.page.locator("#id_display_name").fill("Alex")
        self.page.locator("#id_email").fill("journey@example.test")
        self.page.locator("#id_password1").fill("Quiet-river-429!")
        self.page.locator("#id_password2").fill("Quiet-river-429!")
        self.page.locator("main form button[type=submit]").click()
        self.page.wait_for_url("**/en/chats/")
        self.goto("/en/notes/new/")
        self.page.locator("#id_title").fill("Lunch preferences")
        self.page.locator("#id_body").fill("Warm meals, fifteen minutes, no milk.")
        self.page.get_by_role("button", name="Save note").click()
        self.page.wait_for_url("**/en/notes/")
        expect(self.page.get_by_role("heading", name="Lunch preferences")).to_be_visible()
        self.goto("/en/chats/")
        self.new_chat()
        chat_path = self.page.url.removeprefix(self.live_server_url)
        self.page.locator(".note-picker > summary").click()
        self.page.get_by_label("Lunch preferences").check()
        self.page.locator("#chat-content").fill("Help me organise my lunch ideas.")
        self.page.get_by_role("button", name="Send message").click()
        expect(self.page.locator(".message")).to_have_count(2)
        expect(self.page.locator(".message-assistant")).to_contain_text("not connected")
        self.page.locator(".message-context summary").click()
        expect(self.page.locator(".snapshot")).to_contain_text(
            "Warm meals, fifteen minutes, no milk."
        )
        self.page.screenshot(path=str(self.screenshot_dir / "chat-en-desktop.png"), full_page=True)
        self.page.get_by_role("button", name="Deutsch", exact=True).click()
        self.page.wait_for_url("**/de/chats/*/")
        expect(self.page.locator("html")).to_have_attribute("lang", "de")
        expect(self.page.locator(".message-user")).to_contain_text(
            "Help me organise my lunch ideas."
        )
        self.page.reload()
        expect(self.page.locator(".message")).to_have_count(2)
        self.page.set_viewport_size({"width": 390, "height": 844})
        self.no_overflow()
        self.page.screenshot(path=str(self.screenshot_dir / "chat-de-mobile.png"), full_page=True)
        self.goto("/en/accounts/settings/")
        self.page.set_viewport_size({"width": 1440, "height": 1000})
        self.page.locator(".account-menu > summary").click()
        self.page.get_by_role("button", name="Log out", exact=True).click()
        self.goto(chat_path)
        self.page.wait_for_url("**/en/accounts/login/?next=**")
        self.page.locator("#id_username").fill("journey@example.test")
        self.page.locator("#id_password").fill("Quiet-river-429!")
        self.page.locator("main form button[type=submit]").click()
        expect(self.page.locator(".message")).to_have_count(2)

    def test_failed_request_keeps_draft_and_skip_link_does_not_disable_chat(self):
        self.login()
        self.new_chat()
        self.page.locator(".skip-link").focus()
        self.page.keyboard.press("Enter")
        self.page.locator("#chat-content").fill("Keep this draft when the connection fails.")
        self.page.route("**/api/chats/*/messages/", lambda route: route.abort("failed"))
        self.page.get_by_role("button", name="Send message").click()
        expect(self.page.locator("#chat-status")).to_contain_text("could not be sent")
        expect(self.page.locator("#chat-content")).to_have_value(
            "Keep this draft when the connection fails."
        )
        self.page.unroute("**/api/chats/*/messages/")
        self.page.get_by_role("button", name="Send message").click()
        expect(self.page.locator(".message")).to_have_count(2)
        self.assertEqual(self.database_value(Message.objects.count), 2)

    def test_late_response_does_not_replace_new_page(self):
        self.login()
        self.new_chat()
        held = []

        def hold(route):
            held.append((route, route.fetch()))
            self.page.evaluate("window.femaktivTestResponseReady = true")

        self.page.route("**/api/chats/*/messages/", hold)
        self.page.locator("#chat-content").fill("A thought saved just before navigating away.")
        self.page.get_by_role("button", name="Send message").click()
        expect(self.page.locator("#chat-status")).to_contain_text("Saving")
        # Wait for the database-backed response while leaving browser delivery pending.
        self.page.wait_for_function("window.femaktivTestResponseReady === true")
        self.page.locator(".main-nav > a[href$='/notes/']").click()
        self.page.wait_for_url("**/en/notes/")
        self.assertEqual(len(held), 1)
        held[0][0].fulfill(response=held[0][1])
        expect(self.page.locator("h1")).to_have_text("My notes")
        expect(self.page.locator("#chat-thread")).to_have_count(0)
        self.assertEqual(self.database_value(lambda: Chat.objects.get().messages.count()), 2)

    def test_public_examples_and_responsive_bilingual_layouts(self):
        self.goto("/")
        self.page.wait_for_url("**/en/")
        expect(self.page.locator("html")).to_have_attribute("lang", "en")
        self.page.screenshot(path=str(self.screenshot_dir / "home-en-desktop.png"), full_page=True)
        self.no_overflow()
        self.page.get_by_role("button", name="Deutsch", exact=True).click()
        self.page.wait_for_url("**/de/")
        expect(self.page.locator("html")).to_have_attribute("lang", "de")
        self.page.screenshot(path=str(self.screenshot_dir / "home-de-desktop.png"), full_page=True)
        self.page.set_viewport_size({"width": 390, "height": 844})
        self.no_overflow()
        self.page.screenshot(path=str(self.screenshot_dir / "home-de-mobile.png"), full_page=True)
        self.goto("/en/community/")
        expect(self.page.locator(".question-card")).to_have_count(6)
        expect(self.page.locator(".preview-notice")).to_contain_text("written examples")
        self.page.get_by_role("link", name="Family care", exact=True).click()
        expect(self.page.locator(".question-card")).to_have_count(2)
        self.no_overflow()
        self.page.screenshot(
            path=str(self.screenshot_dir / "community-en-mobile.png"), full_page=True
        )
        self.goto("/en/examples/family-care/")
        expect(self.page.locator("main")).to_contain_text("example")
        self.no_overflow()
