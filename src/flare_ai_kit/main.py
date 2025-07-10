"""Entry point for Flare AI Kit SDK."""

from .config import AppSettings, settings
from .ecosystem import BlockExplorer, Flare, FtsoV2
from .ingestion import GithubIngestor
from .rag.vector import VectorRAGPipeline, create_vector_rag_pipeline
from .social import TelegramClient, XClient
from .a2a import A2AClient

class FlareAIKit:
    """The main entry point for the Flare AI Kit SDK."""

    def __init__(self, config: AppSettings | None = None) -> None:
        """
        Initializes the Flare AI Kit SDK with the provided or default configuration.

        Examples:
        ```python
        from flare_ai_kit import FlareAIKit
        kit = FlareAIKit()
        balance = await kit.flare.check_balance("0x...")
        price = await (await kit.ftso).get_latest_price("FLR/USD")
        ```

        """
        self.settings = config or settings

        # Lazy-loaded properties
        self._flare = None
        self._block_explorer = None
        self._ftso = None
        self._vector_rag = None
        self._telegram = None
        self._github_ingestor = None
        self._x_client = None
        self._a2a = None

    # Ecosystem Interaction Methods
    @property
    def flare(self) -> Flare:
        """Access Flare blockchain interaction methods."""
        if self._flare is None:
            self._flare = Flare(self.settings.ecosystem)
        return self._flare

    @property
    async def ftso(self) -> FtsoV2:
        """Access FTSOv2 price oracle methods."""
        # Note the async nature of the property now
        if self._ftso is None:
            self._ftso = await FtsoV2.create(self.settings.ecosystem)
        return self._ftso

    @property
    def block_explorer(self) -> BlockExplorer:
        """Access the block explorer methods."""
        if self._block_explorer is None:
            self._block_explorer = BlockExplorer(self.settings.ecosystem)
        return self._block_explorer

    # Social Media Interaction Methods
    @property
    def telegram(self) -> TelegramClient:
        """Access Telegram client methods."""
        if self._telegram is None:
            self._telegram = TelegramClient(self.settings.social)
        return self._telegram

    @property
    def x_client(self) -> XClient:
        """Access X (formerly Twitter) client methods."""
        if self._x_client is None:
            self._x_client = XClient(self.settings.social)
        return self._x_client

    # RAG Methods
    @property
    def vector_rag(self) -> VectorRAGPipeline:
        """Access the RAG retriever."""
        if self._vector_rag is None:
            self._vector_rag = create_vector_rag_pipeline(
                vector_db_settings=self.settings.vector_db,
                agent_settings=self.settings.agent,
            )
        return self._vector_rag

    def github_ingestor(self) -> GithubIngestor:
        """Access the GitHub ingestor methods."""
        if self._github_ingestor is None:
            self._github_ingestor = GithubIngestor(self.settings.ingestion)
        return self._github_ingestor

    def a2a_client(self, sqlite_db_path: str):
        """"Access the A2A client and provide and optional db path for task management"""
        if self._a2a is None:
            self._a2a = A2AClient(sqlite_db_path)
        return self._a2a