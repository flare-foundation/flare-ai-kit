"""Settings for TEE."""

from pydantic import BaseModel, Field, StrictBool


class TeeSettingsModel(BaseModel):
    """Configuration specific to the Flare ecosystem interactions."""

    simulate_attestation_token: StrictBool = Field(
        False,  # noqa: FBT003
        description="Use a pregenerated attestation token for testing.",
    )
