"""Interactions with Flare Data Availability (DA) Layer."""

from types import TracebackType
from typing import Any, Self, TypeVar
from urllib.parse import urljoin

import httpx
import structlog

from flare_ai_kit.common import (
    AttestationNotFoundError,
    DALayerError,
    FTSOAnchorFeed,
    FTSOAnchorFeedsWithProof,
    VotingRound,
)
from flare_ai_kit.ecosystem.flare import Flare
from flare_ai_kit.ecosystem.settings import EcosystemSettings

# HTTP Status Codes
HTTP_NOT_FOUND = 404

logger = structlog.get_logger(__name__)

# Type variable for the factory method pattern
T = TypeVar("T", bound="DataAvailabilityLayer")


class DataAvailabilityLayer(Flare):
    """
    Connector for interacting with the Flare Data Availability (DA) Layer.

    This class provides methods to:
    - Retrieve attestation data committed via Flare State Protocol (FSP)
    - Fetch and verify Merkle proofs for attestation data
    - Access historical data from the DA Layer
    - Query voting round information
    """

    def __init__(self, settings: EcosystemSettings) -> None:
        super().__init__(settings)
        self.da_layer_base_url = str(settings.da_layer_base_url)
        self.da_layer_api_key = settings.da_layer_api_key
        self.client: httpx.AsyncClient | None = None
        self.timeout = httpx.Timeout(30.0)

    @classmethod
    async def create(cls, settings: EcosystemSettings) -> Self:
        """
        Asynchronously creates and initializes a DataAvailabilityLayer instance.

        Args:
            settings: Instance of EcosystemSettings.

        Returns:
            A fully initialized DataAvailabilityLayer instance.

        """
        instance = cls(settings)
        logger.debug("Initializing DataAvailabilityLayer...")

        # Initialize HTTP client
        headers = {
            "Content-Type": "application/json",
            "User-Agent": "flare-ai-kit/1.0.0",
        }

        # Add API key to headers if available
        if instance.da_layer_api_key:
            headers["Authorization"] = (
                f"Bearer {instance.da_layer_api_key.get_secret_value()}"
            )

        instance.client = httpx.AsyncClient(
            timeout=instance.timeout,
            headers=headers,
        )

        # Verify connection to DA Layer
        await instance._verify_connection()
        logger.debug(
            "DataAvailabilityLayer initialized", base_url=instance.da_layer_base_url
        )
        return instance

    async def __aenter__(self) -> Self:
        """Async context manager entry."""
        if not self.client:
            headers = {
                "Content-Type": "application/json",
                "User-Agent": "flare-ai-kit/1.0.0",
            }

            # Add API key to headers if available
            if self.da_layer_api_key:
                headers["Authorization"] = (
                    f"Bearer {self.da_layer_api_key.get_secret_value()}"
                )

            self.client = httpx.AsyncClient(
                timeout=self.timeout,
                headers=headers,
            )
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        """Async context manager exit."""
        await self.close()

    async def close(self) -> None:
        """Close the HTTP client."""
        if self.client:
            await self.client.aclose()
            self.client = None

    async def _verify_connection(self) -> None:
        """Verify connection to the DA Layer API."""
        try:
            await self._make_request("GET", "health")
            logger.info("Successfully connected to DA Layer API")
        except Exception as e:
            msg = f"Failed to connect to DA Layer API: {e}"
            logger.exception(msg)
            raise DALayerError(msg) from e

    def _raise_not_found_error(self, endpoint: str) -> None:
        """Helper method to raise AttestationNotFoundError."""
        msg = f"Resource not found: {endpoint}"
        raise AttestationNotFoundError(msg)

    async def _make_request(
        self,
        method: str,
        endpoint: str,
        params: dict[str, Any] | None = None,
        data: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        Make HTTP request to DA Layer API.

        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint
            params: Query parameters
            data: Request body data

        Returns:
            Response data as dictionary

        Raises:
            DALayerError: If request fails

        """
        if not self.client:
            msg = "HTTP client not initialized. Use create() method."
            raise DALayerError(msg)

        url = urljoin(self.da_layer_base_url, endpoint)

        try:
            response = await self.client.request(
                method=method, url=url, params=params, json=data
            )
            if response.status_code == HTTP_NOT_FOUND:
                self._raise_not_found_error(endpoint)
            response.raise_for_status()
            result = response.json()
        except httpx.HTTPError as e:
            msg = f"HTTP request failed for {method} {endpoint}"
            logger.exception(msg)
            raise DALayerError(msg) from e
        except Exception as e:
            msg = f"Unexpected error during {method} {endpoint}"
            logger.exception(msg)
            raise DALayerError(msg) from e
        else:
            logger.debug(
                "DA Layer API request successful",
                method=method,
                endpoint=endpoint,
                status_code=response.status_code,
            )
            return result

    async def get_latest_voting_round(self) -> VotingRound:
        """
        Retrieve the latest voting round.

        Returns:
            Latest voting round data

        Raises:
            DALayerError: If request fails

        """
        endpoint = "v0/fsp/latest-voting-round"

        try:
            data = await self._make_request("GET", endpoint)
            voting_round_data = VotingRound.model_validate(data)

            logger.info("Retrieved FSP voting round data")
        except Exception as e:
            msg = f"Failed to retrieve FSP voting round data: {e}"
            raise DALayerError(msg) from e
        else:
            return voting_round_data

    async def get_ftso_anchor_feed_names(self) -> list[FTSOAnchorFeed]:
        """
        Retrieve list of available FTSO anchor feed names and metadata.

        Returns:
            List of FTSO anchor feed configurations

        Raises:
            DALayerError: If request fails

        """
        endpoint = "v0/ftso/anchor-feed-names"

        try:
            data = await self._make_request("GET", endpoint)
            feeds: list[FTSOAnchorFeed] = [
                FTSOAnchorFeed.model_validate(feed) for feed in data
            ]
            logger.info("Retrieved FTSO anchor feed names", count=len(feeds))
        except Exception as e:
            msg = f"Failed to retrieve FTSO anchor feed names: {e}"
            raise DALayerError(msg) from e
        else:
            return feeds

    async def get_ftso_anchor_feeds_with_proof(
        self,
        feed_ids: list[str],
    ) -> list[FTSOAnchorFeedsWithProof]:
        """
        Retrieve FTSO anchor feeds with Merkle proofs for a specific voting round.

        Args:
            feed_ids: Optional list of specific feed IDs to retrieve

        Returns:
            FTSO anchor feeds with proofs for the voting round

        Raises:
            DALayerError: If request fails

        """
        endpoint = "v0/ftso/anchor-feeds-with-proof"
        payload = {"feed_ids": feed_ids}

        try:
            data = await self._make_request("POST", endpoint, data=payload)
            feeds: list[FTSOAnchorFeedsWithProof] = [
                FTSOAnchorFeedsWithProof.model_validate(feed) for feed in data
            ]

            logger.info(
                "Retrieved FTSO anchor feeds with proof",
                feed_count=len(feeds),
            )
        except Exception as e:
            msg = "Failed to retrieve FTSO anchor feeds"
            raise DALayerError(msg) from e
        else:
            return feeds
