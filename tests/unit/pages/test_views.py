import json

from django.conf import settings
from django.test import TestCase


class PublicPagesTests(TestCase):
    def test_public_pages_are_available_in_both_languages(self):
        for language in ("en", "de"):
            for path in ("", "community/", "examples/my-wellbeing/", "examples/family-care/"):
                with self.subTest(language=language, path=path):
                    response = self.client.get(f"/{language}/{path}")
                    self.assertEqual(response.status_code, 200)
                    self.assertContains(response, f'<html lang="{language}">')
                    self.assertNotContains(response, "FemAktiv")

    def test_six_examples_have_matching_translated_identifiers(self):
        data = json.loads((settings.BASE_DIR / "content/examples.json").read_text())
        for group in ("topics", "questions", "conversations"):
            self.assertEqual(
                [r["slug"] for r in data["en"][group]], [r["slug"] for r in data["de"][group]]
            )
        self.assertEqual(len(data["en"]["questions"]), 6)
        for item in data["en"]["questions"]:
            self.assertEqual(self.client.get(f"/en/community/{item['slug']}/").status_code, 200)

    def test_topics_filter_example_content(self):
        response = self.client.get("/en/community/?topic=family-care")
        self.assertEqual(len(response.context["questions"]), 2)
        self.assertTrue(all(q["topic"] == "family-care" for q in response.context["questions"]))

    def test_unknown_examples_are_not_fabricated(self):
        self.assertEqual(self.client.get("/en/community/not-a-question/").status_code, 404)
        self.assertEqual(self.client.get("/en/examples/not-an-example/").status_code, 404)

    def test_explicit_language_switch_keeps_current_page_and_sets_cookie(self):
        response = self.client.post(
            "/language/", {"language": "de", "next": "/en/examples/family-care/"}
        )
        self.assertRedirects(response, "/de/examples/family-care/", fetch_redirect_response=False)
        self.assertEqual(response.cookies["femaktiv_language"].value, "de")

    def test_language_switch_cannot_redirect_off_site(self):
        response = self.client.post(
            "/language/", {"language": "de", "next": "https://untrusted.example/"}
        )
        self.assertNotIn("untrusted.example", response.headers["Location"])

    def test_language_switch_uses_page_locale_despite_browser_or_stale_cookie(self):
        self.client.cookies[settings.LANGUAGE_COOKIE_NAME] = "de"
        response = self.client.post(
            "/language/", {"language": "de", "next": "/en/"}, HTTP_ACCEPT_LANGUAGE="de-DE"
        )
        self.assertEqual(response.headers["Location"], "/de/")
        self.client.cookies[settings.LANGUAGE_COOKIE_NAME] = "en"
        response = self.client.post(
            "/language/", {"language": "en", "next": "/de/community/?topic=family-care"}
        )
        self.assertEqual(response.headers["Location"], "/en/community/?topic=family-care")
