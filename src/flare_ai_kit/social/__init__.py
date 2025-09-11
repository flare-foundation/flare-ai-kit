"""Module providing clients for interacting with social media platforms."""

from typing import TYPE_CHECKING

from .settings import SocialSettings

if TYPE_CHECKING:
    from .telegram import TelegramClient
    from .x import XClient

__all__ = ["SocialSettings", "TelegramClient", "XClient"]


def __getattr__(name: str):
    """Lazy import for social components."""
    if name == "TelegramClient":
        from .telegram import TelegramClient

        return TelegramClient
    if name == "XClient":
        from .x import XClient

        return XClient
    msg = f"module '{__name__}' has no attribute '{name}'"
    raise AttributeError(msg)
