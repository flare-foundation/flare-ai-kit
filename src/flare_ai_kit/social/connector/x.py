"""Connector for Flare AI Kit."""

# pyright: reportMissingTypeStubs=false

from typing import Any, cast

from tweepy import API, OAuth1UserHandler
from tweepy.asynchronous import AsyncClient
from tweepy.errors import TweepyException

from flare_ai_kit.config import AppSettings
from flare_ai_kit.social.connector import SocialConnector


class XConnector(SocialConnector):
    """X (formerly Twitter) Connector for Flare AI Kit."""

    def __init__(self) -> None:
        """Initialize the XConnector with API keys and tokens."""
        settings = AppSettings().social
        self.bearer_token = (
            settings.x_api_key.get_secret_value() if settings.x_api_key else ""
        )

        self.client = AsyncClient(bearer_token=self.bearer_token)  # type: ignore[reportGeneralTypeIssues]

        self.auth = OAuth1UserHandler(
            settings.x_api_key.get_secret_value() if settings.x_api_key else "",
            settings.x_api_key_secret.get_secret_value()
            if settings.x_api_key_secret
            else "",
            settings.x_access_token.get_secret_value()
            if settings.x_access_token
            else "",
            settings.x_access_token_secret.get_secret_value()
            if settings.x_access_token_secret
            else "",
        )

        self.sync_client = API(self.auth)  # type: ignore[reportGeneralTypeIssues]

    @property
    def platform(self) -> str:
        """Return the platform name."""
        return "x"

    async def fetch_mentions(self, query: str, limit: int = 10) -> list[dict[str, Any]]:
        """Fetch recent tweets matching the query."""
        try:
            raw_response = await self.client.search_recent_tweets(  # type: ignore[reportGeneralTypeIssues]
                query=query,
                max_results=limit,
                tweet_fields=["created_at", "author_id"],
            )
            response = cast("Any", raw_response)
            tweets = cast("list[Any]", getattr(response, "data", []))

            return [
                {
                    "platform": self.platform,
                    "content": str(getattr(tweet, "text", "")),
                    "author_id": str(getattr(tweet, "author_id", "")),
                    "tweet_id": str(getattr(tweet, "id", "")),
                    "timestamp": (
                        tweet.created_at.isoformat()
                        if getattr(tweet, "created_at", None) is not None
                        else None
                    ),
                }
                for tweet in tweets
            ]

        except TweepyException:
            return []

    def post_tweet(self, content: str) -> dict[str, Any]:
        """Post a new tweet (synchronous)."""
        try:
            client: Any = self.sync_client
            tweet = client.update_status(status=content)
            return {
                "tweet_id": str(getattr(tweet, "id", "")),
                "content": str(getattr(tweet, "text", "")),
                "created_at": (
                    tweet.created_at.isoformat()
                    if getattr(tweet, "created_at", None) is not None
                    else None
                ),
            }
        except TweepyException:
            return {}

    def reply_to_tweet(self, tweet_id: int, reply_text: str) -> dict[str, Any]:
        """Reply to a tweet by ID."""
        try:
            client: Any = self.sync_client
            tweet = client.update_status(
                status=reply_text,
                in_reply_to_status_id=tweet_id,
                auto_populate_reply_metadata=True,
            )
            return {
                "reply_id": str(getattr(tweet, "id", "")),
                "content": str(getattr(tweet, "text", "")),
                "created_at": getattr(tweet, "created_at", ""),
            }
        except TweepyException:
            return {}
