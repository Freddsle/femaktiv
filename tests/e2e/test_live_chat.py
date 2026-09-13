import json
from unittest.mock import patch

from django.test import LiveServerTestCase, override_settings
from playwright.sync_api import expect

from chats.errors import ChatError
from chats.models import ActiveNote, Chat, Message
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

    def scroll_to_latest(self):
        selector = (
            ".chat-scroll-area" if self.page.viewport_size["width"] <= 700 else "#chat-thread"
        )
        self.page.locator(selector).evaluate(
            "node => { node.style.scrollBehavior = 'auto'; node.scrollTop = node.scrollHeight; }"
        )

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
            expect(self.page.locator(".urgent-help")).to_have_count(0)
            expect(self.page.locator(".paragraph-citations a")).to_have_attribute(
                "href",
                "https://www.dge.de/gesunde-ernaehrung/gut-essen-und-trinken/dge-empfehlungen/",
            )
            expect(self.page.locator("[data-active-count]")).to_have_text("1")
            expect(self.page.locator(".chat-mode-notice")).to_contain_text(
                "This prototype uses AI."
            )
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
                    self.scroll_to_latest()
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
            expect(self.page.locator(".urgent-help")).to_have_count(0)
            expect(self.page.locator(".paragraph-citations a").first).to_have_attribute(
                "rel", "noopener noreferrer"
            )

    def test_urgent_help_both_locales_sizes_dynamic_saved_and_phone_links(self):
        with patch("chats.provider.complete", return_value=intake(decision="urgent")) as model:
            self.login()
            for language, heading in (
                ("en", "If you are in Germany"),
                ("de", "Wenn du in Deutschland bist"),
            ):
                self.page.set_viewport_size({"width": 1440, "height": 1000})
                self.goto("/en/chats/")
                self.new_chat()
                path = self.page.url.removeprefix(self.live_server_url)
                if language == "de":
                    self.goto(path.replace("/en/", "/de/"))
                for count, (width, size) in enumerate(
                    ((390, "mobile"), (1440, "desktop")), start=1
                ):
                    self.page.set_viewport_size(
                        {"width": width, "height": 1000 if width > 400 else 844}
                    )
                    self.send(
                        "Meine Mutter ist gestürzt und hat sich am Kopf verletzt."
                        if language == "de"
                        else "My mum fell and hurt her head."
                    )
                    expect(self.page.locator(".message-assistant")).to_have_count(count)
                    panel = self.page.locator(".message-assistant").last.locator(".urgent-help")
                    expect(panel.get_by_role("heading")).to_have_text(heading)
                    for number in ("112", "116117"):
                        expect(
                            panel.get_by_role("link", name=number, exact=True)
                        ).to_have_attribute("href", f"tel:{number}")
                    for index, url in enumerate(
                        (
                            "https://gesund.bund.de/notfallnummern",
                            "https://www.116117.de/de/englisch.php",
                        )
                    ):
                        source = panel.locator(".urgent-help-source").nth(index)
                        expect(source).to_have_attribute("href", url)
                        expect(source).to_have_attribute("target", "_blank")
                        expect(source).to_have_attribute("rel", "noopener noreferrer")
                    saved_text = panel.inner_text()
                    self.no_overflow()
                    self.scroll_to_latest()
                    self.page.screenshot(
                        path=str(self.screenshot_dir / f"live-urgent-help-{language}-{size}.png"),
                        full_page=True,
                    )
                    self.page.reload()
                    expect(panel).to_have_text(saved_text, use_inner_text=True)
                    expect(panel.locator(".urgent-help-number").first).to_have_attribute(
                        "href", "tel:112"
                    )
                    # Prevent dialing, after the application's document click handler runs.
                    # Activating a phone link must leave the next chat submission usable.
                    self.page.evaluate("""() => {
                        document.addEventListener('click', event => {
                            if (event.target.closest('a[href^="tel:"]')) event.preventDefault();
                        });
                    }""")
                    panel.locator(".urgent-help-number").first.focus()
                    self.page.keyboard.press("Enter")
                self.page.get_by_role(
                    "button", name="Deutsch" if language == "en" else "English", exact=True
                ).click()
                self.page.wait_for_url(f"**/{'de' if language == 'en' else 'en'}/chats/*/")
                expect(panel).to_have_text(saved_text, use_inner_text=True)
                expect(panel.get_by_role("heading")).to_have_text(heading)
            self.assertEqual(model.call_count, 4)

    def test_save_mothers_information_to_notes_both_locales_and_sizes(self):
        self.login()
        for language, report, request, title, body, confirmation, notes_label in (
            (
                "en",
                "My mum fell and hurt her skull, does she need to go to the hospital?",
                "Please save this info in my notes, its about my mother.",
                "Mother — fall",
                "My mother fell and hurt her skull. I asked whether she needs hospital assessment.",
                "Your note has been saved.",
                "My notes",
            ),
            (
                "de",
                "Meine Mutter ist gestürzt und hat sich am Kopf verletzt. Muss sie ins Krankenhaus?",
                "Bitte speichere das in meinen Notizen. Es geht um meine Mutter.",
                "Mutter — Sturz",
                "Meine Mutter ist gestürzt und hat sich am Kopf verletzt. Ich habe gefragt, ob sie ins Krankenhaus muss.",
                "Deine Notiz wurde gespeichert.",
                "Meine Notizen",
            ),
        ):
            for width, size in ((390, "mobile"), (1440, "desktop")):
                with self.subTest(language=language, width=width):
                    self.page.set_viewport_size({"width": 1440, "height": 1000})
                    self.goto("/en/chats/")
                    self.new_chat()
                    path = self.page.url.removeprefix(self.live_server_url)
                    path = path.replace("/en/", f"/{language}/")
                    self.goto(path)
                    self.page.set_viewport_size(
                        {"width": width, "height": 1000 if width > 400 else 844}
                    )
                    initial_count = self.database_value(PersonalNote.objects.count)
                    with patch(
                        "chats.provider.complete",
                        side_effect=[
                            intake(decision="urgent", topic="care", facts=[report]),
                            intake(
                                decision="save_note",
                                topic="care",
                                facts=[report],
                                evidence_topics=[],
                                note_action={"action": "create", "title": title, "body": body},
                            ),
                        ],
                    ) as model:
                        self.send(report)
                        expect(self.page.locator(".message-assistant")).to_have_count(1)
                        self.assertEqual(
                            self.database_value(PersonalNote.objects.count), initial_count
                        )
                        self.send(request)
                        expect(self.page.locator(".message-assistant")).to_have_count(2)
                        saved_reply = self.page.locator(".message-assistant").last
                        expect(saved_reply).to_contain_text(confirmation)
                        expect(saved_reply.locator(".urgent-help")).to_have_count(0)
                        self.assertEqual(model.call_count, 2)
                        self.assertEqual(
                            self.database_value(PersonalNote.objects.count), initial_count + 1
                        )
                    note = self.database_value(lambda: PersonalNote.objects.latest("created_at"))
                    self.assertEqual(note.owner_id, self.user.pk)
                    self.assertEqual(note.body, body)
                    note_path = f"/{language}/notes/{note.pk}/edit/"
                    saved_link = saved_reply.locator(".message-saved-note a")
                    expect(saved_link).to_have_text(f"{notes_label} · {title}")
                    expect(saved_link).to_have_js_property("href", self.live_server_url + note_path)
                    expect(self.page.locator("[data-active-count]")).to_have_text("0")
                    self.page.locator(".note-picker > summary").click()
                    checkbox = self.page.locator(f'input[name="note_ids"][value="{note.pk}"]')
                    expect(checkbox).to_be_visible()
                    expect(checkbox).not_to_be_checked()
                    self.page.locator(".note-picker > summary").click()
                    self.no_overflow()
                    self.scroll_to_latest()
                    self.page.screenshot(
                        path=str(self.screenshot_dir / f"live-saved-note-{language}-{size}.png"),
                        full_page=True,
                    )
                    self.page.reload()
                    expect(saved_reply).to_contain_text(confirmation)
                    expect(saved_link).to_have_js_property("href", self.live_server_url + note_path)
                    saved_link.focus()
                    self.page.keyboard.press("Enter")
                    self.page.wait_for_url(f"**{note_path}")
                    expect(self.page.locator("#id_title")).to_have_value(title)
                    expect(self.page.locator("#id_body")).to_have_value(body)
                    self.no_overflow()
                    self.goto(f"/{language}/notes/")
                    expect(self.page.locator("h1")).to_have_text(notes_label)
                    note_card = self.page.locator(".note-card").filter(
                        has=self.page.locator(f'h2 a[href="{note_path}"]')
                    )
                    expect(note_card).to_contain_text(body)
                    self.page.reload()
                    expect(note_card).to_contain_text(body)
                    self.no_overflow()

    def test_care_cited_guidance_and_call_preparation_without_local_lookup(self):
        def model(**kwargs):
            return (
                intake(topic="care", evidence_topics=["discharge"])
                if kwargs["name"] == "femaktiv_intake"
                else answer(kwargs["language"], care=True)
            )

        with patch("chats.provider.complete", side_effect=model):
            self.login()
            self.new_chat()
            expect(self.page.locator("#chat-locality")).to_have_count(0)
            expect(self.page.locator("[data-live-context]")).not_to_contain_text("Brave")
            self.send(
                "My older mother is in hospital after a broken leg. Help arrange care and a German call."
            )
            expect(self.page.locator(".message")).to_have_count(2)
            expect(self.page.locator(".message-assistant").last).to_contain_text(
                "Welche Unterstützung"
            )
            expect(self.page.locator(".paragraph-citations a")).to_have_attribute(
                "href", "https://gesund.bund.de/en/entlassung-aus-dem-krankenhaus"
            )
            expect(self.page.locator(".source-card[open]")).to_have_count(0)
            self.page.set_viewport_size({"width": 390, "height": 844})
            self.no_overflow()
            self.scroll_to_latest()
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
            expect(self.page.locator(".paragraph-citations a").last).to_have_attribute(
                "href", "https://gesund.bund.de/en/entlassung-aus-dem-krankenhaus"
            )
            expect(self.page.locator(".source-card[open]")).to_have_count(0)
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
        self.page.get_by_role("button", name="Reset message context", exact=True).click()
        expect(self.page.locator("#chat-status")).to_contain_text("could not be confirmed")
        with patch("chats.provider.complete") as model:
            self.send("Do not send with uncertain context.")
            expect(self.page.locator("#chat-status")).to_contain_text("Refresh the page")
            model.assert_not_called()
