import io
import json
import os
from tempfile import TemporaryDirectory
from unittest.mock import patch

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import SimpleTestCase, override_settings

from chats.service import ChatReply
from tests.unit.chats.fixtures import LIVE_SETTINGS


@override_settings(**LIVE_SETTINGS)
class LiveEvaluationTests(SimpleTestCase):
    def test_requires_explicit_flag_and_honours_offline_guard(self):
        with patch("chats.provider.available_models") as models:
            with self.assertRaises(CommandError):
                call_command("evaluate_live_chat", stdout=io.StringIO())
            with (
                patch.dict(os.environ, {"FEMAKTIV_OFFLINE_CHECKS": "1"}),
                self.assertRaises(CommandError),
            ):
                call_command("evaluate_live_chat", allow_provider_calls=True, stdout=io.StringIO())
            models.assert_not_called()

    def test_missing_essential_facts_fails_and_never_retries(self):
        def generated(**kwargs):
            kwargs["intake_observer"]({"facts": ["Fifteen minutes, but important allergy lost"]})
            return ChatReply("Fictional answer", "live", citations=[{"id": "dge-food"}])

        with (
            TemporaryDirectory() as directory,
            patch.dict(os.environ, {"FEMAKTIV_OFFLINE_CHECKS": "0"}),
            patch("chats.provider.available_models", return_value={"fictional-model"}),
            patch("chats.service.generate_reply", side_effect=generated) as model,
        ):
            output = directory + "/report.json"
            with self.assertRaises(CommandError):
                call_command(
                    "evaluate_live_chat",
                    allow_provider_calls=True,
                    output=output,
                    stdout=io.StringIO(),
                )
            with open(output) as stream:
                report = json.load(stream)
            self.assertFalse(report["passed"])
            self.assertFalse(report["cases"][0]["essential_facts"])
            self.assertEqual(model.call_count, 1)
