"""Settings for Flare AI Kit."""

from functools import lru_cache
from typing import Literal

import structlog
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from flare_ai_kit.agent.settings import AgentSettings
from flare_ai_kit.ecosystem.settings import EcosystemSettings
from flare_ai_kit.ingestion.settings import IngestionSettings
from flare_ai_kit.rag.graph.settings import GraphDbSettings
from flare_ai_kit.rag.vector.settings import VectorDbSetting
from flare_ai_kit.social.settings_models import SocialSettings
from flare_ai_kit.tee.settings import TeeSettings


class AppSettings(BaseSettings):
    """Main application settings, composes settings from SDK components."""

    # Configure loading behavior
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_nested_delimiter="__",  # Use double underscore for nested variables
        case_sensitive=False,
        extra="ignore",
    )
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = Field(
        default="DEBUG", description="Logging level"
    )
    agent: AgentSettings
    ecosystem: EcosystemSettings
    vector_db: VectorDbSetting
    graph_db: GraphDbSettings
    social: SocialSettings
    tee: TeeSettings
    ingestion: IngestionSettings


@lru_cache
def get_settings() -> AppSettings:
    """Singleton settings."""
    settings = AppSettings()  # pyright: ignore[reportCallIssue]
    structlog.configure(
        wrapper_class=structlog.make_filtering_bound_logger(settings.log_level)
    )
    return settings
