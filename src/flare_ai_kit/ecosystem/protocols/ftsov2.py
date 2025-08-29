"""Interactions with Flare Time Series Oracle V2 (FTSOv2)."""

from typing import Final, Self, TypeVar

import structlog

from flare_ai_kit.common import FtsoFeedCategory, FtsoV2Error, load_abi
from flare_ai_kit.ecosystem.flare import Flare
from flare_ai_kit.ecosystem.settings import EcosystemSettings

logger = structlog.get_logger(__name__)

# Valid categories when querying FTSOv2 prices
VALID_CATEGORIES: Final[frozenset[str]] = frozenset(["01", "02", "03", "04", "05"])

# Type variable for the factory method pattern
T = TypeVar("T", bound="FtsoV2")


class FtsoV2(Flare):
    """Fetches price data from Flare Time Series Oracle V2 contracts."""

    def __init__(self, settings: EcosystemSettings) -> None:
        super().__init__(settings)
        self.ftsov2 = None  # Will be initialized in 'create'

    # Factory method for asynchronous initialization
    @classmethod
    async def create(cls, settings: EcosystemSettings) -> Self:
        """
        Asynchronously creates and initializes an FtsoV2 instance.

        Args:
            settings: Instance of EcosystemSettings.

        Returns:
            A fully initialized AsyncFtsoV2 instance.

        """
        instance = cls(settings)
        logger.info("Initializing FtsoV2...")
        # Await the async method from the base class
        ftsov2_address = await instance.get_protocol_contract_address("FtsoV2")
        instance.ftsov2 = instance.w3.eth.contract(
            address=instance.w3.to_checksum_address(ftsov2_address),
            abi=load_abi("FtsoV2"),  # Assuming load_abi is sync
        )
        logger.debug("FtsoV2 initialized", address=ftsov2_address)
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
            return await self.ftsov2.functions.getFeedById(feed_id).call()  # pyright: ignore[reportUnknownVariableType,reportGeneralTypeIssues]
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
            return await self.ftsov2.functions.getFeedsById(feed_ids).call()  # pyright: ignore[reportUnknownVariableType,reportGeneralTypeIssues]
        except Exception as e:
            msg = f"Contract call failed for getFeedsById({len(feed_ids)} feeds)"
            raise FtsoV2Error(msg) from e

    @staticmethod
    def _feed_name_to_id(feed_name: str, category: FtsoFeedCategory) -> str:
        """
        Converts a human-readable feed name and category into a bytes21 hex feed ID.

        Example: ("BTC/USD", "01") -> "0x014254432f55534400..."

        Args:
            feed_name: The feed name string (e.g., "BTC/USD").
            category: The category (e.g., FtsoFeedCategory.CRYPTO).

        Returns:
            The resulting bytes21 feed ID as a hex string prefixed with '0x'.

        Raises:
            ValueError: If feed_name cannot be encoded.

        """
        # Encode name to bytes, convert to hex
        hex_feed_name = feed_name.encode("utf-8").hex()
        # Concatenate category value and hex name
        combined_hex = category.value + hex_feed_name
        # Pad with '0' on the right to reach 42 hex characters (21 bytes)
        hex_bytes_size = 42
        padded_hex_string = combined_hex.ljust(hex_bytes_size, "0")
        # Ensure it doesn't exceed 42 chars if feed_name is very long
        if len(padded_hex_string) > hex_bytes_size:
            msg = f"Resulting hex string '{feed_name}' is too long."
            raise FtsoV2Error(msg)
        return f"0x{padded_hex_string}"

    async def get_latest_price(
        self, feed_name: str, category: FtsoFeedCategory = FtsoFeedCategory.CRYPTO
    ) -> float:
        """
        Retrieves the latest price for a single feed.

        Args:
            feed_name: The human-readable feed name (e.g., "BTC/USD").
            category: The feed category (default: CRYPTO i.e. "01").

        Returns:
            The latest price as a float, adjusted for decimals.
            Returns 0.0 if the price or decimals returned by the contract are zero,
            which might indicate an invalid or unprovided feed.

        Raises:
            FtsoV2Error: If the category is invalid, feed name cannot be converted
                or the contract call fails.

        """
        feed_id = self._feed_name_to_id(feed_name, category)
        value, decimals, timestamp = await self._get_feed_by_id(feed_id)
        logger.debug(
            "get_latest_price",
            feed_name=feed_name,
            feed_id=feed_id,
            value=value,
            decimals=decimals,
            timestamp=timestamp,
        )
        return value / (10**decimals)

    async def get_latest_prices(
        self,
        feed_names: list[str],
        category: FtsoFeedCategory = FtsoFeedCategory.CRYPTO,
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

        feed_ids = [
            self._feed_name_to_id(feed_name, category) for feed_name in feed_names
        ]
        values, decimals, timestamp = await self._get_feeds_by_id(feed_ids)
        logger.debug(
            "get_latest_prices",
            feed_names=feed_names,
            feed_ids=feed_ids,
            value=values,
            decimals=decimals,
            timestamp=timestamp,
        )
        return [
            value / 10**decimal for value, decimal in zip(values, decimals, strict=True)
        ]
