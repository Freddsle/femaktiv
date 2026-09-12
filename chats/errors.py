"""Safe, translated errors. Never expose provider exception text."""

from django.utils.translation import gettext_lazy as _

MESSAGES = {
    "not_configured": _(
        "Live AI is not configured. Ask the prototype operator to check the server settings."
    ),
    "provider_unavailable": _("The AI service is unavailable. Your draft is still here."),
    "privacy_failed": _("The service did not confirm anonymization. No answer was accepted."),
    "invalid_reply": _("The AI reply could not be verified. Your draft is still here."),
    "deadline_exceeded": _("This request timed out. It will not be retried automatically."),
    "context_too_large": _(
        "This AI context is too long. Remove a note or reset the AI context before trying again."
    ),
    "context_changed": _(
        "The chat context changed. The old reply was discarded; review your draft and send again."
    ),
    "chat_busy": _("Another reply is being prepared in this chat. Please wait for it to finish."),
    "account_busy": _(
        "Another reply is being prepared for your account. Please wait for it to finish."
    ),
    "live_access_denied": _(
        "Live chat is available only to approved testers. Ask the prototype operator for access."
    ),
    "rate_limited": _("This prototype's request limit has been reached. Please try again later."),
    "note_limit": _("A chat can use up to five active notes. Remove one before attaching another."),
    "not_found": _("This chat or note is not available."),
    "request_conflict": _(
        "This request was already used for another message. Refresh and try again."
    ),
    "invalid_context": _("The context update is invalid. Refresh the page and try again."),
    "network_disabled": _("External services are disabled during automated checks."),
    "unsafe_url": _("This source could not be opened safely."),
}

FAILURE_REASONS = frozenset(
    {
        "http_error",
        "connection_error",
        "dns_error",
        "invalid_json",
        "unsupported_encoding",
        "response_too_large",
        "timeout",
        "completion_truncated",
        "unexpected_completion",
        "unexpected_tool_call",
        "invalid_message",
        "invalid_model_json",
        "schema_validation",
        "invalid_prose",
        "empty_prose",
        "inconsistent_intake",
    }
)
VALIDATION_RULES = frozenset(
    {
        "type",
        "enum",
        "required",
        "additionalProperties",
        "minLength",
        "maxLength",
        "minItems",
        "maxItems",
        "uniqueItems",
    }
)


class ChatError(Exception):
    def __init__(
        self,
        code,
        status=502,
        *,
        provider_http_status=None,
        failure_reason=None,
        validation_rule=None,
    ):
        self.code = code if code in MESSAGES else "provider_unavailable"
        self.status = status
        # Only content-free, application-defined diagnostics may reach evaluation reports.
        self.provider_http_status = (
            provider_http_status
            if type(provider_http_status) is int and 100 <= provider_http_status <= 599
            else None
        )
        self.failure_reason = (
            failure_reason
            if type(failure_reason) is str and failure_reason in FAILURE_REASONS
            else None
        )
        self.validation_rule = (
            validation_rule
            if type(validation_rule) is str and validation_rule in VALIDATION_RULES
            else None
        )
        super().__init__(self.code)

    @property
    def message(self):
        return str(MESSAGES[self.code])
