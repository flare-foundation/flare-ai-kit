import httpx
import structlog

from flare_ai_kit.config import AppSettings
from flare_ai_kit.ecosystem.applications.open_ocean_models import *

logger = structlog.get_logger(__name__)


class OpenOceanConnector:
    """
    Connector class to interface with OpenOcean v4 API for DEX aggregation.
    """

    BASE_URL = "https://open-api.openocean.finance/v4"

    def __init__(self):
        self.settings = AppSettings().ecosystem
        self.client = httpx.AsyncClient(timeout=self.settings.web3_provider_timeout)

    async def describe_openocean_services(self) -> str:
        return """
        OpenOcean is a leading DEX aggregator that sources liquidity across multiple decentralized exchanges (DEXes) on various EVM-compatible chains. It allows you to:
        - Get the best swap quote across supported DEXes
        - Estimate trade output and slippage
        - Prepare swap transactions with calldata
        - Fetch token and DEX metadata
        - Decode input data and track transactions
        """

    async def swap(self, params: OpenOceanQuoteRequest) -> SwapQuoteResponse:
        """
        Swap method to get a quote for swapping tokens on OpenOcean.
        """
        logger.info("Requesting OpenOcean quote", params=params.model_dump())
        try:
            url = f"{self.BASE_URL}/{params.chain}/quote"
            query = {
                "inTokenAddress": params.in_token_address,
                "outTokenAddress": params.out_token_address,
                "amountDecimals": params.amount_decimals,
                "slippage": params.slippage,
            }

            if params.gas_price_decimals:
                query["gasPriceDecimals"] = params.gas_price_decimals
            if params.enabled_dex_ids:
                query["enabledDexIds"] = params.enabled_dex_ids
            if params.disabled_dex_ids:
                query["disabledDexIds"] = params.disabled_dex_ids
            if params.account:
                query["account"] = params.account

            response = await self.client.get(url, params=query)
            response.raise_for_status()
            data = response.json()

            if data.get("code") != 200:
                raise RuntimeError(f"OpenOcean API error: {data}")
            return data["data"]
        except Exception as e:
            logger.exception("Failed OpenOcean quote fetch", error=str(e))
            raise

    async def get_token_list(self, chain: str) -> TokenListResponse:
        """
        Get list of available tokens on a given chain.
        """
        logger.info("Fetching OpenOcean token list", chain=chain)
        url = f"{self.BASE_URL}/{chain}/tokenList"
        try:
            response = await self.client.get(url)
            response.raise_for_status()
            return response.json().get("data", [])
        except Exception as e:
            logger.exception("Failed fetching token list", error=str(e))
            raise

    async def get_dex_list(self, chain: str) -> DexListResponse:
        """
        Get list of supported DEXes on a given chain.
        """
        logger.info("Fetching OpenOcean DEX list", chain=chain)
        url = f"{self.BASE_URL}/{chain}/dexList"
        try:
            response = await self.client.get(url)
            response.raise_for_status()
            return response.json().get("data", [])
        except Exception as e:
            logger.exception("Failed fetching DEX list", error=str(e))
            raise

    async def get_transaction(self, hash: str, chain: str) -> TransactionResponse:
        """
        Get transaction data by hash for a given chain.
        """
        logger.info("Fetching OpenOcean transaction", hash=hash, chain=chain)
        url = f"{self.BASE_URL}/{chain}/getTransaction"
        try:
            response = await self.client.get(url, params={"hash": hash})
            response.raise_for_status()
            return response.json().get("data", {})
        except Exception as e:
            logger.exception("Failed fetching transaction", error=str(e))
            raise

    async def close(self):
        await self.client.aclose()
