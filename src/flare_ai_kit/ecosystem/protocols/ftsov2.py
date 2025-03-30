"""Interactions with Flare Time Series Oracle V2 (FTSOv2)."""

from typing import Final, Self, TypeVar

import structlog

from flare_ai_kit.common import FtsoV2Error, load_abi
from flare_ai_kit.ecosystem.flare import Flare

logger = structlog.get_logger(__name__)

# Valid categories when querying FTSOv2 prices
VALID_CATEGORIES: Final[frozenset[str]] = frozenset(["01", "02", "03", "04", "05"])

# Type variable for the factory method pattern
T = TypeVar("T", bound="FtsoV2")


class FtsoV2(Flare):
    """Fetches price data from Flare Time Series Oracle V2 contracts."""

    def __init__(self, **kwargs: str) -> None:
        super().__init__(**kwargs)
        self.ftsov2 = None  # Will be initialized in 'create'
        self.logger = logger.bind(router="ftso")

    # Factory method for asynchronous initialization
    @classmethod
    async def create(cls, web3_provider_url: str, **kwargs: str) -> Self:
        """
        Asynchronously creates and initializes an FtsoV2 instance.

        Args:
            web3_provider_url: URL of the Web3 provider endpoint.
            **kwargs: Additional keyword arguments for the base class.

        Returns:
            A fully initialized AsyncFtsoV2 instance.

        """
        instance = cls(web3_provider_url=web3_provider_url, **kwargs)
        instance.logger.debug("Initializing FtsoV2...")
        # Await the async method from the base class
        ftsov2_address = await instance.get_protocol_contract_address("FtsoV2")
        instance.ftsov2 = instance.w3.eth.contract(
            address=instance.w3.to_checksum_address(ftsov2_address),
            abi=load_abi("FtsoV2"),  # Assuming load_abi is sync
        )
        instance.logger.debug("FtsoV2 initialized", address=ftsov2_address)
        return instance

    async def _get_feed_by_id(self, feed_id: str) -> tuple[int, int, int]:
        """
        Internal method to call the getFeedById contract function.

        Args:
            feed_id: The bytes21 feed ID (e.g., '0x014254432f555344...').

        Returns:
            A tuple containing (price, decimals, timestamp).

        Raises:
            FtsoV2Error: If the contract call fails (e.g., revert, network issue).

        """
        if not self.ftsov2:
            msg = "FtsoV2 instance not fully initialized. Use FtsoV2.create()."
            raise AttributeError(msg)
        try:
            # The contract returns (price, decimals, timestamp)
            return await self.ftsov2.functions.getFeedById(feed_id).call()  # type: ignore
        except Exception as e:
            msg = f"Contract call failed for getFeedById({feed_id}): {e}"
            raise FtsoV2Error(msg) from e

    async def _get_feeds_by_id(
        self, feed_ids: list[str]
    ) -> tuple[list[int], list[int], list[int]]:
        """
        Internal method to call the getFeedsById contract function for multiple feeds.

        Args:
            feed_ids: A list of bytes21 feed IDs.

        Returns:
            A tuple containing (list_of_prices, list_of_decimals, single_timestamp).

        Raises:
            FtsoV2Error: If the contract call fails.

        """
        if not self.ftsov2:
            msg = "FtsoV2 instance not fully initialized. Use FtsoV2.create()."
            raise AttributeError(msg)
        try:
            # The contract returns (prices[], decimals[], timestamp)
            return await self.ftsov2.functions.getFeedsById(feed_ids).call()  # type: ignore
        except Exception as e:
            msg = f"Contract call failed for getFeedsById({len(feed_ids)} feeds)"
            raise FtsoV2Error(msg) from e

    @staticmethod
    def _check_category_validity(category: str) -> None:
        """
        Validates the provided category string.

        Args:
            category: The category string (e.g., "01").

        Raises:
            FtsoV2Error: If the category is not in VALID_CATEGORIES.

        """
        if category not in VALID_CATEGORIES:
            msg = f"Invalid category '{category}' specified."
            f"Valid categories: {sorted(VALID_CATEGORIES)}"
            raise FtsoV2Error(msg)

    @staticmethod
    def _feed_name_to_id(feed_name: str, category: str) -> str:
        """
        Converts a human-readable feed name and category into a bytes21 hex feed ID.

        Example: ("BTC/USD", "01") -> "0x014254432f55534400..."

        Args:
            feed_name: The feed name string (e.g., "BTC/USD").
            category: The category string (e.g., "01").

        Returns:
            The resulting bytes21 feed ID as a hex string prefixed with '0x'.

        Raises:
            ValueError: If feed_name cannot be encoded.

        """
        # Encode name to bytes, convert to hex
        hex_feed_name = feed_name.encode("utf-8").hex()
        # Concatenate category and hex name
        combined_hex = category + hex_feed_name
        # Pad with '0' on the right to reach 42 hex characters (21 bytes)
        hex_bytes_size = 42
        padded_hex_string = combined_hex.ljust(hex_bytes_size, "0")
        # Ensure it doesn't exceed 42 chars if feed_name is very long
        if len(padded_hex_string) > hex_bytes_size:
            msg = f"Resulting hex string '{feed_name}' is too long."
            raise FtsoV2Error(msg)
        return f"0x{padded_hex_string}"

    async def get_latest_price(self, feed_name: str, category: str = "01") -> float:
        """
        Retrieves the latest price for a single feed.

        Args:
            feed_name: The human-readable feed name (e.g., "BTC/USD").
            category: The feed category (default: "01").

        Returns:
            The latest price as a float, adjusted for decimals.
            Returns 0.0 if the price or decimals returned by the contract are zero,
            which might indicate an invalid or unprovided feed.

        Raises:
            FtsoV2Error: If the category is invalid, feed name cannot be converted
                or the contract call fails.

        """
        self._check_category_validity(category)
        feed_id = self._feed_name_to_id(feed_name, category)
        feeds, decimals, timestamp = await self._get_feed_by_id(feed_id)
        self.logger.debug(
            "get_latest_price",
            feed_name=feed_name,
            feed_id=feed_id,
            feeds=feeds,
            decimals=decimals,
            timestamp=timestamp,
        )
        return feeds / (10**decimals)

    async def get_latest_prices(
        self, feed_names: list[str], category: str = "01"
    ) -> list[float]:
        """
        Retrieves the latest prices for multiple feeds within the same category.

        Args:
            feed_names: A list of human-readable feed names.
            category: The feed category for all requested feeds (default: "01").

        Returns:
            A list of prices as floats, corresponding to the order of `feed_names`.
            Individual prices will be 0.0 if the contract returned zero values.

        Raises:
            FtsoV2Error: If the category is invalid, feed name cannot be converted
                or the contract call fails.

        """
        if not self.ftsov2:
            msg = "FtsoV2 instance not fully initialized. Use FtsoV2.create()."
            raise AttributeError(msg)

        self._check_category_validity(category)
        feed_ids = [
            self._feed_name_to_id(feed_name, category) for feed_name in feed_names
        ]
        feeds, decimals, timestamp = await self._get_feeds_by_id(feed_ids)
        self.logger.debug(
            "get_latest_prices_async",
            num_feeds=len(feed_names),
            feeds=feeds,
            decimals=decimals,
            timestamp=timestamp,
        )
        return [
            feed / 10**decimal for feed, decimal in zip(feeds, decimals, strict=True)
        ]
