""""X Connector for Flare AI Kit."""

import os

from dotenv import load_dotenv
from tweepy import API, OAuth1UserHandler
from tweepy.asynchronous import AsyncClient
from tweepy.errors import TweepyException

from flare_ai_kit.social.connector import SocialConnector

load_dotenv()


class XConnector(SocialConnector):
    """X (formerly Twitter) Connector for Flare AI Kit."""

    def __init__(self) -> None:
        self.bearer_token = os.getenv("SOCIAL__X_API_KEY")
        self.client = AsyncClient(bearer_token=self.bearer_token)


        self.auth = OAuth1UserHandler(
            os.getenv("SOCIAL__X_API_KEY"),
            os.getenv("SOCIAL__X_API_KEY_SECRET"),
            os.getenv("SOCIAL__X_ACCESS_TOKEN"),
            os.getenv("SOCIAL__X_ACCESS_TOKEN_SECRET"),
        )
        self.sync_client = API(self.auth)

    @property
    def platform(self) -> str:
        """Return the platform name."""
        return "x"

    async def fetch_mentions(self, query: str, limit: int = 10) -> list[dict]:
        """Fetch recent tweets matching the query."""
        try:
            response = await self.client.search_recent_tweets(
                query=query, max_results=limit, tweet_fields=["created_at", "author_id"]
            )
            tweets = response.data or []
            return [
                {
                    "platform": self.platform,
                    "content": tweet.text,
                    "author_id": tweet.author_id,
                    "tweet_id": tweet.id,
                    "timestamp": tweet.created_at.isoformat()
                    if tweet.created_at
                    else None,
                }
                for tweet in tweets
            ]
        except TweepyException:
            return []

    def post_tweet(self, content: str) -> dict:
        """Post a new tweet (synchronous)."""
        try:
            tweet = self.sync_client.update_status(status=content)
            return {
                "tweet_id": tweet.id,
                "content": tweet.text,
                "created_at": str(tweet.created_at),
            }
        except TweepyException:
            return {}

    def reply_to_tweet(self, tweet_id: int, reply_text: str) -> dict:
        """Reply to a tweet by ID."""
        try:
            tweet = self.sync_client.update_status(
                status=reply_text,
                in_reply_to_status_id=tweet_id,
                auto_populate_reply_metadata=True,
            )
            return {
                "reply_id": tweet.id,
                "content": tweet.text,
                "created_at": str(tweet.created_at),
            }
        except TweepyException:
            return {}
