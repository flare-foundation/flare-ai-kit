"""Settings for Flare AI Kit."""

from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from flare_ai_kit.a2a.settings import A2ASettings
from flare_ai_kit.agent.settings import AgentSettings
from flare_ai_kit.common.logging import configure_logging
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

    agent: AgentSettings = Field(default_factory=AgentSettings)  # pyright: ignore[reportArgumentType,reportUnknownVariableType]
    ecosystem: EcosystemSettings = Field(default_factory=EcosystemSettings)  # pyright: ignore[reportArgumentType,reportUnknownVariableType]
    vector_db: VectorDbSettings = Field(default_factory=VectorDbSettings)  # pyright: ignore[reportArgumentType,reportUnknownVariableType]
    graph_db: GraphDbSettings = Field(default_factory=GraphDbSettings)  # pyright: ignore[reportArgumentType,reportUnknownVariableType]
    social: SocialSettings = Field(default_factory=SocialSettings)  # pyright: ignore[reportArgumentType,reportUnknownVariableType]
    tee: TeeSettings = Field(default_factory=TeeSettings)  # pyright: ignore[reportArgumentType,reportUnknownVariableType]
    ingestion: IngestionSettings = Field(default_factory=IngestionSettings)  # pyright: ignore[reportArgumentType,reportUnknownVariableType]
    a2a: A2ASettings = Field(default_factory=A2ASettings)

    def model_post_init(self, __context: object, /) -> None:  # pyright: ignore[reportMissingParameterType]
        """Initialize logging after settings are loaded."""
        configure_logging(self.log_level)


def initialize_logging(log_level: str = "INFO") -> None:
    """
    Initialize structured logging for the Flare AI Kit.

    This function can be called manually if you want to configure logging
    without using AppSettings, or if you want to change the log level
    after initialization.

    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)

    Example:
        ```python
        from flare_ai_kit.config import initialize_logging

        # Initialize logging with custom level
        initialize_logging("DEBUG")

        # Now all modules will use structured logging
        from flare_ai_kit.common.logging import get_logger
        logger = get_logger(__name__)
        logger.info("This will be structured logging")
        ```

    """
    configure_logging(log_level)
