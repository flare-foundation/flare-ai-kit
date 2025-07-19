from pydantic import BaseModel, Field
from flare_ai_kit.ecosystem.tooling.goldsky import ChainSlug

class GoldskyConfig(BaseModel):
    """Configuration for Goldsky integration."""
    api_key: str = Field(..., description="Goldsky API key")
    project_name: str = Field(..., description="Goldsky project name")
    chain_slug: ChainSlug = Field(default=ChainSlug.FLARE_MAINNET, description="Flare chain slug")
    goldsky_cli_path: str = Field(default="goldsky", description="Path to Goldsky CLI")
    base_url: str = Field(default="https://api.goldsky.com", description="Goldsky API base URL")
    timeout: int = Field(default=30, description="HTTP timeout