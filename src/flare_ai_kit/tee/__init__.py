"""TEE (Trusted Execution Environment) module for secure computation."""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .attestation import VtpmAttestation
    from .validation import VtpmValidation

__all__ = ["VtpmAttestation", "VtpmValidation"]


def __getattr__(name: str):
    """Lazy import for TEE components."""
    if name == "VtpmAttestation":
        from .attestation import VtpmAttestation

        return VtpmAttestation
    if name == "VtpmValidation":
        from .validation import VtpmValidation

        return VtpmValidation
    msg = f"module '{__name__}' has no attribute '{name}'"
    raise AttributeError(msg)
