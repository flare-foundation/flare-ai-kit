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

All exceptions include structured context information for better debugging
and troubleshooting. Sensitive data is automatically masked in error messages.
"""


# --- Root SDK Exception ---
class FlareAIKitError(Exception):
    """
    Base exception for all Flare AI Kit specific errors.

    Provides structured context information and automatic masking of sensitive data.
    """

    def __init__(
        self,
        message: str,
        context: dict[str, str] | None = None,
        error_code: str | None = None,
        **kwargs: str,
    ) -> None:
        """
        Initialize the exception with structured context.

        Args:
            message: Human-readable error message
            context: Additional context information (sensitive data will be masked)
            error_code: Optional error code for programmatic handling
            **kwargs: Additional context fields (sensitive data will be masked)

        """
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.context = self._mask_sensitive_data(context or {})
        self.context.update(self._mask_sensitive_data(kwargs))

    def _mask_sensitive_data(self, data: dict[str, str]) -> dict[str, str]:
        """Mask sensitive data in context information."""
        sensitive_keys = {
            "password",
            "passwd",
            "pwd",
            "secret",
            "token",
            "key",
            "api_key",
            "private_key",
            "privatekey",
            "mnemonic",
            "seed",
            "auth",
            "authorization",
            "credential",
            "cred",
            "access_token",
            "refresh_token",
            "bearer",
            "jwt",
            "session",
            "cookie",
        }

        masked_data: dict[str, str] = {}
        for key, value in data.items():
            key_lower = key.lower()
            if any(sensitive in key_lower for sensitive in sensitive_keys):
                masked_data[key] = "***MASKED***"
            else:
                masked_data[key] = value
        return masked_data

    def __str__(self) -> str:
        """Return formatted error message with context."""
        parts = [self.message]
        if self.error_code:
            parts.append(f"[{self.error_code}]")
        if self.context:
            context_str = ", ".join(f"{k}={v}" for k, v in self.context.items())
            parts.append(f"Context: {context_str}")
        return " ".join(parts)


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


# --- Wallet Errors ---
class WalletError(FlareAIKitError):
    """Base exception for wallet-related errors."""


class WalletCreationError(WalletError):
    """Raised when wallet creation fails."""


class WalletNotFoundError(WalletError):
    """Raised when a requested wallet is not found."""


class WalletPermissionError(WalletError):
    """Raised when wallet operation is denied due to permissions."""


class WalletSigningError(WalletError):
    """Raised when transaction signing fails."""


class WalletExportError(WalletError):
    """Raised when wallet export fails."""


class WalletImportError(WalletError):
    """Raised when wallet import fails."""


# --- Configuration Errors ---
class ConfigurationError(FlareAIKitError):
    """Raised for configuration-related errors."""


class InvalidConfigurationError(ConfigurationError):
    """Raised when configuration is invalid or missing required fields."""


# --- Validation Errors ---
class ValidationError(FlareAIKitError):
    """Base exception for validation errors."""


class InvalidInputError(ValidationError):
    """Raised when input validation fails."""


class InvalidAddressError(ValidationError):
    """Raised when an invalid blockchain address is provided."""


class InvalidAmountError(ValidationError):
    """Raised when an invalid amount is provided."""


# --- Consensus Errors ---
class ConsensusError(FlareAIKitError):
    """Base exception for consensus-related errors."""


class ConflictResolutionError(ConsensusError):
    """Raised when conflict resolution fails."""


class AgentCommunicationError(ConsensusError):
    """Raised when agent communication fails."""


# --- Social Connector Errors ---
class SocialConnectorError(FlareAIKitError):
    """Base exception for social connector errors."""


class TelegramConnectorError(SocialConnectorError):
    """Raised for Telegram connector errors."""


class DiscordConnectorError(SocialConnectorError):
    """Raised for Discord connector errors."""


class SlackConnectorError(SocialConnectorError):
    """Raised for Slack connector errors."""


class XConnectorError(SocialConnectorError):
    """Raised for X (Twitter) connector errors."""


class FarcasterConnectorError(SocialConnectorError):
    """Raised for Farcaster connector errors."""


# --- Ingestion Errors ---
class IngestionError(FlareAIKitError):
    """Base exception for data ingestion errors."""


class PDFProcessingError(IngestionError):
    """Raised when PDF processing fails."""


class GitHubIngestionError(IngestionError):
    """Raised when GitHub data ingestion fails."""


# --- RAG Errors ---
class RAGError(FlareAIKitError):
    """Base exception for RAG (Retrieval-Augmented Generation) errors."""


class VectorIndexError(RAGError):
    """Raised for vector indexing errors."""


class EmbeddingError(RAGError):
    """Raised for embedding generation errors."""


class RetrievalError(RAGError):
    """Raised for retrieval errors."""


class ResponseGenerationError(RAGError):
    """Raised for response generation errors."""
