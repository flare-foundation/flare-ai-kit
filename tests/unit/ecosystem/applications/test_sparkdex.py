import warnings
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from hexbytes import HexBytes
from web3 import AsyncWeb3
from web3.contract.async_contract import AsyncContract

from flare_ai_kit.ecosystem import Contracts, EcosystemSettings
from flare_ai_kit.ecosystem.applications.sparkdex import (
    SparkDEX,
    get_swaprouter_abi,
    get_universalrouter_abi,
)
from flare_ai_kit.ecosystem.explorer import BlockExplorer
from flare_ai_kit.ecosystem.flare import Flare

# Suppress websockets deprecation warning
warnings.filterwarnings(
    "ignore", category=DeprecationWarning, module=r"websockets(\..*)?"
)


class TestSparkDEX:
    def setup_method(self):
        self.settings = MagicMock(spec=EcosystemSettings)
        self.settings.account_address = "0x" + "1" * 40

        self.contracts = MagicMock(spec=Contracts)
        self.contracts.flare = MagicMock()
        self.contracts.flare.sparkdex_universal_router = "0x" + "1" * 40
        self.contracts.flare.sparkdex_swap_router = "0x" + "2" * 40

        self.flare_explorer = MagicMock(spec=BlockExplorer)
        self.flare_provider = MagicMock(spec=Flare)
        self.flare_provider.address = self.settings.account_address
        self.flare_provider.w3 = MagicMock(spec=AsyncWeb3)
        self.flare_provider.w3.eth = MagicMock()
        self.flare_provider.w3.eth.contract = AsyncMock()

        self.univ_ct = MagicMock(spec=AsyncContract)
        self.swap_ct = MagicMock(spec=AsyncContract)

        self.sparkdex = SparkDEX(
            settings=self.settings,
            contracts=self.contracts,
            flare_explorer=self.flare_explorer,
            flare_provider=self.flare_provider,
            universalrouter_contract=self.univ_ct,
            swaprouter_contract=self.swap_ct,
        )

    @pytest.mark.asyncio
    @patch("flare_ai_kit.ecosystem.applications.sparkdex.get_universalrouter_abi")
    @patch("flare_ai_kit.ecosystem.applications.sparkdex.get_swaprouter_abi")
    async def test_create(self, mock_swap_abi, mock_univ_abi):
        mock_univ_abi.return_value = [{"name": "execute"}]
        mock_swap_abi.return_value = [{"name": "exactInputSingle"}]
        univ = MagicMock(spec=AsyncContract)
        swap = MagicMock(spec=AsyncContract)

        async def side_fx(address, abi):
            return (
                univ
                if address == self.contracts.flare.sparkdex_universal_router
                else swap
            )

        self.flare_provider.w3.eth.contract.side_effect = side_fx

        dex = await SparkDEX.create(
            settings=self.settings,
            contracts=self.contracts,
            flare_explorer=self.flare_explorer,
            flare_provider=self.flare_provider,
        )

        assert isinstance(dex, SparkDEX)
        assert await dex.universalrouter_contract == univ
        assert await dex.swaprouter_contract == swap

    def test_init(self):
        assert self.sparkdex.account_address == self.settings.account_address
        assert self.sparkdex.swaprouter_contract == self.swap_ct

    @pytest.mark.asyncio
    async def test_swap_no_approval(self):
        token_in = "0x" + "3" * 40
        token_out = "0x" + "4" * 40
        in_w = 1000
        out_min = 500
        ts = 1234567890

        self.flare_provider.erc20_allowance = AsyncMock(return_value=2 * in_w)
        self.flare_provider.w3.eth.get_block = AsyncMock(return_value={"timestamp": ts})
        self.flare_provider.build_transaction = AsyncMock(return_value={"tx": "x"})
        self.flare_provider.eth_call = AsyncMock(return_value=True)
        self.flare_provider.sign_and_send_transaction = AsyncMock(return_value="0xabc")
        self.flare_provider.w3.eth.wait_for_transaction_receipt = AsyncMock(
            return_value={"blockNumber": 1}
        )
        self.swap_ct.functions.exactInputSingle.return_value = MagicMock()

        tx = await self.sparkdex.swap_erc20_tokens(token_in, token_out, in_w, out_min)
        assert tx == "0xabc"
        self.flare_provider.w3.eth.wait_for_transaction_receipt.assert_called_with(
            HexBytes("0xabc")
        )

    @pytest.mark.asyncio
    async def test_swap_with_approval(self):
        token_in = "0x" + "3" * 40
        token_out = "0x" + "4" * 40
        in_w = 1000
        out_min = 500
        ts = 1234567890

        self.flare_provider.erc20_allowance = AsyncMock(return_value=0)
        self.flare_provider.erc20_approve = AsyncMock()
        self.flare_provider.w3.eth.get_block = AsyncMock(return_value={"timestamp": ts})
        self.flare_provider.build_transaction = AsyncMock(return_value={"tx": "x"})
        self.flare_provider.eth_call = AsyncMock(return_value=True)
        self.flare_provider.sign_and_send_transaction = AsyncMock(return_value="0xabc")
        self.flare_provider.w3.eth.wait_for_transaction_receipt = AsyncMock(
            return_value={"blockNumber": 1}
        )
        self.swap_ct.functions.exactInputSingle.return_value = MagicMock()

        tx = await self.sparkdex.swap_erc20_tokens(token_in, token_out, in_w, out_min)
        assert tx == "0xabc"
        self.flare_provider.erc20_approve.assert_called_with(
            token_address=token_in,
            spender_address=self.contracts.flare.sparkdex_swap_router,
            amount=in_w,
        )
        self.flare_provider.w3.eth.wait_for_transaction_receipt.assert_called_with(
            HexBytes("0xabc")
        )

    @pytest.mark.asyncio
    async def test_swap_simulation_fail(self):
        token_in = "0x" + "3" * 40
        token_out = "0x" + "4" * 40
        in_w = 1000
        out_min = 500
        ts = 1234567890

        self.flare_provider.erc20_allowance = AsyncMock(return_value=2 * in_w)
        self.flare_provider.w3.eth.get_block = AsyncMock(return_value={"timestamp": ts})
        self.flare_provider.build_transaction = AsyncMock(return_value={"tx": "x"})
        self.flare_provider.eth_call = AsyncMock(return_value=False)
        self.swap_ct.functions.exactInputSingle.return_value = MagicMock()

        with pytest.raises(
            Exception,
            match="We stop here because the simulated transaction was not sucessfull",
        ):
            await self.sparkdex.swap_erc20_tokens(token_in, token_out, in_w, out_min)

    def test_get_univ_abi(self):
        abi = get_universalrouter_abi()
        assert isinstance(abi, list) and len(abi) == 2

    def test_get_swap_abi(self):
        abi = get_swaprouter_abi()
        assert isinstance(abi, list) and abi[0]["name"] == "exactInputSingle"
