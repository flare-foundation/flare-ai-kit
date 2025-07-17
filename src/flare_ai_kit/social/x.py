"""Client for interacting with the X API using Tweepy."""

import structlog
import tweepy.asynchronous as tweepy  # type: ignore[reportMissingTypeStubs]
from tweepy.errors import TweepyException  # type: ignore[reportMissingTypeStubs]

from flare_ai_kit.social.settings import SocialSettings

logger = structlog.get_logger(__name__)


class XClient:
    """A client to interact with the X API for posting tweets."""

    def __init__(self, settings: SocialSettings) -> None:
        """
        Initializes the XClient using credentials from the settings.

        This will set up the API client. If any credentials are missing,
        the client will not be configured to make real API calls.

        Args:
            settings: The social settings model containing X API keys and tokens.

        """
        api_key = settings.x_api_key.get_secret_value() if settings.x_api_key else None
        api_key_secret = (
            settings.x_api_key_secret.get_secret_value()
            if settings.x_api_key_secret
            else None
        )
        access_token = (
            settings.x_access_token.get_secret_value()
            if settings.x_access_token
            else None
        )
        access_token_secret = (
            settings.x_access_token_secret.get_secret_value()
            if settings.x_access_token_secret
            else None
        )

        self.client: tweepy.AsyncClient | None = None
        self.is_configured = False

        if api_key and api_key_secret and access_token and access_token_secret:
            try:
                logger.info("XClient credentials provided, initializing client.")

                # V2 API Client for creating tweets
                self.client = tweepy.AsyncClient(
                    consumer_key=api_key,
                    consumer_secret=api_key_secret,
                    access_token=access_token,
                    access_token_secret=access_token_secret,
                )
                self.is_configured = True
                logger.info("XClient initialized and configured successfully.")
            except Exception as e:
                logger.exception("Failed to initialize Tweepy client", error=e)
        else:
            logger.warning(
                "XClient is not fully configured due to missing credentials. "
                "API calls will be simulated."
            )

    async def post_tweet(self, text: str) -> bool:
        """
        Posts a tweet to X.

        Args:
            text: The content of the tweet to post. Must be 280 characters or less.

        Returns:
            True if the tweet was posted successfully, False otherwise.

        """
        if not self.is_configured or not self.client:
            logger.info(
                "Simulating tweet post because X client is not configured.", text=text
            )
            return True  # Simulate success

        if not text:
            logger.error("Invalid tweet content provided. Must be a non-empty string.")
            return False

        logger.info("Attempting to post", tweet=text[:50])
        try:
            response = await self.client.create_tweet(text=text)  # pyright: ignore[reportUnknownMemberType, reportUnknownVariableType]
            tweet_id = response.data.get("id") if response.data else "N/A"  # pyright: ignore[reportUnknownMemberType, reportAttributeAccessIssue, reportUnknownVariableType]
        except TweepyException as e:
            logger.exception("Failed to post tweet due to an API error.", error=e)
            return False
        except Exception as e:
            logger.exception(
                "An unexpected error occurred while posting a tweet.", error=e
            )
            return False
        else:
            logger.info("Tweet posted successfully.", tweet_id=tweet_id)
            return True
