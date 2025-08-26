"""Flare Data Connector (FDC) protocol connector for Flare AI Kit."""

import structlog
import httpx
from dataclasses import dataclass
from enum import IntEnum
from typing import Any, Dict, Self, Optional, TypeVar, cast
from eth_abi.abi import encode
from web3.types import HexStr, Wei, TxParams

from flare_ai_kit.common import FdcError, load_abi
from flare_ai_kit.ecosystem.flare import Flare
from flare_ai_kit.ecosystem.settings_models import EcosystemSettingsModel
 
logger = structlog.get_logger(__name__)

# Inline minimal ABI for FdcHub (requestAttestation only)
FDC_HUB_ABI = [
    {
        "inputs": [
            {"internalType": "uint256", "name": "attestationType", "type": "uint256"},
            {"internalType": "bytes", "name": "requestData", "type": "bytes"}
        ],
        "name": "requestAttestation",
        "outputs": [
            {"internalType": "uint256", "name": "requestId", "type": "uint256"}
        ],
        "stateMutability": "payable",
        "type": "function"
    }
]

# --- Attestation Types ---
class FdcAttestationType(IntEnum):
    AddressValidity = 0
    EVMTransaction = 1
    JsonApi = 2
    Payment = 3
    ConfirmedBlockHeightExists = 4
    BalanceDecreasingTransaction = 5
    ReferencedPaymentNonexistence = 6

# --- Result Dataclasses ---
@dataclass(frozen=True)
class AddressValidityResult:
    is_valid: bool
    address: str
    chain: str

@dataclass(frozen=True)
class EVMTransactionResult:
    tx_hash: str
    block_number: int
    status: str
    from_address: str
    to_address: str
    value: int
    gas_used: int
    input_data: str
    timestamp: int

@dataclass(frozen=True)
class JsonApiResult:
    data: Any
    url: str
    jq: Optional[str]

@dataclass(frozen=True)
class PaymentResult:
    tx_id: str
    chain: str
    amount: int
    sender: str
    recipient: str
    confirmed: bool
    timestamp: int

@dataclass(frozen=True)
class ConfirmedBlockHeightExistsResult:
    chain: str
    block_height: int
    confirmed: bool

@dataclass(frozen=True)
class BalanceDecreasingTransactionResult:
    tx_id: str
    chain: str
    amount: int
    sender: str
    recipient: str
    decreased: bool
    timestamp: int

@dataclass(frozen=True)
class ReferencedPaymentNonexistenceResult:
    chain: str
    reference: str
    nonexistence: bool
    checked_interval: str

# --- FDC Connector ---
T = TypeVar("T", bound="Fdc")

class Fdc(Flare):
    """Adapter for interacting with the Flare Data Connector (FDC) oracle."""

    def __init__(self, settings: EcosystemSettingsModel) -> None:
        super().__init__(settings)
        # self.fdc = None  # Will be initialized in 'create'
        self.fdc_hub = None
        self.fdc_verification = None
        # self.da_layer_url = self._get_da_layer_url(settings.is_testnet)
        # self.http_client = httpx.AsyncClient()

    def _get_da_layer_url(self, is_testnet: bool) -> str:
        """
        Returns the base URL for the Data Availability Layer based on the network.
        """
        if is_testnet:
            # Coston2 Testnet URL
            return "https://coston2-api.flare.network/ext/C/rpc"
        # Mainnet URL
        return "https://flare-api.flare.network/ext/C/rpc"

    @classmethod
    async def create(cls, settings: EcosystemSettingsModel) -> Self:
        """
        Asynchronously creates and initializes an FDC instance.

        Args:
            settings: Instance of EcosystemSettingsModel.

        Returns:
            A fully initialized FDC instance.
        """

        instance = cls(settings)
        logger.debug("Initializing FDC...")

        # Get contract addresses
        # FdcHub =  0xc25c749DC27Efb1864Cb3DADa8845B7687eB2d44 (source: flarescan)
        fdc_hub_address = await instance.get_protocol_contract_address("FdcHub")
        fdc_verification_address = await instance.get_protocol_contract_address(
            "FdcVerification"
        )

        # Initialize contract instances
        instance.fdc_hub = instance.w3.eth.contract(
            address=instance.w3.to_checksum_address(fdc_hub_address),
            abi= load_abi("FdcHub"),
        )
        instance.fdc_verification = instance.w3.eth.contract(
            address=instance.w3.to_checksum_address(fdc_verification_address),
            abi=load_abi("FdcVerification"),
        )

        logger.debug(
            "FDC initialized",             
            fdc_hub=fdc_hub_address,
            fdc_verification=fdc_verification_address,
        )
        return instance

    async def request_attestation(
        self,
        attestation_type: FdcAttestationType,
        request_data: Dict[str, Any],
        value_wei: int = 0,
    ) -> int:
        """
        Submits an attestation request to the FDC contract.
        Returns the request ID.
        """
        if not self.fdc_hub:
            raise FdcError("FDC contract not initialized. Use Fdc.create().")
        try:
            encoded_data = self._encode_request_data(attestation_type, request_data)
            tx = self.fdc_hub.functions.requestAttestation(
                int(attestation_type), encoded_data
            ).build_transaction({"from": self.address, "value": value_wei})
            tx_hash = await self.sign_and_send_transaction(cast(TxParams, tx))
            if tx_hash is None:
                raise FdcError("Transaction hash is None")
            logger.info("Attestation request submitted", tx_hash=tx_hash)
            return int(tx_hash, 16)
        except Exception as e:
            logger.error("Failed to submit attestation request", error=str(e))
            raise FdcError(f"Failed to submit attestation request: {e}") from e

    def _encode_request_data(self, attestation_type: FdcAttestationType, request_data: Dict[str, Any]) -> bytes:
        """
        ABI-encodes request_data for the given attestation type.
        This must match the FDC contract's expected input for each type.
        """
        if attestation_type == FdcAttestationType.EVMTransaction:
            tx_hash = request_data.get("txHash")
            if not isinstance(tx_hash, str):
                tx_hash = ""
            return encode(["uint256", "bytes32"], [request_data["chainId"], bytes.fromhex(tx_hash or "")])
        elif attestation_type == FdcAttestationType.JsonApi:
            return encode(["string", "string"], [request_data["url"], request_data.get("jq", "")])
        return bytes(str(request_data), "utf-8")

    async def get_attestation_result(
        self,
        request_id: int,
        da_layer_url: str,
        timeout: float = 10.0,
    ) -> Any:
        """
        Retrieves the result of an attestation request from the DA Layer.
        Returns a structured result dataclass or dict.
        """
        try:
            result = await self.query_offchain_data(
                f"{da_layer_url}/attestation/{request_id}", params={}, timeout=timeout
            )
            return self._parse_attestation_result(result)
        except Exception as e:
            logger.error("Failed to get attestation result", error=str(e))
            raise FdcError(f"Failed to get attestation result: {e}") from e

    async def query_offchain_data(
        self, endpoint: str, params: Dict[str, Any], timeout: float = 10.0
    ) -> Dict[str, Any]:
        """
        Queries the DA Layer for offchain attestation data and Merkle proofs.
        """
        async with httpx.AsyncClient(timeout=timeout) as client:
            resp = await client.get(endpoint, params=params)
            resp.raise_for_status()
            return resp.json()

    def _parse_attestation_result(self, result: Dict[str, Any]) -> Any:
        """
        Parses the DA Layer result into a structured dataclass or dict.
        """
        attestation_type = result.get("attestationType")
        if attestation_type == FdcAttestationType.EVMTransaction:
            return EVMTransactionResult(
                tx_hash=result["txHash"],
                block_number=result["blockNumber"],
                status=result["status"],
                from_address=result["from"],
                to_address=result["to"],
                value=result["value"],
                gas_used=result["gasUsed"],
                input_data=result["inputData"],
                timestamp=result["timestamp"],
            )
        elif attestation_type == FdcAttestationType.JsonApi:
            return JsonApiResult(
                data=result["data"],
                url=result["url"],
                jq=result.get("jq"),
            )
        elif attestation_type == FdcAttestationType.AddressValidity:
            return AddressValidityResult(
                is_valid=result["isValid"],
                address=result["address"],
                chain=result["chain"],
            )
        elif attestation_type == FdcAttestationType.Payment:
            return PaymentResult(
                tx_id=result["txId"],
                chain=result["chain"],
                amount=result["amount"],
                sender=result["sender"],
                recipient=result["recipient"],
                confirmed=result["confirmed"],
                timestamp=result["timestamp"],
            )
        elif attestation_type == FdcAttestationType.ConfirmedBlockHeightExists:
            return ConfirmedBlockHeightExistsResult(
                chain=result["chain"],
                block_height=result["blockHeight"],
                confirmed=result["confirmed"],
            )
        elif attestation_type == FdcAttestationType.BalanceDecreasingTransaction:
            return BalanceDecreasingTransactionResult(
                tx_id=result["txId"],
                chain=result["chain"],
                amount=result["amount"],
                sender=result["sender"],
                recipient=result["recipient"],
                decreased=result["decreased"],
                timestamp=result["timestamp"],
            )
        elif attestation_type == FdcAttestationType.ReferencedPaymentNonexistence:
            return ReferencedPaymentNonexistenceResult(
                chain=result["chain"],
                reference=result["reference"],
                nonexistence=result["nonexistence"],
                checked_interval=result["checkedInterval"],
            )
        else:
            logger.warning("Unknown attestation type, returning raw result.")
            return result
