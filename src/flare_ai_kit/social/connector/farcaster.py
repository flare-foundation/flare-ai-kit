"""Farcaster Connector for Flare AI Kit."""

import os
from typing import Any

import httpx

from flare_ai_kit.social.connector import SocialConnector


class FarcasterConnector(SocialConnector):
    """Farcaster Connector for Flare AI Kit."""

    def __init__(self, client: httpx.AsyncClient | None = None) -> None:
        self.api_key = os.getenv("SOCIAL__FARCASTER_API_KEY")
        self.endpoint = "https://api.neynar.com/v2/farcaster/feed/search"
        self.client = client or httpx.AsyncClient()

    @property
    def platform(self) -> str:
        """Return the platform name."""
        return "farcaster"

    async def fetch_mentions(self, query: str, limit: int = 10) -> list[dict[str, Any]]:
        """Fetch mentions from Farcaster based on a query."""
        if not self.api_key:
            return []

        try:
            response = await self.client.get(
                self.endpoint,
                params={"text": query, "limit": limit},
                headers={"api_key": self.api_key},
            )
            response.raise_for_status()
            json_data = response.json()  # Already a dict in httpx
            casts = json_data.get("casts", [])

            return [
                {
                    "platform": self.platform,
                    "content": cast.get("text", ""),
                    "author_id": cast.get("author", {}).get("fid", ""),
                    "timestamp": cast.get("timestamp", ""),
                }
                for cast in casts
            ]
        except httpx.HTTPError:
            return []
