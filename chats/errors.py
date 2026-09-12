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
    "invalid_locality": _(
        "Enter a German city or a five-digit postcode, without a street address."
    ),
    "note_limit": _("A chat can use up to five active notes. Remove one before attaching another."),
    "not_found": _("This chat or note is not available."),
    "request_conflict": _(
        "This request was already used for another message. Refresh and try again."
    ),
    "invalid_context": _("The context update is invalid. Refresh the page and try again."),
    "network_disabled": _("External services are disabled during automated checks."),
    "unsafe_url": _("This source could not be opened safely."),
    "search_unavailable": _("Local services could not be checked right now."),
}


class ChatError(Exception):
    def __init__(self, code, status=502):
        self.code = code if code in MESSAGES else "provider_unavailable"
        self.status = status
        super().__init__(self.code)

    @property
    def message(self):
        return str(MESSAGES[self.code])
