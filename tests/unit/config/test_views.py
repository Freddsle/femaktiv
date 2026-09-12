from django.test import TestCase


class LanguageEntryTests(TestCase):
    def test_first_visit_ignores_browser_language(self):
        response = self.client.get("/", HTTP_ACCEPT_LANGUAGE="de-DE,de;q=0.9")
        self.assertRedirects(response, "/en/", fetch_redirect_response=False)

    def test_remembered_explicit_choice(self):
        self.client.cookies["femaktiv_language"] = "de"
        self.assertRedirects(self.client.get("/"), "/de/", fetch_redirect_response=False)

    def test_invalid_cookie_falls_back_to_english(self):
        self.client.cookies["femaktiv_language"] = "xx"
        self.assertRedirects(self.client.get("/"), "/en/", fetch_redirect_response=False)

    def test_health_is_non_billable_and_does_not_expose_configuration(self):
        self.assertEqual(
            self.client.get("/health/").json(),
            {"status": "ok", "mode": "placeholder", "version": "0.1.0"},
        )
