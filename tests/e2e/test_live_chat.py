import json
from unittest.mock import patch

from django.test import LiveServerTestCase, override_settings
from playwright.sync_api import expect

from chats.errors import ChatError
from chats.models import ActiveNote, Chat, Message
from chats.search import contact_record
from notes.models import PersonalNote
from tests.unit.chats.fixtures import LIVE_SETTINGS, answer, intake

from . import test_platform


@override_settings(**LIVE_SETTINGS)
class LiveChatBrowserTests(LiveServerTestCase):
    # Reuse the existing browser fixture without inheriting/rerunning its test cases.
    setUp = test_platform.PlatformBrowserTests.setUp
    tearDown = test_platform.PlatformBrowserTests.tearDown
    record_response = test_platform.PlatformBrowserTests.record_response
    database_value = test_platform.PlatformBrowserTests.database_value
    goto = test_platform.PlatformBrowserTests.goto
    login = test_platform.PlatformBrowserTests.login
    new_chat = test_platform.PlatformBrowserTests.new_chat
    no_overflow = test_platform.PlatformBrowserTests.no_overflow

    def send(self, content):
        self.page.locator("#chat-content").fill(content)
        self.page.locator("#chat-form [type=submit]").click()

    def test_live_nutrition_both_locales_sizes_notes_citations_and_keyboard(self):
        self.database_value(
            lambda: PersonalNote.objects.create(
                owner=self.user,
                title="Food context",
                body="Milk allergy. Hypertension. Fifteen minutes.",
            )
        )

        def model(**kwargs):
            return intake() if kwargs["name"] == "femaktiv_intake" else answer(kwargs["language"])

        with patch("chats.provider.complete", side_effect=model) as provider_mock:
            self.login()
            self.new_chat()
            self.page.locator(".skip-link").focus()
            self.page.keyboard.press("Enter")
            self.page.locator(".note-picker > summary").click()
            self.page.get_by_label("Food context", exact=True).check()
            self.send("More protein and fibre, please.")
            expect(self.page.locator(".message")).to_have_count(2)
            expect(self.page.locator(".message-assistant")).to_contain_text("without milk")
            expect(self.page.locator(".paragraph-citations a")).to_have_attribute(
                "href",
                "https://www.dge.de/gesunde-ernaehrung/gut-essen-und-trinken/dge-empfehlungen/",
            )
            expect(self.page.locator("[data-active-count]")).to_have_text("1")
            expect(self.page.locator(".chat-mode-notice")).to_contain_text("Anymize receives")
            self.send("Another quick idea.")
            expect(self.page.locator(".message")).to_have_count(4)
            self.assertEqual(self.database_value(ActiveNote.objects.count), 1)
            chat_path = self.page.url.removeprefix(self.live_server_url)
            for language in ("en", "de"):
                self.goto(chat_path.replace("/en/", f"/{language}/"))
                self.send("Noch eine Idee." if language == "de" else "One more idea.")
                expect(self.page.locator(".message-assistant").last).to_contain_text(
                    "ohne Milch" if language == "de" else "without milk"
                )
                for width, size in ((390, "mobile"), (1440, "desktop")):
                    self.page.set_viewport_size(
                        {"width": width, "height": 1000 if width > 400 else 844}
                    )
                    self.no_overflow()
                    self.page.locator("#chat-thread").evaluate(
                        "node => { node.style.scrollBehavior = 'auto'; node.scrollTop = node.scrollHeight; }"
                    )
                    self.page.screenshot(
                        path=str(self.screenshot_dir / f"live-chat-{language}-{size}.png"),
                        full_page=True,
                    )
            panel = self.page.locator("[data-live-context]")
            panel.locator(":scope > summary").focus()
            self.page.keyboard.press("Enter")
            expect(panel.locator(".active-note")).to_contain_text("Food context")
            self.page.get_by_role("button", name="Kopie entfernen", exact=True).click()
            expect(self.page.locator("[data-active-count]")).to_have_text("0")
            expect(self.page.locator("#chat-status")).to_contain_text("nicht erneut übermittelt")
            self.send("Ein neuer Gedanke.")
            expect(self.page.locator(".message-user").last).to_contain_text("Ein neuer Gedanke.")
            self.assertNotIn(
                "Milk allergy", provider_mock.call_args_list[-2].kwargs["messages"][1]["content"]
            )
            self.page.reload()
            expect(self.page.locator("[data-active-count]")).to_have_text("0")
            expect(self.page.locator(".paragraph-citations a").first).to_have_attribute(
                "rel", "noopener noreferrer"
            )

    def test_care_locality_clarification_verified_cards_and_call_preparation(self):
        record = contact_record(
            "https://care.example.test/berlin",
            "Pflegestützpunkt Example",
            "Berlin Pflegeberatung Kontakt 030 12345678",
            [],
            "Berlin",
            1,
        )

        def model(**kwargs):
            return (
                intake(topic="care", needs_local_services=True, evidence_topics=["discharge"])
                if kwargs["name"] == "femaktiv_intake"
                else answer(kwargs["language"], care=True)
            )

        with (
            patch("chats.provider.complete", side_effect=model),
            patch("chats.search.lookup", return_value=([record], "verified")) as lookup,
        ):
            self.login()
            self.new_chat()
            self.send(
                "My older mother is in hospital after a broken leg. Help arrange care and a German call."
            )
            expect(self.page.locator(".message-assistant")).to_contain_text(
                "city or German postcode"
            )
            lookup.assert_not_called()
            expect(self.page.locator("#chat-locality")).to_be_visible()
            self.page.locator("#chat-locality").fill("Berlin")
            self.page.get_by_role("button", name="Save locality", exact=True).click()
            expect(self.page.locator("#chat-status")).to_contain_text("Locality saved")
            self.send(
                "My older mother will leave hospital after a broken leg. Find care advice and prepare a German call."
            )
            expect(self.page.locator(".message")).to_have_count(4)
            expect(self.page.locator(".message-assistant").last).to_contain_text(
                "Welche Unterstützung"
            )
            expect(self.page.locator(".source-card[open]")).to_contain_text("030 12345678")
            expect(self.page.locator(".source-card[open]")).to_contain_text("unknown")
            expect(self.page.locator(".source-card[open] a")).to_have_attribute(
                "href", "https://care.example.test/berlin"
            )
            self.page.set_viewport_size({"width": 390, "height": 844})
            self.no_overflow()
            self.page.locator("#chat-thread").evaluate(
                "node => { node.style.scrollBehavior = 'auto'; node.scrollTop = node.scrollHeight; }"
            )
            self.page.screenshot(
                path=str(self.screenshot_dir / "live-care-en-mobile.png"), full_page=True
            )
            path = self.page.url.removeprefix(self.live_server_url).replace("/en/", "/de/")
            self.goto(path)
            self.send("Bitte bereite das Gespräch auf Deutsch vor.")
            expect(self.page.locator(".message-assistant").last).to_contain_text(
                "Frage den Sozialdienst"
            )
            self.page.reload()
            expect(self.page.locator(".source-card[open]").last).to_contain_text("nicht geklärt")
            self.no_overflow()

    def test_pending_status_recovers_result_without_second_paid_request(self):
        with patch("chats.provider.complete", side_effect=[intake(), answer()]) as model:
            self.login()
            self.new_chat()

            def pending_response(route):
                completed = route.fetch()
                data = completed.json()
                route.fulfill(
                    status=202,
                    content_type="application/json",
                    body=json.dumps({"status": "processing", "mode": "live", "chat": data["chat"]}),
                )

            self.page.route("**/api/chats/*/messages/", pending_response)
            self.send("Test a recovered reply.")
            expect(self.page.locator(".message")).to_have_count(2)
            expect(self.page.locator("#chat-content")).to_have_value("")
            self.assertEqual(model.call_count, 2)
            self.assertEqual(self.database_value(Message.objects.count), 2)

    def test_live_network_failure_retains_draft_and_request_id(self):
        self.login()
        self.new_chat()
        requests = []

        def fail(route):
            requests.append(route.request.post_data_json)
            route.abort("failed")

        self.page.route("**/api/chats/*/messages/", fail)
        self.send("Keep this fictional draft.")
        expect(self.page.locator("#chat-status")).to_contain_text("could not be sent")
        expect(self.page.locator("#chat-content")).to_have_value("Keep this fictional draft.")
        self.page.locator("#chat-form [type=submit]").click()
        expect(self.page.locator("#chat-form [type=submit]")).to_be_enabled()
        self.assertEqual(requests[0]["client_request_id"], requests[1]["client_request_id"])

    def test_live_late_response_cannot_replace_another_page(self):
        with patch("chats.provider.complete", side_effect=[intake(), answer()]):
            self.login()
            self.new_chat()
            held = []

            def hold(route):
                held.append((route, route.fetch()))
                self.page.evaluate("window.liveReplyHeld = true")

            self.page.route("**/api/chats/*/messages/", hold)
            self.send("A fictional thought before navigating.")
            self.page.wait_for_function("window.liveReplyHeld === true")
            self.page.locator(".main-nav > a[href$='/notes/']").click()
            self.page.wait_for_url("**/en/notes/")
            held[0][0].fulfill(response=held[0][1])
            expect(self.page.locator("h1")).to_have_text("My notes")
            self.assertEqual(self.database_value(lambda: Chat.objects.get().messages.count()), 2)

    def test_terminal_timeout_retains_draft_and_copies_and_waits_for_explicit_retry(self):
        self.database_value(
            lambda: PersonalNote.objects.create(
                owner=self.user, title="Fictional allergy", body="Milk allergy"
            )
        )
        expected_errors, requests = [], []
        self.page.remove_listener("response", self.record_response)
        self.page.on(
            "response",
            lambda response: (
                expected_errors.append(response.url)
                if response.status == 504
                else self.record_response(response)
            ),
        )
        self.page.on(
            "request",
            lambda request: (
                requests.append(request.post_data_json)
                if request.method == "POST" and request.url.endswith("/messages/")
                else None
            ),
        )
        with patch(
            "chats.provider.complete",
            side_effect=[ChatError("deadline_exceeded", 504), intake(), answer()],
        ) as model:
            self.login()
            self.new_chat()
            self.page.locator(".note-picker > summary").click()
            self.page.get_by_label("Fictional allergy", exact=True).check()
            self.send("Keep this timed-out draft.")
            expect(self.page.locator("#chat-status")).to_contain_text(
                "will not be retried automatically"
            )
            expect(self.page.locator("#chat-content")).to_have_value("Keep this timed-out draft.")
            expect(self.page.locator("[data-active-count]")).to_have_text("1")
            self.assertEqual(model.call_count, 1)
            self.assertEqual(self.database_value(Message.objects.count), 0)
            self.page.locator("[data-live-context] > summary").click()
            expect(self.page.get_by_role("button", name="Remove copy", exact=True)).to_be_visible()
            self.page.locator("#chat-form [type=submit]").click()
            expect(self.page.locator(".message")).to_have_count(2)
            self.assertEqual(model.call_count, 3)
            self.assertNotEqual(requests[0]["client_request_id"], requests[1]["client_request_id"])
            self.assertEqual(len(expected_errors), 1)
            self.assertTrue(expected_errors[0].endswith("/messages/"))

    def test_stalled_connection_has_browser_deadline_and_keeps_recovery_id(self):
        self.login()
        self.new_chat()
        self.page.clock.install()
        self.page.evaluate("""() => {
            const realFetch = window.fetch;
            window.deadlineTestRequests = [];
            window.fetch = (url, options) => {
                if (String(url).endsWith('/messages/')) {
                    window.deadlineTestRequests.push(JSON.parse(options.body));
                    if (window.deadlineTestRequests.length === 1) {
                        return new Promise((resolve, reject) => {
                            options.signal.addEventListener('abort', () => reject(options.signal.reason), { once: true });
                        });
                    }
                }
                return realFetch(url, options);
            };
        }""")
        self.send("Keep a stalled-connection draft.")
        expect(self.page.locator("#chat-status")).to_contain_text("Preparing")
        self.page.clock.fast_forward(76000)
        expect(self.page.locator("#chat-status")).to_contain_text("could not be sent")
        expect(self.page.locator("#chat-content")).to_have_value("Keep a stalled-connection draft.")
        expect(self.page.locator("#chat-form [type=submit]")).to_be_enabled()
        with patch("chats.provider.complete", side_effect=[intake(), answer()]):
            self.page.locator("#chat-form [type=submit]").click()
            expect(self.page.locator(".message")).to_have_count(2)
        requests = self.page.evaluate("window.deadlineTestRequests")
        self.assertEqual(requests[0]["client_request_id"], requests[1]["client_request_id"])

    def test_uncertain_context_write_requires_refresh_before_more_inference(self):
        self.login()
        self.new_chat()
        self.page.locator("[data-live-context] > summary").click()
        self.page.route("**/api/chats/*/context/", lambda route: route.abort("failed"))
        self.page.locator("#chat-locality").fill("Berlin")
        self.page.get_by_role("button", name="Save locality", exact=True).click()
        expect(self.page.locator("#chat-status")).to_contain_text("could not be confirmed")
        with patch("chats.provider.complete") as model:
            self.send("Do not send with uncertain context.")
            expect(self.page.locator("#chat-status")).to_contain_text("Refresh the page")
            model.assert_not_called()
