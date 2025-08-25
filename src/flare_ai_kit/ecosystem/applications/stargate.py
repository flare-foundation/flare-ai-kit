import httpx

from flare_ai_kit.ecosystem.applications.stargate_models import *


class StargateClient:
    def __init__(self):
        self.base_url = "https://stargate.finance/api/v1"

    async def describe_stargate_services(self) -> str:
        return """
        Stargate is a composable cross-chain liquidity transport protocol enabling seamless asset transfers between blockchains.
        It allows users to:
        - Swap tokens across different chains
        - Provide liquidity to cross-chain pools
        - Earn yield on cross-chain assets
        - Access a wide range of assets and chains through a single interface
        """

    async def quote(
        self,
        src_token: str,
        dst_token: str,
        src_chain_key: str,
        dst_chain_key: str,
        src_address: str,
        dst_address: str,
        src_amount: int,
        dst_amount_min: int,
    ) -> StargateQuoteResponse:
        params = {
            "srcToken": src_token,
            "dstToken": dst_token,
            "srcChainKey": src_chain_key,
            "dstChainKey": dst_chain_key,
            "srcAddress": src_address,
            "dstAddress": dst_address,
            "srcAmount": str(src_amount),
            "dstAmountMin": str(dst_amount_min),
        }

        async with httpx.AsyncClient() as client:
            response = await client.get(f"{self.base_url}/quotes", params=params)
            response.raise_for_status()
            return StargateQuoteResponse(**response.json())
