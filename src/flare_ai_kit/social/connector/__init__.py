from abc import ABC, abstractmethod
from typing import Any


class SocialConnector(ABC):
    """Abstract base class for all social platform connectors."""

    @abstractmethod
    def __init__(self) -> None:
        """Initialize connector (optional for future shared setup)."""

    @property
    @abstractmethod
    def platform(self) -> str:
        """The name of the platform (e.g., 'x', 'github', 'discord')."""

    @abstractmethod
    async def fetch_mentions(self, query: str) -> list[dict[str, Any]]:
        """
        Fetch public mentions or messages related to a given query.

        Returns a list of dictionaries with at least.
            - platform
            - content
            - author_id
            - timestamp
        """
