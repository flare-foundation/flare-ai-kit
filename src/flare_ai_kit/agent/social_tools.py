"""ADK tool wrappers for social media platform integrations."""

import structlog
from typing import Any

from flare_ai_kit.agent.tool import tool
from flare_ai_kit.social import SocialSettings, TelegramClient, XClient

logger = structlog.get_logger(__name__)


@tool
async def send_telegram_message(chat_id: str, text: str) -> dict[str, Any]:
    """
    Send a message to a Telegram chat or channel.

    Args:
        chat_id: The unique identifier for the target chat (e.g., '@channelname' or user ID)
        text: The text message to send

    Returns:
        Dictionary containing the send status and message details

    """
    logger.info("Sending Telegram message", chat_id=chat_id, text_length=len(text))

    try:
        settings = SocialSettings()  # type: ignore[call-arg] 
        telegram_client = TelegramClient(settings)

        success = await telegram_client.send_message(chat_id, text)

        return {
            "chat_id": chat_id,
            "text": text[:100] + "..." if len(text) > 100 else text,
            "success": success,
            "platform": "telegram",
            "configured": telegram_client.is_configured,
            "status": "success" if success else "failed",
        }
    except Exception as e:
        logger.error("Failed to send Telegram message", error=str(e))
        return {
            "chat_id": chat_id,
            "text": text[:100] + "..." if len(text) > 100 else text,
            "success": False,
            "platform": "telegram",
            "configured": False,
            "status": "error",
            "error": str(e),
        }


@tool
async def post_tweet(text: str) -> dict[str, Any]:
    """
    Post a tweet to X (formerly Twitter).

    Args:
        text: The content of the tweet (must be 280 characters or less)

    Returns:
        Dictionary containing the post status and tweet details

    """
    logger.info("Posting tweet", text_length=len(text))

    try:
        if len(text) > 280:
            raise ValueError("Tweet text exceeds 280 character limit")

        settings = SocialSettings()  # type: ignore[call-arg]
        x_client = XClient(settings)

        success = await x_client.post_tweet(text)

        return {
            "text": text,
            "character_count": len(text),
            "success": success,
            "platform": "x",
            "configured": x_client.is_configured,
            "status": "success" if success else "failed",
        }
    except Exception as e:
        logger.error("Failed to post tweet", error=str(e))
        return {
            "text": text,
            "character_count": len(text),
            "success": False,
            "platform": "x",
            "configured": False,
            "status": "error",
            "error": str(e),
        }


@tool
async def broadcast_message(
    text: str, platforms: list[str], telegram_chat_id: str | None = None
) -> dict[str, Any]:
    """
    Broadcast a message across multiple social media platforms.

    Args:
        text: The message to broadcast
        platforms: List of platforms to post to ("telegram", "x")
        telegram_chat_id: Chat ID for Telegram (required if telegram in platforms)

    Returns:
        Dictionary containing results for each platform

    """
    logger.info("Broadcasting message", platforms=platforms, text_length=len(text))

    try:
        results: list[dict[str, Any]] = []

        for platform in platforms:
            if platform.lower() == "telegram":
                if not telegram_chat_id:
                    results.append(
                        {
                            "platform": "telegram",
                            "success": False,
                            "error": "telegram_chat_id is required for Telegram posts",
                        }
                    )
                    continue

                telegram_result = await send_telegram_message(telegram_chat_id, text)
                results.append(
                    {
                        "platform": "telegram",
                        "success": telegram_result["success"],
                        "configured": telegram_result["configured"],
                    }
                )

            elif platform.lower() == "x":
                if len(text) > 280:
                    # Truncate text for X
                    truncated_text = text[:277] + "..."
                    x_result = await post_tweet(truncated_text)
                else:
                    x_result = await post_tweet(text)

                results.append(
                    {
                        "platform": "x",
                        "success": x_result["success"],
                        "configured": x_result["configured"],
                        "character_count": x_result["character_count"],
                    }
                )

            else:
                results.append(
                    {
                        "platform": platform,
                        "success": False,
                        "error": f"Unsupported platform: {platform}",
                    }
                )

        success_count = sum(1 for r in results if r.get("success", False))

        return {
            "results": results,
            "total_platforms": len(platforms),
            "successful_posts": success_count,
            "text": text[:100] + "..." if len(text) > 100 else text,
            "status": "success",
        }
    except Exception as e:
        logger.error("Failed to broadcast message", error=str(e))
        return {
            "results": [],
            "total_platforms": len(platforms),
            "successful_posts": 0,
            "text": text[:100] + "..." if len(text) > 100 else text,
            "status": "error",
            "error": str(e),
        }


@tool
async def check_social_configuration() -> dict[str, Any]:
    """
    Check the configuration status of social media clients.

    Returns:
        Dictionary containing configuration status for each platform

    """
    logger.info("Checking social media configuration")

    try:
        settings = SocialSettings()  # type: ignore[call-arg]  # type: ignore

        # Check Telegram configuration
        telegram_client = TelegramClient(settings)
        telegram_configured = telegram_client.is_configured

        # Check X configuration
        x_client = XClient(settings)
        x_configured = x_client.is_configured

        return {
            "telegram": {
                "configured": telegram_configured,
                "status": "ready" if telegram_configured else "not_configured",
                "api_token_set": bool(settings.telegram_api_token),
            },
            "x": {
                "configured": x_configured,
                "status": "ready" if x_configured else "not_configured",
                "api_key_set": bool(settings.x_api_key),
                "api_key_secret_set": bool(settings.x_api_key_secret),
                "access_token_set": bool(settings.x_access_token),
                "access_token_secret_set": bool(settings.x_access_token_secret),
            },
            "overall_status": "success",
        }
    except Exception as e:
        logger.error("Failed to check social configuration", error=str(e))
        return {
            "telegram": {
                "configured": False,
                "status": "error",
                "api_token_set": False,
            },
            "x": {
                "configured": False,
                "status": "error",
                "api_key_set": False,
                "api_key_secret_set": False,
                "access_token_set": False,
                "access_token_secret_set": False,
            },
            "overall_status": "error",
            "error": str(e),
        }


@tool
async def format_social_update(
    title: str,
    description: str,
    url: str | None = None,
    hashtags: list[str] | None = None,
    platform: str = "general",
) -> dict[str, Any]:
    """
    Format a social media update with title, description, and optional elements.

    Args:
        title: Main title or headline
        description: Detailed description or body text
        url: Optional URL to include
        hashtags: Optional list of hashtags (without # symbol)
        platform: Target platform for formatting ("telegram", "x", "general")

    Returns:
        Dictionary containing formatted message and metadata

    """
    logger.info("Formatting social update", platform=platform, title=title)

    try:
        # Format hashtags
        formatted_hashtags = ""
        if hashtags:
            formatted_hashtags = " " + " ".join(
                f"#{tag.strip('#')}" for tag in hashtags
            )

        # Format based on platform
        if platform.lower() == "telegram":
            # Telegram supports markdown formatting
            message = f"*{title}*\n\n{description}"
            if url:
                message += f"\n\n🔗 {url}"
            if formatted_hashtags:
                message += f"\n\n{formatted_hashtags}"

        elif platform.lower() == "x":
            # X has character limits, so be concise
            message = f"{title}\n\n{description}"
            if url:
                message += f"\n\n{url}"
            if formatted_hashtags:
                message += formatted_hashtags

            # Truncate if too long
            if len(message) > 280:
                available_chars = 280 - len(formatted_hashtags) - len(url or "") - 10
                truncated_desc = description[:available_chars] + "..."
                message = f"{title}\n\n{truncated_desc}"
                if url:
                    message += f"\n\n{url}"
                if formatted_hashtags:
                    message += formatted_hashtags

        else:
            # General format
            message = f"{title}\n\n{description}"
            if url:
                message += f"\n\n{url}"
            if formatted_hashtags:
                message += f"\n\n{formatted_hashtags}"

        return {
            "message": message,
            "character_count": len(message),
            "title": title,
            "description": description,
            "url": url or "",
            "hashtags": hashtags or [],
            "platform": platform,
            "status": "success",
        }
    except Exception as e:
        logger.error("Failed to format social update", error=str(e))
        return {
            "message": "",
            "character_count": 0,
            "title": title,
            "description": description,
            "url": url or "",
            "hashtags": hashtags or [],
            "platform": platform,
            "status": "error",
            "error": str(e),
        }
