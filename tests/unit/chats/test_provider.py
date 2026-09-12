import json
from copy import deepcopy
from unittest.mock import patch

from django.test import SimpleTestCase, override_settings

from chats import provider
from chats.contracts import INTAKE_SCHEMA
from chats.errors import ChatError
from chats.transport import Budget

from .fixtures import LIVE_SETTINGS, intake


@override_settings(**LIVE_SETTINGS)
class ProviderTests(SimpleTestCase):
    def result(self):
        return {
            "_anymize": {"anonymized": True},
            "choices": [{"finish_reason": "stop", "message": {"content": json.dumps(intake())}}],
        }

    def call(self, budget=None):
        return provider.complete(
            messages=[{"role": "user", "content": "Fictional data"}],
            schema=INTAKE_SCHEMA,
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
        for modification in (
            {"finish_reason": "length"},
            {"message": {"content": "broken private json"}},
            {"message": {"content": "{}"}},
            {
                "message": {
                    "content": json.dumps(intake()),
                    "tool_calls": [{"name": "fetch_secret"}],
                }
            },
        ):
            response = deepcopy(base)
            response["choices"][0].update(modification)
            bad.append(response)
        for response in bad:
            with (
                self.subTest(response=response),
                patch("chats.provider.transport.request_json", return_value=response),
            ):
                with self.assertRaises(ChatError) as error:
                    self.call()
                self.assertEqual(str(error.exception), "invalid_reply")

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
