"""Settings for Flare AI Kit."""


from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from flare_ai_kit.agent.settings import AgentSettings
from flare_ai_kit.ecosystem.settings import EcosystemSettings
from flare_ai_kit.ingestion.settings import IngestionSettings
from flare_ai_kit.rag.graph.settings import GraphDbSettings
from flare_ai_kit.rag.vector.settings import VectorDbSettings
from flare_ai_kit.social.settings import SocialSettings
from flare_ai_kit.tee.settings import TeeSettings


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

    agent: AgentSettingsModel = Field(default_factory=AgentSettingsModel)  # pyright: ignore[reportArgumentType,reportUnknownVariableType]
    ecosystem: EcosystemSettingsModel = Field(default_factory=EcosystemSettingsModel)  # pyright: ignore[reportArgumentType,reportUnknownVariableType]
    vector_db: VectorDbSettingsModel = Field(default_factory=VectorDbSettingsModel)  # pyright: ignore[reportArgumentType,reportUnknownVariableType]
    graph_db: GraphDbSettingsModel = Field(default_factory=GraphDbSettingsModel)  # pyright: ignore[reportArgumentType,reportUnknownVariableType]
    social: SocialSettingsModel = Field(default_factory=SocialSettingsModel)  # pyright: ignore[reportArgumentType,reportUnknownVariableType]
    tee: TeeSettingsModel = Field(default_factory=TeeSettingsModel)  # pyright: ignore[reportArgumentType,reportUnknownVariableType]
    ingestion: IngestionSettingsModel = Field(default_factory=IngestionSettingsModel)  # pyright: ignore[reportArgumentType,reportUnknownVariableType]

