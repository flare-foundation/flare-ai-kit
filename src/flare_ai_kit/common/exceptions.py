"""All exceptions in Flare AI Kit."""


# vTPM errors
class VtpmAttestationError(Exception):
    """Custom exception for vTPM attestation service communication errors."""


class VtpmValidationError(Exception):
    """Custom exception for validation errors."""


class InvalidCertificateChainError(VtpmValidationError):
    """Raised when certificate chain validation fails."""


class CertificateParsingError(VtpmValidationError):
    """Raised when certificate parsing fails."""


class SignatureValidationError(VtpmValidationError):
    """Raised when signature validation fails."""


# Telegram Bot errors
class TelegramBotError(Exception):
    """Custom exception for Telegram errors."""


class BotNotInitializedError(TelegramBotError):
    """Telegram Bot was not initialized."""


class UpdaterNotInitializedError(TelegramBotError):
    """Telegram Updater was not initialized."""


# Flare blockchain errors
class FlareError(Exception):
    """Custom exception for Flare errors."""


class FtsoV2Error(Exception):
    """Custom exception for FtsoV errors."""


# Explorer errors
class ExplorerError(Exception):
    """Custom exception for Explorer errors."""


class AbiError(ExplorerError):
    """Custom exception for ABI loading errors."""


class EmbeddingsError(Exception):
    """Custom exception for embeddings errors."""
