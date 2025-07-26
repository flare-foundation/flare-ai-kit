"""Farcaster Connector for Flare AI Kit."""

from typing import Any

import httpx

from flare_ai_kit.config import AppSettings
from flare_ai_kit.social.connector import SocialConnector


class FarcasterConnector(SocialConnector):
    """Farcaster Connector for Flare AI Kit."""

    def __init__(self, client: httpx.AsyncClient | None = None) -> None:
        """Initialize the FarcasterConnector with API key."""
        settings = AppSettings().social
        self.api_key = (
            settings.farcaster_api_key.get_secret_value()
            if settings.farcaster_api_key
            else ""
        )
        self.signer_uuid = (
            settings.farcaster_signer_uuid.get_secret_value()
            if settings.farcaster_signer_uuid
            else ""
        )
        self.fid = (
            settings.farcaster_fid.get_secret_value() if settings.farcaster_fid else ""
        )
        self.api_url = (
            settings.farcaster_api_url.get_secret_value()
            if settings.farcaster_api_url
            else ""
        )
        self.endpoint = f"{self.api_url}/v2/farcaster/feed/search"
        self.client = client or httpx.AsyncClient()

    @property
    def platform(self) -> str:
        """Return the platform name."""
        return "farcaster"

    async def fetch_mentions(self, query: str, limit: int = 10) -> list[dict[str, Any]]:
        """Fetch mentions from Farcaster based on a query."""
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

    async def post_message(self, content: str) -> dict[str, Any]:
        """Post a message to Farcaster."""
        try:
            response = await self.client.post(
                f"{self.api_url}/v2/casts",
                headers={
                    "Content-Type": "application/json",
                    "x-api-key": self.api_key,
                },
                json={
                    "text": content,
                    "signer_uuid": self.signer_uuid,
                },
            )
            response.raise_for_status()

        except httpx.HTTPError as e:
            return {"error": str(e)}
        else:
            return {
                "platform": "farcaster",
                "content": content,
            }
