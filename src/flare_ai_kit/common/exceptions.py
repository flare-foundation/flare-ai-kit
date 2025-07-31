"""
Custom exceptions used throughout the Flare AI Kit SDK.

All exceptions defined in this SDK inherit from the base `FlareAIKitError`.
This allows users to catch any specific SDK error using:

try:
    # Code using Flare AI Kit
    ...
except FlareAIKitError as e:
    # Handle any error originating from the Flare AI Kit
    print(f"An SDK error occurred: {e}")

Specific error types can be caught by targeting their respective classes
or intermediate base exceptions (e.g., `FlareTxError`, `VtpmError`).
"""


# --- Root SDK Exception ---
class FlareAIKitError(Exception):
    """Base exception for all Flare AI Kit specific errors."""


# --- vTPM Errors ---
class VtpmError(FlareAIKitError):
    """Base exception for vTPM related errors."""


class VtpmAttestationError(VtpmError):
    """Raised for errors during communication with the vTPM attestation service."""


class VtpmValidationError(VtpmError):
    """Base exception for vTPM validation errors."""


class InvalidCertificateChainError(VtpmValidationError):
    """Raised when vTPM certificate chain validation fails."""


class CertificateParsingError(VtpmValidationError):
    """Raised when parsing a vTPM certificate fails."""


class SignatureValidationError(VtpmValidationError):
    """Raised when vTPM signature validation fails."""


# --- Telegram Bot errors ---
class TelegramBotError(FlareAIKitError):
    """Base exception for Telegram Bot integration errors."""


class BotNotInitializedError(TelegramBotError):
    """Raised when the Telegram Bot is required, but it's not initialized."""


class UpdaterNotInitializedError(TelegramBotError):
    """Raised when the Telegram Updater is required, but it's not initialized."""


# --- Flare Blockchain Interaction Errors ---
class FlareTxError(FlareAIKitError):
    """Raised for errors during Flare transaction building, signing, or sending."""


class FlareTxRevertedError(FlareTxError):
    """Raised when a Flare transaction is confirmed but has reverted on-chain."""


class FtsoV2Error(FlareAIKitError):
    """Raised for errors specific to interacting with FTSO V2 contracts.."""


# --- Flare Explorer Errors ---
class ExplorerError(FlareAIKitError):
    """Base exception for errors related to Flare Block Explorer interactions."""


# --- ABI Errors ---
class AbiError(FlareAIKitError):
    """Raised for errors encountered while fetching or processing contract ABIs."""


# --- Embeddings Errors ---
class EmbeddingsError(FlareAIKitError):
    """Raised for errors encountered when generating or handling embeddings."""


# --- VectorDB Errors ---
class VectorDbError(FlareAIKitError):
    """Raised for errors encountered when interacting with VectorDBs."""


# --- FAssets Errors ---
class FAssetsError(FlareAIKitError):
    """Base exception for errors related to FAssets protocol interactions."""


class FAssetsContractError(FAssetsError):
    """Raised for errors during FAssets contract interactions."""


class FAssetsMintError(FAssetsError):
    """Raised for errors during FAssets minting process."""


class FAssetsRedeemError(FAssetsError):
    """Raised for errors during FAssets redemption process."""


class FAssetsCollateralError(FAssetsError):
    """Raised for errors related to FAssets collateral management."""


class FAssetsAgentError(FAssetsError):
    """Raised for errors related to FAssets agent operations."""


# --- DA Layer Errors ---
class DALayerError(FlareAIKitError):
    """Base exception for errors related to Data Availability Layer interactions."""


class AttestationNotFoundError(DALayerError):
    """Raised when a requested attestation is not found."""


class MerkleProofError(DALayerError):
    """Raised for errors related to Merkle proof validation or processing."""


# --- A2A Errors ---
class A2AClientError(FlareAIKitError):
    """Error class concerned with unrecoverable A2A errors."""


# --- PDF Processing Errors ---
class PdfPostingError(FlareAIKitError):
    """Error class concerned with onchain PDF data posting errors."""
