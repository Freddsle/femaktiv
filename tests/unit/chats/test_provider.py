import json
from copy import deepcopy
from unittest.mock import patch

from django.test import SimpleTestCase, override_settings
from jsonschema import Draft202012Validator

from chats import provider
from chats.contracts import INTAKE_SCHEMA, answer_schema, validate_prose
from chats.errors import ChatError
from chats.transport import Budget

from .fixtures import LIVE_SETTINGS, answer, intake


@override_settings(**LIVE_SETTINGS)
class ProviderTests(SimpleTestCase):
    def result(self, output=None):
        return {
            "_anymize": {"anonymized": True},
            "choices": [
                {
                    "finish_reason": "stop",
                    "message": {"content": json.dumps(intake() if output is None else output)},
                }
            ],
        }

    def call(self, budget=None, schema=INTAKE_SCHEMA):
        return provider.complete(
            messages=[{"role": "user", "content": "Fictional data"}],
            schema=schema,
            name="intake",
            language="de",
            budget=budget or Budget(),
        )

    def test_anymize_only_configuration_uses_anonymous_route_schema_and_no_fallback(self):
        with patch("chats.provider.transport.request_json", return_value=self.result()) as request:
            self.assertEqual(self.call(), intake())
        self.assertEqual(request.call_args.args[0], provider.ANONYMOUS_URL)
        payload = request.call_args.kwargs["payload"]
        self.assertFalse(payload["stream"])
        self.assertEqual(payload["model"], "fictional-model")
        self.assertEqual(payload["response_format"]["type"], "json_schema")
        self.assertNotIn("tools", payload)

    def test_intake_and_answer_wire_schemas_preserve_structure_and_original_constraints(self):
        expected_intake = deepcopy(INTAKE_SCHEMA)
        del expected_intake["properties"]["intro"]["minLength"]
        del expected_intake["properties"]["intro"]["maxLength"]
        for field in ("facts", "questions"):
            del expected_intake["properties"][field]["items"]["minLength"]
            del expected_intake["properties"][field]["items"]["maxLength"]
        del expected_intake["properties"]["evidence_topics"]["uniqueItems"]
        cases = [(INTAKE_SCHEMA, intake(), expected_intake)]
        for source_ids in (["dge-food", "bund-discharge"], []):
            schema = answer_schema(source_ids)
            expected = deepcopy(schema)
            paragraph = expected["properties"]["paragraphs"]["items"]["properties"]
            del paragraph["text"]["minLength"]
            del paragraph["text"]["maxLength"]
            del paragraph["source_ids"]["uniqueItems"]
            output = (
                answer()
                if source_ids
                else {
                    "paragraphs": [
                        {"text": "What would help?", "kind": "question", "source_ids": []}
                    ]
                }
            )
            cases.append((schema, output, expected))

        for schema, output, expected in cases:
            original = deepcopy(schema)
            with (
                self.subTest(schema=schema),
                patch(
                    "chats.provider.transport.request_json", return_value=self.result(output)
                ) as request,
            ):
                self.assertEqual(self.call(schema=schema), output)
            request.assert_called_once()
            supplied = request.call_args.kwargs["payload"]["response_format"]["json_schema"]
            self.assertTrue(supplied["strict"])
            self.assertEqual(supplied["schema"], expected)
            self.assertEqual(schema, original)

    def test_local_validation_still_rejects_wire_valid_lengths_and_duplicates(self):
        cases = [
            (INTAKE_SCHEMA, intake(facts=[""]), "minLength"),
            (INTAKE_SCHEMA, intake(intro="FICTIONAL_PRIVATE_INTRO" * 30), "maxLength"),
            (INTAKE_SCHEMA, intake(evidence_topics=["protein", "protein"]), "uniqueItems"),
        ]
        for text, source_ids, rule in (
            ("", ["dge-food"], "minLength"),
            ("x" * 1801, ["dge-food"], "maxLength"),
            ("Claim", ["dge-food", "dge-food"], "uniqueItems"),
        ):
            cases.append(
                (
                    answer_schema(["dge-food"]),
                    {
                        "paragraphs": [
                            {"text": text, "kind": "explanation", "source_ids": source_ids}
                        ]
                    },
                    rule,
                )
            )
        for schema, output, rule in cases:
            with (
                self.subTest(output=output),
                patch(
                    "chats.provider.transport.request_json", return_value=self.result(output)
                ) as request,
                self.assertRaises(ChatError) as rejected,
            ):
                self.call(schema=schema)
            self.assertEqual(rejected.exception.code, "invalid_reply")
            self.assertEqual(rejected.exception.failure_reason, "schema_validation")
            self.assertEqual(rejected.exception.validation_rule, rule)
            self.assertNotIn("FICTIONAL_PRIVATE", repr(vars(rejected.exception)))
            request.assert_called_once()
            sent_schema = request.call_args.kwargs["payload"]["response_format"]["json_schema"][
                "schema"
            ]
            self.assertTrue(Draft202012Validator(sent_schema).is_valid(output))
            self.assertFalse(Draft202012Validator(schema).is_valid(output))

    def test_metadata_must_confirm_anonymization_as_boolean(self):
        for metadata in (None, {}, {"anonymized": False}, {"anonymized": "true"}):
            response = self.result()
            response["_anymize"] = metadata
            with (
                self.subTest(metadata=metadata),
                patch("chats.provider.transport.request_json", return_value=response) as request,
            ):
                with self.assertRaises(ChatError) as error:
                    self.call()
                self.assertEqual(error.exception.code, "privacy_failed")
                self.assertEqual(request.call_count, 1)

    def test_malformed_truncated_tool_and_schema_outputs_are_rejected(self):
        base = self.result()
        bad = []
        for modification, reason in (
            ({"finish_reason": "length"}, "completion_truncated"),
            ({"finish_reason": "FICTIONAL_PRIVATE_FINISH_REASON"}, "unexpected_completion"),
            ({"message": None}, "invalid_message"),
            ({"message": {"content": []}}, "invalid_message"),
            ({"message": {"content": "x" * 24001}}, "invalid_message"),
            ({"message": {"content": "FICTIONAL_PRIVATE_JSON"}}, "invalid_model_json"),
            ({"message": {"content": "{}"}}, "schema_validation"),
            (
                {
                    "finish_reason": "tool_calls",
                    "message": {
                        "content": json.dumps(intake()),
                        "tool_calls": [{"name": "FICTIONAL_PRIVATE_TOOL"}],
                    },
                },
                "unexpected_tool_call",
            ),
        ):
            response = deepcopy(base)
            response["choices"][0].update(modification)
            bad.append((response, reason))
        for choices in (None, [], ["FICTIONAL_PRIVATE_CHOICE"]):
            response = deepcopy(base)
            response["choices"] = choices
            bad.append((response, "invalid_message"))
        for response, reason in bad:
            with (
                self.subTest(reason=reason),
                patch("chats.provider.transport.request_json", return_value=response) as request,
            ):
                with self.assertRaises(ChatError) as error:
                    self.call()
                self.assertEqual(str(error.exception), "invalid_reply")
                self.assertEqual(error.exception.failure_reason, reason)
                self.assertEqual(
                    error.exception.validation_rule,
                    "required" if reason == "schema_validation" else None,
                )
                self.assertNotIn("FICTIONAL_PRIVATE", repr(vars(error.exception)))
                request.assert_called_once()

    def test_prose_rejection_reports_only_empty_or_forbidden_reason(self):
        for prose, reason in (
            (" \n", "empty_prose"),
            ("FICTIONAL_PRIVATE@example.test", "invalid_prose"),
        ):
            with self.subTest(reason=reason), self.assertRaises(ChatError) as error:
                validate_prose(prose)
            self.assertEqual(error.exception.failure_reason, reason)
            self.assertNotIn("FICTIONAL_PRIVATE", repr(vars(error.exception)))

    def test_call_budget_and_provider_errors_never_retry(self):
        with patch("chats.provider.transport.request_json", return_value=self.result()) as request:
            budget = Budget()
            self.call(budget)
            self.call(budget)
            with self.assertRaises(ChatError):
                self.call(budget)
            self.assertEqual(request.call_count, 2)
        with patch(
            "chats.provider.transport.request_json", side_effect=ChatError("deadline_exceeded")
        ) as request:
            with self.assertRaises(ChatError):
                self.call()
            self.assertEqual(request.call_count, 1)

    def test_model_ids_are_read_from_account(self):
        with patch(
            "chats.provider.transport.request_json",
            return_value={"data": [{"id": "account-specific-model"}]},
        ) as request:
            self.assertEqual(provider.available_models(Budget()), {"account-specific-model"})
            self.assertEqual(request.call_args.args[0], provider.BASE_URL + "/models")

    def test_account_privacy_acknowledgements_are_required_before_network(self):
        for setting in ("ANYMIZE_ZDR_CONFIRMED", "ANYMIZE_FALLBACKS_DISABLED_CONFIRMED"):
            with (
                self.subTest(setting=setting),
                override_settings(**{setting: False}),
                patch("chats.provider.transport.request_json") as request,
                self.assertRaises(ChatError) as error,
            ):
                self.call()
            self.assertEqual(error.exception.code, "not_configured")
            request.assert_not_called()
