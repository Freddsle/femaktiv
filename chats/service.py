"""Replace only this reply boundary when a real LLM is deliberately connected."""

from dataclasses import dataclass
from typing import Sequence

from django.utils import translation
from django.utils.translation import gettext as _


@dataclass(frozen=True)
class ContextNote:
    title: str
    body: str


@dataclass(frozen=True)
class ChatReply:
    content: str
    mode: str = "placeholder"


def generate_reply(
    *, history: Sequence, context: Sequence[ContextNote], language: str
) -> ChatReply:
    """A deterministic, non-network adapter. Do not infer advice from the inputs."""
    with translation.override(language):
        return ChatReply(
            _(
                "Your message has been saved. AI replies are not connected yet. You can continue adding thoughts, attach your notes, or explore an example conversation."
            )
        )
