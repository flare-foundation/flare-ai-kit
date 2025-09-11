"""Settings for Flare AI Kit."""

from typing import TYPE_CHECKING, Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

if TYPE_CHECKING:
    from flare_ai_kit.a2a.settings import A2ASettings
    from flare_ai_kit.agent.settings import AgentSettings
    from flare_ai_kit.ecosystem.settings import EcosystemSettings
    from flare_ai_kit.ingestion.settings import IngestionSettings
    from flare_ai_kit.rag.graph.settings import GraphDbSettings
    from flare_ai_kit.rag.vector.settings import VectorDbSettings
    from flare_ai_kit.social.settings import SocialSettings
    from flare_ai_kit.tee.settings import TeeSettings


def _get_agent_settings():
    """Lazy import for AgentSettings."""
    from flare_ai_kit.agent.settings import AgentSettings
    return AgentSettings()


def _get_ecosystem_settings():
    """Lazy import for EcosystemSettings."""
    from flare_ai_kit.ecosystem.settings import EcosystemSettings
    return EcosystemSettings()


def _get_vector_db_settings():
    """Lazy import for VectorDbSettings."""
    from flare_ai_kit.rag.vector.settings import VectorDbSettings
    return VectorDbSettings()


def _get_graph_db_settings():
    """Lazy import for GraphDbSettings."""
    from flare_ai_kit.rag.graph.settings import GraphDbSettings
    return GraphDbSettings()


def _get_social_settings():
    """Lazy import for SocialSettings."""
    from flare_ai_kit.social.settings import SocialSettings
    return SocialSettings()


def _get_tee_settings():
    """Lazy import for TeeSettings."""
    from flare_ai_kit.tee.settings import TeeSettings
    return TeeSettings()


def _get_ingestion_settings():
    """Lazy import for IngestionSettings."""
    from flare_ai_kit.ingestion.settings import IngestionSettings
    return IngestionSettings()


def _get_a2a_settings():
    """Lazy import for A2ASettings."""
    from flare_ai_kit.a2a.settings import A2ASettings
    return A2ASettings()


class AppSettings(BaseSettings):
    """Main application settings, composes settings from SDK components."""

    # Configure loading behavior
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_nested_delimiter="__",
        case_sensitive=False,
        extra="ignore",
    )
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = Field(
        default="DEBUG", description="Logging level"
    )

    agent: "AgentSettings" = Field(default_factory=_get_agent_settings)  # pyright: ignore[reportArgumentType,reportUnknownVariableType]
    ecosystem: "EcosystemSettings" = Field(default_factory=_get_ecosystem_settings)  # pyright: ignore[reportArgumentType,reportUnknownVariableType]
    vector_db: "VectorDbSettings" = Field(default_factory=_get_vector_db_settings)  # pyright: ignore[reportArgumentType,reportUnknownVariableType]
    graph_db: "GraphDbSettings" = Field(default_factory=_get_graph_db_settings)  # pyright: ignore[reportArgumentType,reportUnknownVariableType]
    social: "SocialSettings" = Field(default_factory=_get_social_settings)  # pyright: ignore[reportArgumentType,reportUnknownVariableType]
    tee: "TeeSettings" = Field(default_factory=_get_tee_settings)  # pyright: ignore[reportArgumentType,reportUnknownVariableType]
    ingestion: "IngestionSettings" = Field(default_factory=_get_ingestion_settings)  # pyright: ignore[reportArgumentType,reportUnknownVariableType]
    a2a: "A2ASettings" = Field(default_factory=_get_a2a_settings)  # pyright: ignore[reportArgumentType,reportUnknownVariableType]


# Rebuild the model to resolve forward references
def _rebuild_app_settings():
    """Rebuild AppSettings model with all required imports."""
    # Import all the settings classes to make them available for model_rebuild
    from flare_ai_kit.agent.settings import AgentSettings
    from flare_ai_kit.ecosystem.settings import EcosystemSettings
    from flare_ai_kit.rag.vector.settings import VectorDbSettings
    from flare_ai_kit.rag.graph.settings import GraphDbSettings
    from flare_ai_kit.social.settings import SocialSettings
    from flare_ai_kit.tee.settings import TeeSettings
    from flare_ai_kit.ingestion.settings import IngestionSettings
    from flare_ai_kit.a2a.settings import A2ASettings

    AppSettings.model_rebuild()

# Call rebuild function to ensure model is properly configured
_rebuild_app_settings()
