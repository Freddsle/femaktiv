import io
import json
import os
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import SimpleTestCase, override_settings

from chats.service import ChatReply
from tests.unit.chats.fixtures import LIVE_SETTINGS
from tests.unit.chats.test_masking_evaluation import fictional_export


@override_settings(**LIVE_SETTINGS)
class LiveEvaluationTests(SimpleTestCase):
    def success(self, **kwargs):
        kwargs["intake_observer"](
            {
                "facts": [
                    "Hypertension, milk protein allergy, fifteen minutes, mother, broken leg, alone, stairs"
                ]
            }
        )
        return ChatReply(
            "Fictional answer", "live", citations=[{"id": "dge-food"}], lookup_status="verified"
        )

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

    def test_export_inputs_and_masking_only_are_offline_without_configuration(self):
        with (
            TemporaryDirectory() as directory,
            override_settings(FEMAKTIV_AI_MODE="placeholder", ANYMIZE_API_KEY=""),
            patch.dict(os.environ, {"FEMAKTIV_OFFLINE_CHECKS": "1"}),
            patch("chats.provider.available_models") as models,
            patch("chats.service.generate_reply") as model,
        ):
            inputs = Path(directory) / "inputs.json"
            call_command(
                "evaluate_live_chat", export_masking_cases=str(inputs), stdout=io.StringIO()
            )
            self.assertTrue(json.loads(inputs.read_text())["fictional_only"])
            exported = Path(directory) / "export.json"
            exported.write_text(json.dumps(fictional_export()))
            report = Path(directory) / "report.json"
            call_command(
                "evaluate_live_chat",
                masking_only=True,
                masking_output=str(exported),
                output=str(report),
                stdout=io.StringIO(),
            )
            saved = json.loads(report.read_text())
            self.assertTrue(saved["masking"]["passed"])
            self.assertNotIn("integration_passed", saved)
            models.assert_not_called()
            model.assert_not_called()

    def test_live_checks_can_pass_while_masking_is_explicitly_incomplete(self):
        with (
            TemporaryDirectory() as directory,
            patch.dict(os.environ, {"FEMAKTIV_OFFLINE_CHECKS": "0"}),
            patch("chats.provider.available_models", return_value={"fictional-model"}),
            patch("chats.service.generate_reply", side_effect=self.success) as model,
        ):
            report = Path(directory) / "report.json"
            call_command(
                "evaluate_live_chat",
                allow_provider_calls=True,
                output=str(report),
                stdout=io.StringIO(),
            )
            saved = json.loads(report.read_text())
            self.assertTrue(saved["integration_passed"])
            self.assertTrue(saved["passed"])
            self.assertEqual(saved["masking"]["status"], "not_evaluated")
            self.assertEqual(model.call_count, 4)

    def test_combined_checks_require_actual_export_and_live_checks(self):
        with (
            TemporaryDirectory() as directory,
            patch.dict(os.environ, {"FEMAKTIV_OFFLINE_CHECKS": "0"}),
            patch("chats.provider.available_models", return_value={"fictional-model"}),
            patch("chats.service.generate_reply", side_effect=self.success),
        ):
            exported = Path(directory) / "export.json"
            exported.write_text(json.dumps(fictional_export()))
            report = Path(directory) / "report.json"
            call_command(
                "evaluate_live_chat",
                allow_provider_calls=True,
                masking_output=str(exported),
                output=str(report),
                stdout=io.StringIO(),
            )
            saved = json.loads(report.read_text())
            self.assertTrue(saved["integration_passed"])
            self.assertTrue(saved["masking"]["passed"])
            self.assertTrue(saved["passed"])

    def test_malformed_or_private_export_fails_without_network_or_content_output(self):
        with (
            TemporaryDirectory() as directory,
            patch.dict(os.environ, {"FEMAKTIV_OFFLINE_CHECKS": "0"}),
            patch("chats.provider.available_models") as models,
        ):
            exported = Path(directory) / "export.json"
            for content in ("private-error-detail", "[]", "x" * 64_001):
                with self.subTest(length=len(content)):
                    exported.write_text(content)
                    output = io.StringIO()
                    with self.assertRaises(CommandError) as error:
                        call_command(
                            "evaluate_live_chat",
                            allow_provider_calls=True,
                            masking_output=str(exported),
                            output=str(Path(directory) / "report.json"),
                            stdout=output,
                        )
                    self.assertNotIn(
                        "private-error-detail", str(error.exception) + output.getvalue()
                    )
            models.assert_not_called()

    def test_masking_only_failure_reports_category_and_does_not_invoke_model(self):
        with TemporaryDirectory() as directory, patch("chats.provider.available_models") as models:
            exported = Path(directory) / "export.json"
            exported.write_text(json.dumps(fictional_export(unmasked_category="legal_case_number")))
            report = Path(directory) / "report.json"
            with self.assertRaises(CommandError):
                call_command(
                    "evaluate_live_chat",
                    masking_only=True,
                    masking_output=str(exported),
                    output=str(report),
                    stdout=io.StringIO(),
                )
            saved = json.loads(report.read_text())
            self.assertFalse(saved["masking"]["passed"])
            self.assertFalse(
                saved["masking"]["cases"][0]["identifier_removal"]["legal_case_number"]
            )
            models.assert_not_called()

    def test_missing_masking_artifact_and_mixed_export_modes_are_rejected(self):
        with patch("chats.provider.available_models") as models:
            for arguments in (
                {"masking_only": True},
                {"masking_only": True, "masking_output": "/does-not-exist/fictional.json"},
                {"export_masking_cases": "unused.json", "allow_provider_calls": True},
            ):
                with self.subTest(arguments=arguments), self.assertRaises(CommandError):
                    call_command("evaluate_live_chat", stdout=io.StringIO(), **arguments)
            models.assert_not_called()
