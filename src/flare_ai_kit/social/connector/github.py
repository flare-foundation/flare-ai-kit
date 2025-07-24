"""GitHub Connector for Flare AI Kit."""

from typing import Any

import httpx

from flare_ai_kit.config import AppSettings
from flare_ai_kit.social.connector import SocialConnector


class GitHubConnector(SocialConnector):
    """GitHub Connector for Flare AI Kit."""

    def __init__(self) -> None:
        """Initialize the GitHubConnector with API token and repository."""
        settings = AppSettings().social
        self.token = (
            settings.github_token.get_secret_value() if settings.github_token else ""
        )
        self.repo = (
            settings.github_repo.get_secret_value() if settings.github_repo else ""
        )
        self.client = httpx.AsyncClient()
        self.endpoint = f"https://api.github.com/repos/{self.repo}/issues/comments"

    @property
    def platform(self) -> str:
        """Return the platform name."""
        return "github"

    async def fetch_mentions(self, query: str, limit: int = 10) -> list[dict[str, Any]]:
        """Fetch issue comments containing the query."""
        try:
            response = await self.client.get(
                self.endpoint,
                headers={"Authorization": f"Bearer {self.token}"},
                params={"per_page": limit},
            )
            response.raise_for_status()
            comments = await response.json()

            return [
                {
                    "platform": self.platform,
                    "content": comment.get("body", ""),
                    "author_id": comment.get("user", {}).get("login", ""),
                    "timestamp": comment.get("created_at", ""),
                }
                for comment in comments
                if query.lower() in comment.get("body", "").lower()
            ]
        except httpx.HTTPError:
            return []
