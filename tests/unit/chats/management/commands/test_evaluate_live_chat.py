import io
import json
import os
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import SimpleTestCase, override_settings

from chats.errors import ChatError
from chats.service import ChatReply
from tests.unit.chats.fixtures import LIVE_SETTINGS, intake
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
        return ChatReply("Fictional answer", "live", citations=[{"id": "dge-food"}])

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

    def test_provider_failure_reports_safe_status_and_stage_without_retry(self):
        for stage in ("intake", "composition"):

            def generated(**kwargs):
                if stage == "composition":
                    kwargs["intake_observer"]({"facts": ["Fictional intake"]})
                raise ChatError(
                    "provider_unavailable", provider_http_status=400, failure_reason="http_error"
                )

            with (
                self.subTest(stage=stage),
                TemporaryDirectory() as directory,
                patch.dict(os.environ, {"FEMAKTIV_OFFLINE_CHECKS": "0"}),
                patch("chats.provider.available_models", return_value={"fictional-model"}),
                patch("chats.service.generate_reply", side_effect=generated) as model,
            ):
                output = Path(directory) / "report.json"
                with self.assertRaises(CommandError) as raised:
                    call_command(
                        "evaluate_live_chat",
                        allow_provider_calls=True,
                        output=str(output),
                        stdout=io.StringIO(),
                    )
                report = json.loads(output.read_text())
                case = report["cases"][0]
                self.assertEqual(case["failure_stage"], stage)
                self.assertEqual(case["provider_http_status"], 400)
                self.assertEqual(case["failure_reason"], "http_error")
                self.assertEqual(model.call_count, 1)
            self.assertIn("nutrition-en", str(raised.exception))
            self.assertIn("provider HTTP 400", str(raised.exception))
            self.assertIn("JSON-schema", str(raised.exception))

    def test_model_access_failure_keeps_actual_provider_status(self):
        with (
            TemporaryDirectory() as directory,
            patch.dict(os.environ, {"FEMAKTIV_OFFLINE_CHECKS": "0"}),
            patch(
                "chats.provider.available_models",
                side_effect=ChatError(
                    "provider_unavailable", provider_http_status=403, failure_reason="http_error"
                ),
            ) as models,
            patch("chats.service.generate_reply") as model,
        ):
            output = Path(directory) / "report.json"
            with self.assertRaises(CommandError) as raised:
                call_command(
                    "evaluate_live_chat",
                    allow_provider_calls=True,
                    output=str(output),
                    stdout=io.StringIO(),
                )
            report = json.loads(output.read_text())
            self.assertEqual(report["failure_stage"], "model_access")
            self.assertEqual(report["provider_http_status"], 403)
            self.assertEqual(report["cases"], [])
            self.assertIn("API-key permissions", str(raised.exception))
            models.assert_called_once()
            model.assert_not_called()

    def test_rejected_intake_is_not_reported_as_composition(self):
        for response in (
            intake(intro="Visit https://untrusted.example.test"),
            intake(decision="clarification", questions=[]),
            intake(decision="answer", questions=["Which meal?"]),
        ):
            with (
                self.subTest(response=response),
                TemporaryDirectory() as directory,
                patch.dict(os.environ, {"FEMAKTIV_OFFLINE_CHECKS": "0"}),
                patch("chats.provider.available_models", return_value={"fictional-model"}),
                patch("chats.provider.complete", return_value=response) as model,
            ):
                output = Path(directory) / "report.json"
                with self.assertRaises(CommandError) as raised:
                    call_command(
                        "evaluate_live_chat",
                        allow_provider_calls=True,
                        output=str(output),
                        stdout=io.StringIO(),
                    )
                case = json.loads(output.read_text())["cases"][0]
                self.assertEqual(case["failure_stage"], "intake")
                self.assertEqual(case["error_code"], "invalid_reply")
                self.assertIn("intake", str(raised.exception))
                model.assert_called_once()

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
            self.assertEqual(report["cases"][0]["failure_stage"], "scenario_checks")
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
            for invocation in model.call_args_list:
                self.assertNotIn("locality", invocation.kwargs)
            for case in saved["cases"]:
                self.assertNotIn("lookup_status", case)

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
