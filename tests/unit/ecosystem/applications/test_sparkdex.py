import warnings
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from web3 import AsyncWeb3
from web3.contract.async_contract import AsyncContract

from flare_ai_kit.ecosystem import Contracts, EcosystemSettingsModel
from flare_ai_kit.ecosystem.applications.sparkdex import (
    SparkDEX,
    get_swaprouter_abi,
    get_universalrouter_abi,
)
from flare_ai_kit.ecosystem.explorer import BlockExplorer
from flare_ai_kit.ecosystem.flare import Flare

# Suppress websockets deprecation warning with stricter module matching
warnings.filterwarnings(
    "ignore", category=DeprecationWarning, module=r"websockets(\..*)?"
)


class TestSparkDEX:
    """
    Test suite for the SparkDEX class, covering initialization, token swaps, and ABI retrieval.
    """

    def setup_method(self):
        """
        Set up test fixtures before each test method.

        Initializes mock objects for settings, contracts, explorer, and provider, and creates a SparkDEX instance.
        """
        self.settings = MagicMock(spec=EcosystemSettingsModel)
        self.settings.account_address = "0x9e8318cc9c83427870ed8994d818Ba7A92739B99"
        self.settings.account_private_key = (
            "0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef"
        )

        self.contracts = MagicMock(spec=Contracts)
        self.contracts.flare = MagicMock()
        self.contracts.flare.sparkdex_universal_router = (
            "0x1111111111111111111111111111111111111111"
        )
        self.contracts.flare.sparkdex_swap_router = (
            "0x2222222222222222222222222222222222222222"
        )

        self.flare_explorer = MagicMock(spec=BlockExplorer)
        self.flare_provider = MagicMock(spec=Flare)
        self.flare_provider.address = "0x9e8318cc9c83427870ed8994d818Ba7A92739B99"
        self.flare_provider.w3 = MagicMock(spec=AsyncWeb3)
        self.flare_provider.w3.eth = MagicMock()
        # Initialize contract mock as AsyncMock to match async contract calls
        self.flare_provider.w3.eth.contract = AsyncMock()

        self.universalrouter_contract = MagicMock(
            spec=AsyncContract, functions=MagicMock()
        )
        self.swaprouter_contract = MagicMock(spec=AsyncContract, functions=MagicMock())

        self.sparkdex = SparkDEX(
            settings=self.settings,
            contracts=self.contracts,
            flare_explorer=self.flare_explorer,
            flare_provider=self.flare_provider,
            universalrouter_contract=self.universalrouter_contract,
            swaprouter_contract=self.swaprouter_contract,
        )

    @pytest.mark.asyncio
    @patch("flare_ai_kit.ecosystem.applications.sparkdex.get_universalrouter_abi")
    @patch("flare_ai_kit.ecosystem.applications.sparkdex.get_swaprouter_abi")
    async def test_create(self, mock_get_swaprouter_abi, mock_get_universalrouter_abi):
        """
        Test the create classmethod to ensure it initializes a SparkDEX instance correctly.
        """
        mock_get_universalrouter_abi.return_value = [{"name": "execute"}]
        mock_get_swaprouter_abi.return_value = [{"name": "exactInputSingle"}]
        mock_universal_contract = MagicMock(spec=AsyncContract, functions=MagicMock())
        mock_swap_contract = MagicMock(spec=AsyncContract, functions=MagicMock())

        # Define an async side_effect to return coroutines that resolve to mocked contracts
        async def contract_side_effect(*args, **kwargs):
            if kwargs["address"] == self.contracts.flare.sparkdex_universal_router:
                return mock_universal_contract
            if kwargs["address"] == self.contracts.flare.sparkdex_swap_router:
                return mock_swap_contract
            raise ValueError("Unexpected contract address")

        self.flare_provider.w3.eth.contract.side_effect = contract_side_effect

        sparkdex = await SparkDEX.create(
            settings=self.settings,
            contracts=self.contracts,
            flare_explorer=self.flare_explorer,
            flare_provider=self.flare_provider,
        )

        assert isinstance(sparkdex, SparkDEX)
        assert sparkdex.settings == self.settings
        assert sparkdex.contracts == self.contracts
        assert sparkdex.flare_explorer == self.flare_explorer
        assert sparkdex.flare_provider == self.flare_provider
        assert sparkdex.account_address == self.flare_provider.address
        assert sparkdex.universalrouter_contract == mock_universal_contract
        assert sparkdex.swaprouter_contract == mock_swap_contract
        self.flare_provider.w3.eth.contract.assert_any_call(
            address=self.contracts.flare.sparkdex_universal_router,
            abi=mock_get_universalrouter_abi.return_value,
        )
        self.flare_provider.w3.eth.contract.assert_any_call(
            address=self.contracts.flare.sparkdex_swap_router,
            abi=mock_get_swaprouter_abi.return_value,
        )

    def test_init(self):
        """
        Test the __init__ method to ensure attributes are set correctly.
        """
        assert self.sparkdex.settings == self.settings
        assert self.sparkdex.contracts == self.contracts
        assert self.sparkdex.flare_explorer == self.flare_explorer
        assert self.sparkdex.flare_provider == self.flare_provider
        assert self.sparkdex.account_address == self.flare_provider.address
        assert self.sparkdex.universalrouter_contract == self.universalrouter_contract
        assert self.swaprouter_contract == self.swaprouter_contract

    @pytest.mark.asyncio
    async def test_swap_erc20_tokens_success_no_approval(self):
        """
        Test swap_erc20_tokens with sufficient allowance, not requiring approval.
        """
        token_in_addr = "0x3333333333333333333333333333333333333333"
        token_out_addr = "0x4444444444444444444444444444444444444444"
        amount_in = 1.0
        amount_out_min = 0.5
        amount_in_wei = 1000000000000000000  # 1 ether
        amount_out_min_wei = 500000000000000000  # 0.5 ether
        block_timestamp = 1697059200

        self.flare_provider.w3.to_wei.side_effect = [amount_in_wei, amount_out_min_wei]
        self.flare_provider.erc20_allowance = AsyncMock(return_value=amount_in_wei * 2)
        self.flare_provider.w3.eth.get_block = AsyncMock(
            return_value={"timestamp": block_timestamp}
        )
        self.flare_provider.build_transaction = AsyncMock(return_value={"tx": "mocked"})
        self.flare_provider.eth_call = AsyncMock(return_value=True)
        self.flare_provider.sign_and_send_transaction = AsyncMock(
            return_value="0x1234567890abcdef"
        )
        self.flare_provider.w3.eth.wait_for_transaction_receipt = AsyncMock(
            return_value={"blockNumber": 123, "logs": []}
        )
        self.swaprouter_contract.functions.exactInputSingle.return_value = MagicMock()

        tx_hash = await self.sparkdex.swap_erc20_tokens(
            token_in_addr, token_out_addr, amount_in, amount_out_min
        )

        assert tx_hash == "0x1234567890abcdef"
        self.flare_provider.erc20_allowance.assert_called_with(
            owner_address=self.flare_provider.address,
            token_address=token_in_addr,
            spender_address=self.contracts.flare.sparkdex_swap_router,
        )
        assert not self.flare_provider.erc20_approve.called
        self.flare_provider.w3.eth.get_block.assert_called_with("latest")
        self.swaprouter_contract.functions.exactInputSingle.assert_called_with(
            (
                token_in_addr,
                token_out_addr,
                500,  # fee_tier
                self.flare_provider.address,
                block_timestamp + 300,
                amount_in_wei,
                amount_out_min_wei,
                0,
            )
        )
        self.flare_provider.build_transaction.assert_called_with(
            self.swaprouter_contract.functions.exactInputSingle.return_value,
            self.flare_provider.address,
            custom_params={"type": 2},
        )
        self.flare_provider.eth_call.assert_called_once()
        self.flare_provider.sign_and_send_transaction.assert_called_once()
        self.flare_provider.w3.eth.wait_for_transaction_receipt.assert_called_with(
            "0x1234567890abcdef"
        )

    @pytest.mark.asyncio
    async def test_swap_erc20_tokens_success_with_approval(self):
        """
        Test swap_erc20_tokens with insufficient allowance, requiring approval.
        """
        token_in_addr = "0x3333333333333333333333333333333333333333"
        token_out_addr = "0x4444444444444444444444444444444444444444"
        amount_in = 1.0
        amount_out_min = 0.5
        amount_in_wei = 1000000000000000000  # 1 ether
        amount_out_min_wei = 500000000000000000  # 0.5 ether
        block_timestamp = 1697059200

        self.flare_provider.w3.to_wei.side_effect = [amount_in_wei, amount_out_min_wei]
        self.flare_provider.erc20_allowance = AsyncMock(return_value=0)
        self.flare_provider.erc20_approve = AsyncMock(return_value="0xabcdef1234567890")
        self.flare_provider.w3.eth.get_block = AsyncMock(
            return_value={"timestamp": block_timestamp}
        )
        self.flare_provider.build_transaction = AsyncMock(return_value={"tx": "mocked"})
        self.flare_provider.eth_call = AsyncMock(return_value=True)
        self.flare_provider.sign_and_send_transaction = AsyncMock(
            return_value="0x1234567890abcdef"
        )
        self.flare_provider.w3.eth.wait_for_transaction_receipt = AsyncMock(
            return_value={"blockNumber": 123, "logs": []}
        )
        self.swaprouter_contract.functions.exactInputSingle.return_value = MagicMock()

        tx_hash = await self.sparkdex.swap_erc20_tokens(
            token_in_addr, token_out_addr, amount_in, amount_out_min
        )

        assert tx_hash == "0x1234567890abcdef"
        self.flare_provider.erc20_allowance.assert_called_with(
            owner_address=self.flare_provider.address,
            token_address=token_in_addr,
            spender_address=self.contracts.flare.sparkdex_swap_router,
        )
        self.flare_provider.erc20_approve.assert_called_with(
            token_address=token_in_addr,
            spender_address=self.contracts.flare.sparkdex_swap_router,
            amount=amount_in_wei,
        )
        self.flare_provider.w3.eth.get_block.assert_called_with("latest")
        self.swaprouter_contract.functions.exactInputSingle.assert_called_with(
            (
                token_in_addr,
                token_out_addr,
                500,  # fee_tier
                self.flare_provider.address,
                block_timestamp + 300,
                amount_in_wei,
                amount_out_min_wei,
                0,
            )
        )
        self.flare_provider.build_transaction.assert_called_with(
            self.swaprouter_contract.functions.exactInputSingle.return_value,
            self.flare_provider.address,
            custom_params={"type": 2},
        )
        self.flare_provider.eth_call.assert_called_once()
        self.flare_provider.sign_and_send_transaction.assert_called_once()
        self.flare_provider.w3.eth.wait_for_transaction_receipt.assert_called_with(
            "0x1234567890abcdef"
        )

    @pytest.mark.asyncio
    async def test_swap_erc20_tokens_failed_simulation(self):
        """
        Test swap_erc20_tokens with a failed transaction simulation.
        """
        token_in_addr = "0x3333333333333333333333333333333333333333"
        token_out_addr = "0x4444444444444444444444444444444444444444"
        amount_in = 1.0
        amount_out_min = 0.5
        amount_in_wei = 1000000000000000000  # 1 ether
        amount_out_min_wei = 500000000000000000  # 0.5 ether
        block_timestamp = 1697059200

        self.flare_provider.w3.to_wei.side_effect = [amount_in_wei, amount_out_min_wei]
        self.flare_provider.erc20_allowance = AsyncMock(return_value=amount_in_wei * 2)
        self.flare_provider.w3.eth.get_block = AsyncMock(
            return_value={"timestamp": block_timestamp}
        )
        self.flare_provider.build_transaction = AsyncMock(return_value={"tx": "mocked"})
        self.flare_provider.eth_call = AsyncMock(return_value=False)
        self.swaprouter_contract.functions.exactInputSingle.return_value = MagicMock()

        result = await self.sparkdex.swap_erc20_tokens(
            token_in_addr, token_out_addr, amount_in, amount_out_min
        )

        assert result is None
        self.flare_provider.erc20_allowance.assert_called_once()
        assert not self.flare_provider.erc20_approve.called
        self.flare_provider.w3.eth.get_block.assert_called_once()
        self.swaprouter_contract.functions.exactInputSingle.assert_called_once()
        self.flare_provider.build_transaction.assert_called_once()
        self.flare_provider.eth_call.assert_called_once()
        assert not self.flare_provider.sign_and_send_transaction.called
        assert not self.flare_provider.w3.eth.wait_for_transaction_receipt.called

    def test_get_universalrouter_abi(self):
        """
        Test get_universalrouter_abi returns the correct ABI.
        """
        abi = get_universalrouter_abi()
        assert isinstance(abi, list)
        assert len(abi) == 2
        assert all(item["name"] == "execute" for item in abi)
        assert any("deadline" not in item["inputs"] for item in abi)
        assert any(
            "deadline" in [input["name"] for input in item["inputs"]] for item in abi
        )

    def test_get_swaprouter_abi(self):
        """
        Test get_swaprouter_abi returns the correct ABI.
        """
        abi = get_swaprouter_abi()
        assert isinstance(abi, list)
        assert len(abi) == 1
        assert abi[0]["name"] == "exactInputSingle"
        assert len(abi[0]["inputs"][0]["components"]) == 8
        assert abi[0]["outputs"][0]["name"] == "amountOut"
