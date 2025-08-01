from web3 import AsyncHTTPProvider, AsyncWeb3

from flare_ai_kit.common.utils import load_abi
from flare_ai_kit.config import AppSettings
from flare_ai_kit.ecosystem.settings import Contracts


class SparkDEXClient:
    def __init__(self):
        self.settings = AppSettings().ecosystem
        self.client = AsyncWeb3(
            AsyncHTTPProvider(str(self.settings.web3_provider_url)),
        )
        self.contracts = Contracts()
        self.contract_address = self.contracts.flare.sparkdex_universal_router
        self.abi = load_abi("SparkDEXRouter")
        self.contract = self.client.eth.contract(
            address=self.contract_address,
            abi=self.abi,
        )

    async def describe_sparkDEX_services(self) -> str:
        return """
        SparkDEX is a decentralized exchange (DEX) on the Flare Network,
        enabling fast and secure token swaps with low fees.             
        """

    async def quote(self, amount_a: int, reserve_a: int, reserve_b: int) -> int:
        """
        Get a quote for swapping amount_a of token A to token B based on reserves.
        """
        return await self.contract.functions.quote(
            amount_a, reserve_a, reserve_b
        ).call()
