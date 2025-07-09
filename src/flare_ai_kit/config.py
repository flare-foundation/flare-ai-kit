"""Settings for Flare AI Kit."""

from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from flare_ai_kit.agent.settings_models import AgentSettingsModel
from flare_ai_kit.ecosystem.settings_models import EcosystemSettingsModel
from flare_ai_kit.ingestion.settings_models import IngestionSettingsModel
from flare_ai_kit.rag.graph.settings_models import GraphDbSettingsModel
from flare_ai_kit.rag.vector.settings_models import VectorDbSettingsModel
from flare_ai_kit.social.settings_models import SocialSettingsModel
from flare_ai_kit.tee.settings_models import TeeSettingsModel


class AppSettings(BaseSettings):
    """Main application settings, composes settings from SDK components."""

    # Configure loading behavior
    model_config = SettingsConfigDict(
        env_file=".env",  # Load variables from '.env' file if it exists
        env_file_encoding="utf-8",
        env_nested_delimiter="__",  # Use double underscore for nested variables
        case_sensitive=False,  # Environment variable names are case-insensitive
        extra="ignore",  # Ignore extra variables found in environment/file
    )

    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = Field(
        "DEBUG",
        description="Logging level (e.g., DEBUG, INFO, WARNING, ERROR, CRITICAL)",
    )
    agent: AgentSettingsModel = Field(default_factory=AgentSettingsModel)  # pyright: ignore[reportArgumentType,reportUnknownVariableType]
    ecosystem: EcosystemSettingsModel = Field(default_factory=EcosystemSettingsModel)  # pyright: ignore[reportArgumentType,reportUnknownVariableType]
    vector_db: VectorDbSettingsModel = Field(default_factory=VectorDbSettingsModel)  # pyright: ignore[reportArgumentType,reportUnknownVariableType]
    graph_db: GraphDbSettingsModel = Field(default_factory=GraphDbSettingsModel)  # pyright: ignore[reportArgumentType,reportUnknownVariableType]
    social: SocialSettingsModel = Field(default_factory=SocialSettingsModel)  # pyright: ignore[reportArgumentType,reportUnknownVariableType]
    tee: TeeSettingsModel = Field(default_factory=TeeSettingsModel)  # pyright: ignore[reportArgumentType,reportUnknownVariableType]
    ingestion: IngestionSettingsModel = Field(default_factory=IngestionSettingsModel)  # pyright: ignore[reportArgumentType,reportUnknownVariableType]
