"""Settings for TEE."""

from pydantic import BaseModel, Field


class TeeSettingsModel(BaseModel):
    """Configuration specific to the Flare ecosystem interactions."""

    simulate_attestation_token: bool = Field(
        True,  # noqa: FBT003
        description="Use a pregenerated attestation token for testing.",
    )
