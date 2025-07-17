"""Interactions with Flare Data Availability (DA) Layer."""

from dataclasses import dataclass
from datetime import UTC, datetime
from types import TracebackType
from typing import Any, Self, TypeVar
from urllib.parse import urljoin

import aiohttp
import structlog

from flare_ai_kit.common.exceptions import (
    AttestationNotFoundError,
    DALayerError,
    MerkleProofError,
)
from flare_ai_kit.ecosystem.flare import Flare
from flare_ai_kit.ecosystem.settings_models import EcosystemSettingsModel

# HTTP Status Codes
HTTP_NOT_FOUND = 404

logger = structlog.get_logger(__name__)

# Type variable for the factory method pattern
T = TypeVar("T", bound="DataAvailabilityLayer")


@dataclass(frozen=True)
class AttestationRequest:
    """Represents an attestation request structure."""

    attestation_type: str
    source_id: str
    message_integrity_code: str
    request_body: dict[str, Any]


@dataclass(frozen=True)
class AttestationResponse:
    """Represents an attestation response structure."""

    attestation_type: str
    source_id: str
    voting_round: int
    lowest_used_timestamp: int
    request_body: dict[str, Any]
    response_body: dict[str, Any]


@dataclass(frozen=True)
class MerkleProof:
    """Represents a Merkle proof for attestation verification."""

    merkle_proof: list[str]
    leaf_index: int
    total_leaves: int


@dataclass(frozen=True)
class AttestationData:
    """Complete attestation data including response and proof."""

    response: AttestationResponse
    proof: MerkleProof


@dataclass(frozen=True)
class VotingRoundData:
    """Data for a specific voting round."""

    voting_round: int
    merkle_root: str
    timestamp: int
    total_attestations: int
    finalized: bool


@dataclass(frozen=True)
class FTSOAnchorFeed:
    """FTSO anchor feed data structure."""

    id: str
    name: str
    decimals: int
    category: str
    description: str


@dataclass(frozen=True)
class FTSOAnchorFeedValue:
    """FTSO anchor feed value with proof."""

    id: str
    value: int
    timestamp: int
    decimals: int
    proof: MerkleProof


@dataclass(frozen=True)
class FTSOAnchorFeedsWithProof:
    """FTSO anchor feeds with proof for a specific voting round."""

    voting_round: int
    merkle_root: str
    feeds: list[FTSOAnchorFeedValue]


class DataAvailabilityLayer(Flare):
    """
    Connector for interacting with the Flare Data Availability (DA) Layer.

    This class provides methods to:
    - Retrieve attestation data committed via Flare State Protocol (FSP)
    - Fetch and verify Merkle proofs for attestation data
    - Access historical data from the DA Layer
    - Query voting round information
    """

    def __init__(self, settings: EcosystemSettingsModel) -> None:
        super().__init__(settings)
        self.da_layer_base_url = str(settings.da_layer_base_url)
        self.da_layer_api_key = settings.da_layer_api_key
        self.session: aiohttp.ClientSession | None = None
        self.timeout = aiohttp.ClientTimeout(total=30.0)

    @classmethod
    async def create(cls, settings: EcosystemSettingsModel) -> Self:
        """
        Asynchronously creates and initializes a DataAvailabilityLayer instance.

        Args:
            settings: Instance of EcosystemSettingsModel.

        Returns:
            A fully initialized DataAvailabilityLayer instance.

        """
        instance = cls(settings)
        logger.debug("Initializing DataAvailabilityLayer...")

        # Initialize HTTP session
        headers = {
            "Content-Type": "application/json",
            "User-Agent": "flare-ai-kit/1.0.0",
        }

        # Add API key to headers if available
        if instance.da_layer_api_key:
            headers["Authorization"] = (
                f"Bearer {instance.da_layer_api_key.get_secret_value()}"
            )

        instance.session = aiohttp.ClientSession(
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
        if not self.session:
            headers = {
                "Content-Type": "application/json",
                "User-Agent": "flare-ai-kit/1.0.0",
            }

            # Add API key to headers if available
            if self.da_layer_api_key:
                headers["Authorization"] = (
                    f"Bearer {self.da_layer_api_key.get_secret_value()}"
                )

            self.session = aiohttp.ClientSession(
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
        """Close the HTTP session."""
        if self.session:
            await self.session.close()
            self.session = None

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
        if not self.session:
            msg = "HTTP session not initialized. Use create() method."
            raise DALayerError(msg)

        url = urljoin(self.da_layer_base_url, endpoint)

        try:
            async with self.session.request(
                method=method, url=url, params=params, json=data
            ) as response:
                if response.status == HTTP_NOT_FOUND:
                    self._raise_not_found_error(endpoint)

                response.raise_for_status()
                result = await response.json()

                logger.debug(
                    "DA Layer API request successful",
                    method=method,
                    endpoint=endpoint,
                    status=response.status,
                )

                return result

        except aiohttp.ClientError as e:
            msg = f"HTTP request failed for {method} {endpoint}: {e}"
            logger.exception(msg)
            raise DALayerError(msg) from e
        except Exception as e:
            msg = f"Unexpected error during {method} {endpoint}: {e}"
            logger.exception(msg)
            raise DALayerError(msg) from e

    async def get_attestation_data(
        self, voting_round: int, attestation_index: int
    ) -> AttestationData:
        """
        Retrieve attestation data for a specific voting round and index.

        Args:
            voting_round: The voting round ID
            attestation_index: Index of the attestation in the round

        Returns:
            Complete attestation data including response and Merkle proof

        Raises:
            AttestationNotFoundError: If attestation is not found
            DALayerError: If request fails

        """
        endpoint = f"attestation/{voting_round}/{attestation_index}"

        try:
            data = await self._make_request("GET", endpoint)

            response = AttestationResponse(
                attestation_type=data["response"]["attestationType"],
                source_id=data["response"]["sourceId"],
                voting_round=data["response"]["votingRound"],
                lowest_used_timestamp=data["response"]["lowestUsedTimestamp"],
                request_body=data["response"]["requestBody"],
                response_body=data["response"]["responseBody"],
            )

            proof = MerkleProof(
                merkle_proof=data["proof"]["merkleProof"],
                leaf_index=data["proof"]["leafIndex"],
                total_leaves=data["proof"]["totalLeaves"],
            )

            logger.info(
                "Retrieved attestation data",
                voting_round=voting_round,
                attestation_index=attestation_index,
                attestation_type=response.attestation_type,
            )

            return AttestationData(response=response, proof=proof)

        except AttestationNotFoundError:
            raise
        except Exception as e:
            msg = (
                f"Failed to retrieve attestation data for round {voting_round}, "
                f"index {attestation_index}: {e}"
            )
            raise DALayerError(msg) from e

    async def get_attestations_by_type(
        self,
        attestation_type: str,
        source_id: str | None = None,
        start_round: int | None = None,
        end_round: int | None = None,
        limit: int = 100,
    ) -> list[AttestationData]:
        """
        Retrieve attestations by type with optional filtering.

        Args:
            attestation_type: Type of attestation (e.g., "Payment", "EVMTransaction")
            source_id: Optional source identifier filter
            start_round: Optional starting voting round
            end_round: Optional ending voting round
            limit: Maximum number of results to return

        Returns:
            List of matching attestation data

        Raises:
            DALayerError: If request fails

        """
        endpoint = "attestations/search"
        params: dict[str, Any] = {"attestationType": attestation_type, "limit": limit}

        if source_id:
            params["sourceId"] = source_id
        if start_round is not None:
            params["startRound"] = start_round
        if end_round is not None:
            params["endRound"] = end_round

        try:
            data = await self._make_request("GET", endpoint, params=params)
            attestations: list[AttestationData] = []

            for item in data["attestations"]:
                response = AttestationResponse(
                    attestation_type=item["response"]["attestationType"],
                    source_id=item["response"]["sourceId"],
                    voting_round=item["response"]["votingRound"],
                    lowest_used_timestamp=item["response"]["lowestUsedTimestamp"],
                    request_body=item["response"]["requestBody"],
                    response_body=item["response"]["responseBody"],
                )

                proof = MerkleProof(
                    merkle_proof=item["proof"]["merkleProof"],
                    leaf_index=item["proof"]["leafIndex"],
                    total_leaves=item["proof"]["totalLeaves"],
                )

                attestations.append(AttestationData(response=response, proof=proof))

            logger.info(
                "Retrieved attestations by type",
                attestation_type=attestation_type,
                source_id=source_id,
                count=len(attestations),
            )
        except Exception as e:
            msg = f"Failed to retrieve attestations by type {attestation_type}: {e}"
            raise DALayerError(msg) from e
        else:
            return attestations

    async def verify_merkle_proof(
        self, attestation_data: AttestationData, expected_merkle_root: str | None = None
    ) -> bool:
        """
        Verify a Merkle proof for attestation data.

        Args:
            attestation_data: Attestation data with proof to verify
            expected_merkle_root: Optional expected root (fetched from chain if not
                provided)

        Returns:
            True if proof is valid, False otherwise

        Raises:
            MerkleProofError: If verification fails due to invalid data
            DALayerError: If request fails

        """
        try:
            # If no expected root provided, fetch from voting round data
            if expected_merkle_root is None:
                round_data = await self.get_voting_round_data(
                    attestation_data.response.voting_round
                )
                expected_merkle_root = round_data.merkle_root

            # Prepare verification request
            endpoint = "proof/verify"
            verification_data = {
                "merkleProof": attestation_data.proof.merkle_proof,
                "leafIndex": attestation_data.proof.leaf_index,
                "totalLeaves": attestation_data.proof.total_leaves,
                "expectedRoot": expected_merkle_root,
                "attestationResponse": {
                    "attestationType": attestation_data.response.attestation_type,
                    "sourceId": attestation_data.response.source_id,
                    "votingRound": attestation_data.response.voting_round,
                    "lowestUsedTimestamp": (
                        attestation_data.response.lowest_used_timestamp
                    ),
                    "requestBody": attestation_data.response.request_body,
                    "responseBody": attestation_data.response.response_body,
                },
            }

            result = await self._make_request("POST", endpoint, data=verification_data)
            is_valid = result.get("valid", False)

            logger.info(
                "Merkle proof verification completed",
                voting_round=attestation_data.response.voting_round,
                valid=is_valid,
            )
        except Exception as e:
            msg = f"Failed to verify Merkle proof: {e}"
            logger.exception(msg)
            raise MerkleProofError(msg) from e
        else:
            return is_valid

    async def get_voting_round_data(self, voting_round: int) -> VotingRoundData:
        """
        Retrieve metadata for a specific voting round.

        Args:
            voting_round: The voting round ID

        Returns:
            Voting round metadata

        Raises:
            DALayerError: If request fails

        """
        endpoint = f"round/{voting_round}"

        try:
            data = await self._make_request("GET", endpoint)

            round_data = VotingRoundData(
                voting_round=data["votingRound"],
                merkle_root=data["merkleRoot"],
                timestamp=data["timestamp"],
                total_attestations=data["totalAttestations"],
                finalized=data["finalized"],
            )

            logger.info(
                "Retrieved voting round data",
                voting_round=voting_round,
                finalized=round_data.finalized,
                total_attestations=round_data.total_attestations,
            )
        except Exception as e:
            msg = f"Failed to retrieve voting round data for round {voting_round}: {e}"
            raise DALayerError(msg) from e
        else:
            return round_data

    async def get_historical_data(
        self,
        start_timestamp: int,
        end_timestamp: int,
        attestation_types: list[str] | None = None,
        source_ids: list[str] | None = None,
        limit: int = 1000,
    ) -> list[AttestationData]:
        """
        Retrieve historical attestation data within a time range.

        Args:
            start_timestamp: Start timestamp (Unix timestamp)
            end_timestamp: End timestamp (Unix timestamp)
            attestation_types: Optional list of attestation types to filter
            source_ids: Optional list of source IDs to filter
            limit: Maximum number of results to return

        Returns:
            List of historical attestation data

        Raises:
            DALayerError: If request fails

        """
        endpoint = "attestations/historical"
        params: dict[str, Any] = {
            "startTimestamp": start_timestamp,
            "endTimestamp": end_timestamp,
            "limit": limit,
        }

        if attestation_types:
            params["attestationTypes"] = ",".join(attestation_types)
        if source_ids:
            params["sourceIds"] = ",".join(source_ids)

        try:
            data = await self._make_request("GET", endpoint, params=params)
            attestations: list[AttestationData] = []

            for item in data["attestations"]:
                response = AttestationResponse(
                    attestation_type=item["response"]["attestationType"],
                    source_id=item["response"]["sourceId"],
                    voting_round=item["response"]["votingRound"],
                    lowest_used_timestamp=item["response"]["lowestUsedTimestamp"],
                    request_body=item["response"]["requestBody"],
                    response_body=item["response"]["responseBody"],
                )

                proof = MerkleProof(
                    merkle_proof=item["proof"]["merkleProof"],
                    leaf_index=item["proof"]["leafIndex"],
                    total_leaves=item["proof"]["totalLeaves"],
                )

                attestations.append(AttestationData(response=response, proof=proof))

            logger.info(
                "Retrieved historical attestation data",
                start_time=datetime.fromtimestamp(start_timestamp, tz=UTC),
                end_time=datetime.fromtimestamp(end_timestamp, tz=UTC),
                count=len(attestations),
            )
        except Exception as e:
            msg = f"Failed to retrieve historical data: {e}"
            raise DALayerError(msg) from e
        else:
            return attestations

    async def get_supported_attestation_types(self) -> list[dict[str, Any]]:
        """
        Retrieve list of supported attestation types and their configurations.

        Returns:
            List of supported attestation types with metadata

        Raises:
            DALayerError: If request fails

        """
        endpoint = "attestation-types"

        try:
            data = await self._make_request("GET", endpoint)
            attestation_types = data.get("attestationTypes", [])

            logger.info(
                "Retrieved supported attestation types", count=len(attestation_types)
            )
        except Exception as e:
            msg = f"Failed to retrieve supported attestation types: {e}"
            raise DALayerError(msg) from e
        else:
            return attestation_types

    async def get_ftso_anchor_feed_names(self) -> list[FTSOAnchorFeed]:
        """
        Retrieve list of available FTSO anchor feed names and metadata.

        Returns:
            List of FTSO anchor feed configurations

        Raises:
            DALayerError: If request fails

        """
        endpoint = "ftso/anchor-feed-names"

        try:
            data = await self._make_request("GET", endpoint)
            feeds: list[FTSOAnchorFeed] = []

            for feed_data in data.get("feeds", []):
                feed = FTSOAnchorFeed(
                    id=feed_data["id"],
                    name=feed_data["name"],
                    decimals=feed_data["decimals"],
                    category=feed_data["category"],
                    description=feed_data["description"],
                )
                feeds.append(feed)

            logger.info("Retrieved FTSO anchor feed names", count=len(feeds))
        except Exception as e:
            msg = f"Failed to retrieve FTSO anchor feed names: {e}"
            raise DALayerError(msg) from e
        else:
            return feeds

    async def get_ftso_anchor_feeds_with_proof(
        self,
        voting_round: int,
        feed_ids: list[str] | None = None,
    ) -> FTSOAnchorFeedsWithProof:
        """
        Retrieve FTSO anchor feeds with Merkle proofs for a specific voting round.

        Args:
            voting_round: The voting round ID
            feed_ids: Optional list of specific feed IDs to retrieve

        Returns:
            FTSO anchor feeds with proofs for the voting round

        Raises:
            DALayerError: If request fails

        """
        endpoint = "ftso/anchor-feeds-with-proof"
        data_payload: dict[str, Any] = {"votingRound": voting_round}

        if feed_ids:
            data_payload["feedIds"] = feed_ids

        try:
            data = await self._make_request("POST", endpoint, data=data_payload)
            feeds: list[FTSOAnchorFeedValue] = []

            for feed_data in data.get("feeds", []):
                proof = MerkleProof(
                    merkle_proof=feed_data["proof"]["merkleProof"],
                    leaf_index=feed_data["proof"]["leafIndex"],
                    total_leaves=feed_data["proof"]["totalLeaves"],
                )

                feed_value = FTSOAnchorFeedValue(
                    id=feed_data["id"],
                    value=feed_data["value"],
                    timestamp=feed_data["timestamp"],
                    decimals=feed_data["decimals"],
                    proof=proof,
                )
                feeds.append(feed_value)

            result = FTSOAnchorFeedsWithProof(
                voting_round=data["votingRound"],
                merkle_root=data["merkleRoot"],
                feeds=feeds,
            )

            logger.info(
                "Retrieved FTSO anchor feeds with proof",
                voting_round=voting_round,
                feed_count=len(feeds),
            )
        except Exception as e:
            msg = (
                f"Failed to retrieve FTSO anchor feeds with proof for round "
                f"{voting_round}: {e}"
            )
            raise DALayerError(msg) from e
        else:
            return result
