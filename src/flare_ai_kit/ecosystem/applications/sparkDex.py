import httpx
from eth_typing import ChecksumAddress
from web3 import AsyncHTTPProvider, AsyncWeb3
from web3.middleware import (
    ExtraDataToPOAMiddleware,  # pyright: ignore[reportUnknownVariableType]
)

from flare_ai_kit.common.utils import load_abi
from flare_ai_kit.config import AppSettings
from flare_ai_kit.ecosystem.settings import Contracts


class SparkDEXClient:
    def __init__(self):
        self.settings = AppSettings().ecosystem
        self.client = AsyncWeb3(
            AsyncHTTPProvider(str(self.settings.web3_provider_url)),
        )
        self.client.middleware_onion.inject(ExtraDataToPOAMiddleware, layer=0)  # pyright: ignore[reportUnknownArgumentType]
        self.contracts = Contracts()
        self.address = self.settings.account_address
        self.private_key = self.settings.account_private_key
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

    async def swap(
        self,
        amountIn: int,
        amountOutMin: int,
        path: list[ChecksumAddress],
        to: ChecksumAddress,
        deadline: int,
    ) -> str:
        """
        Execute a token swap on SparkDEX.
        """
        gas_price = self.client.to_wei(50, "gwei")
        if self.address is None:
            raise ValueError("Account address is not set")
        try:
            tx = await self.contract.functions.swapExactTokensForTokens(
                amountIn, amountOutMin, path, to, deadline
            ).build_transaction(
                {
                    "from": self.address,
                    "gas": 3000000,
                    "gasPrice": gas_price,
                    "nonce": await self.client.eth.get_transaction_count(self.address),
                }
            )
            if self.private_key is None:
                raise ValueError("Private key is not set")
            private_key = self.private_key.get_secret_value()
            signed = self.client.eth.account.sign_transaction(tx, private_key)
            tx_hash = await self.client.eth.send_raw_transaction(signed.raw_transaction)
            return tx_hash.hex()

        except Exception as e:
            print(f"Error during swap: {e}")
            raise RuntimeError("Swap transaction failed") from e

    async def get_sprk_price(self) -> int | str | None:
        url = "https://api.sparkdex.ai/price/latest?symbols=SPRK"
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(url)
                response.raise_for_status()  # Raise an exception for HTTP errors
                return response.json().get("SPRK")
            except httpx.HTTPStatusError as e:
                print(f"HTTP error occurred: {e}")
            except Exception as e:
                print(f"An error occurred: {e}")
