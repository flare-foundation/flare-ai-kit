"""Entry point for Flare AI Kit SDK."""

import asyncio

import structlog

from .a2a import A2AClient
from .config import AppSettings
from .ecosystem import BlockExplorer, FAssets, Flare, FtsoV2
from .ingestion import GithubIngestor
from .ingestion.pdf_processor import PDFProcessor
from .onchain.contract_poster import ContractPoster
from .rag.vector import VectorRAGPipeline, create_vector_rag_pipeline
from .social import TelegramClient, XClient

logger = structlog.get_logger(__name__)


class FlareAIKit:
    """The main entry point for the Flare AI Kit SDK."""

    def __init__(self, config: AppSettings | None) -> None:
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
        self.settings = config or AppSettings()

        # Lazy-loaded properties
        self._flare: Flare | None = None
        self._block_explorer: BlockExplorer | None = None
        self._ftso: FtsoV2 | None = None
        self._fassets: FAssets | None = None
        self._vector_rag: VectorRAGPipeline | None = None
        self._telegram: TelegramClient | None = None
        self._github_ingestor: GithubIngestor | None = None
        self._x_client: XClient | None = None
        self._pdf_processor: PDFProcessor | None = None
        self._a2a_client: A2AClient | None = None

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
    async def fassets(self) -> FAssets:
        """Access FAssets protocol methods."""
        if self._fassets is None:
            self._fassets = await FAssets.create(self.settings.ecosystem)
        return self._fassets

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

    # RAG and Ingestion Methods
    @property
    def vector_rag(self) -> VectorRAGPipeline:
        """Access the RAG retriever."""
        if self._vector_rag is None:
            self._vector_rag = create_vector_rag_pipeline(
                vector_db_settings=self.settings.vector_db,
                agent_settings=self.settings.agent,
            )
        return self._vector_rag

    @property
    def github_ingestor(self) -> GithubIngestor:
        """Access the GitHub ingestor methods."""
        if self._github_ingestor is None:
            self._github_ingestor = GithubIngestor(self.settings.ingestion)
        return self._github_ingestor

    @property
    def pdf_processor(self) -> PDFProcessor:
        """Access the PDF ingestion and on-chain posting service."""
        if self._pdf_processor is None:
            if not self.settings.ingestion or not self.settings.ingestion.pdf_ingestion:
                msg = "PDF ingestion settings are not configured."
                raise ValueError(msg)

            contract_poster = ContractPoster(
                contract_settings=self.settings.ingestion.pdf_ingestion.contract_settings,
                ecosystem_settings=self.settings.ecosystem,
            )
            self._pdf_processor = PDFProcessor(
                settings=self.settings.ingestion.pdf_ingestion,
                contract_poster=contract_poster,
            )
        return self._pdf_processor

    # A2A methods
    @property
    def a2a_client(self) -> A2AClient:
        """Access the A2A client with optional db path."""
        if self._a2a_client is None:
            self._a2a_client = A2AClient(settings=self.settings.a2a)
        return self._a2a_client


async def core() -> None:
    """Core function to run the Flare AI Kit SDK."""
    logger.info("Starting Flare AI Kit core...")
    # Your core logic
    logger.info("Ending Flare AI Kit core...")


def start() -> None:
    """Main entry point for the Flare AI Kit SDK."""
    asyncio.run(core())
