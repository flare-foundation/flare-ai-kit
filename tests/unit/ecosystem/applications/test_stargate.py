import warnings
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from web3 import Web3
from web3.contract.contract import Contract

from flare_ai_kit.ecosystem import ChainIdConfig, Contracts, EcosystemSettingsModel
from flare_ai_kit.ecosystem.applications.stargate import Stargate
from flare_ai_kit.ecosystem.explorer import BlockExplorer
from flare_ai_kit.ecosystem.flare import Flare

# Suppress all websockets warnings
warnings.filterwarnings("ignore", category=DeprecationWarning, module=r"websockets.*")


class TestStargate:
    """Test suite for the Stargate class, covering initialization and cross-chain ETH transfers."""

    def setup_method(self):
        """Set up test fixtures before each test method.

        Initializes mock objects for settings, contracts, chains, explorer, provider, and logger, and creates a Stargate instance.
        """
        # Mock structlog to avoid logging issues
        self.logger_patcher = patch("structlog.get_logger", return_value=MagicMock())
        self.logger_patcher.start()

        self.settings = MagicMock(spec=EcosystemSettingsModel)
        self.settings.account_address = "0x9e8318cc9c83427870ed8994d818Ba7A92739B99"
        self.settings.account_private_key = (
            "0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef"
        )

        self.contracts = MagicMock(spec=Contracts)
        self.contracts.flare = MagicMock()
        self.contracts.flare.stargate_StargateOFTETH = (
            "0x5555555555555555555555555555555555555555"
        )
        self.contracts.flare.weth = "0x6666666666666666666666666666666666666666"

        self.chains = MagicMock(spec=ChainIdConfig)
        self.chains.chains = MagicMock()
        self.chains.chains.base = 8453  # Example chain ID for Base

        self.flare_explorer = MagicMock(spec=BlockExplorer)
        self.flare_provider = MagicMock(spec=Flare)
        self.flare_provider.address = "0x9e8318cc9c83427870ed8994d818Ba7A92739B99"
        self.flare_provider.w3 = MagicMock(spec=Web3)
        self.flare_provider.w3.eth = MagicMock()

        self.oft_abi = [
            {
                "name": "quoteOFT",
                "inputs": [{"type": "tuple", "components": []}],
                "outputs": [
                    {"type": "tuple", "components": []},
                    {"type": "tuple", "components": []},
                    {"type": "tuple", "components": []},
                ],
                "stateMutability": "view",
                "type": "function",
            },
            {
                "name": "quoteSend",
                "inputs": [{"type": "tuple", "components": []}, {"type": "bool"}],
                "outputs": [{"type": "uint256"}, {"type": "uint256"}],
                "stateMutability": "view",
                "type": "function",
            },
            {
                "name": "send",
                "inputs": [
                    {"type": "tuple", "components": []},
                    {"type": "tuple", "components": []},
                    {"type": "address"},
                ],
                "outputs": [],
                "stateMutability": "payable",
                "type": "function",
            },
        ]

        # Initialize Stargate with mocked oft_contract
        self.stargate = Stargate(
            settings=self.settings,
            contracts=self.contracts,
            chains=self.chains,
            flare_explorer=self.flare_explorer,
            flare_provider=self.flare_provider,
            oft_abi=self.oft_abi,
        )
        self.stargate.oft_contract = MagicMock(spec=Contract, functions=MagicMock())

    def teardown_method(self):
        """Clean up by stopping the logger patcher."""
        self.logger_patcher.stop()

    @pytest.mark.asyncio
    async def test_create(self):
        """Test the create classmethod to ensure it initializes a Stargate instance correctly."""
        mock_oft_abi = [{"name": "someFunction"}]
        mock_oft_contract = MagicMock(spec=Contract, functions=MagicMock())
        self.flare_explorer.get_contract_abi = AsyncMock(return_value=mock_oft_abi)
        self.flare_provider.w3.eth.contract = MagicMock(return_value=mock_oft_contract)

        stargate = await Stargate.create(
            settings=self.settings,
            contracts=self.contracts,
            chains=self.chains,
            flare_explorer=self.flare_explorer,
            flare_provider=self.flare_provider,
        )

        assert isinstance(stargate, Stargate)
        assert stargate.contracts == self.contracts
        assert stargate.chains == self.chains
        assert stargate.flare_explorer == self.flare_explorer
        assert stargate.flare_provider == self.flare_provider
        assert stargate.account_address == self.settings.account_address
        assert stargate.account_private_key == self.settings.account_private_key
        assert stargate.oft_abi == mock_oft_abi
        assert stargate.oft_contract == mock_oft_contract
        self.flare_explorer.get_contract_abi.assert_called_with(
            self.contracts.flare.stargate_StargateOFTETH
        )
        self.flare_provider.w3.eth.contract.assert_called_with(
            address=self.contracts.flare.stargate_StargateOFTETH, abi=mock_oft_abi
        )

    def test_init_valid(self):
        """Test the __init__ method with valid settings to ensure attributes are set correctly."""
        assert self.stargate.contracts == self.contracts
        assert self.stargate.chains == self.chains
        assert self.stargate.flare_explorer == self.flare_explorer
        assert self.stargate.flare_provider == self.flare_provider
        assert self.stargate.account_address == self.settings.account_address
        assert self.stargate.account_private_key == self.settings.account_private_key
        assert self.stargate.oft_abi == self.oft_abi
        self.flare_provider.w3.eth.contract.assert_called_with(
            address=self.contracts.flare.stargate_StargateOFTETH, abi=self.oft_abi
        )

    def test_init_missing_account_details(self):
        """Test the __init__ method with missing account details to ensure it raises an Exception."""
        settings_missing = MagicMock(spec=EcosystemSettingsModel)
        settings_missing.account_address = ""
        settings_missing.account_private_key = ""

        with pytest.raises(
            Exception,
            match="Please set self.account_private_key and self.account_address in your .env file.",
        ):
            Stargate(
                settings=settings_missing,
                contracts=self.contracts,
                chains=self.chains,
                flare_explorer=self.flare_explorer,
                flare_provider=self.flare_provider,
                oft_abi=self.oft_abi,
            )

    @pytest.mark.asyncio
    async def test_bridge_weth_to_chain_success(self):
        """Test bridge_weth_to_chain with a successful transaction simulation."""
        desired_amount_wei = 1000000000000000000  # 1 ETH
        min_amount_wei = int(desired_amount_wei * (1 - 0.01))  # 1% slippage
        block_number = 123
        tx_hash = "0x1234567890abcdef"
        oft_limits = (500000000000000000, 5000000000000000000)  # 0.5 ETH min, 5 ETH max
        oft_fee_details = (100, 200, 300)
        oft_receipt = (desired_amount_wei, 0)
        messaging_fee = (1000000000000000, 0)  # nativeFee, lzTokenFee
        weth_balance = desired_amount_wei * 2
        allowance = desired_amount_wei // 2

        to_address = Web3.to_bytes(
            hexstr="0x000000000000000000000000" + self.settings.account_address[2:]
        )
        send_param = (
            self.chains.chains.base,
            to_address,
            desired_amount_wei,
            min_amount_wei,
            b"",
            b"",
            b"",
        )

        self.stargate.oft_contract.functions.quoteOFT = MagicMock()
        self.stargate.oft_contract.functions.quoteSend = MagicMock()
        self.stargate.oft_contract.functions.send = MagicMock()
        self.stargate.oft_contract.functions.quoteOFT.return_value.call = AsyncMock(
            return_value=(oft_limits, oft_fee_details, oft_receipt)
        )
        self.stargate.oft_contract.functions.quoteSend.return_value.call = AsyncMock(
            return_value=messaging_fee
        )
        self.flare_provider.erc20_balanceOf = AsyncMock(return_value=weth_balance)
        self.flare_provider.erc20_allowance = AsyncMock(return_value=allowance)
        self.flare_provider.erc20_approve = AsyncMock(return_value="0xapprovehash")
        self.flare_provider.build_transaction = AsyncMock(
            return_value={"tx": "stubbed"}
        )
        self.flare_provider.eth_call = AsyncMock(return_value=True)
        self.flare_provider.sign_and_send_transaction = AsyncMock(return_value=tx_hash)
        self.flare_provider.w3.eth.wait_for_transaction_receipt = AsyncMock(
            return_value={"blockNumber": block_number}
        )

        result = await self.stargate.bridge_weth_to_chain(desired_amount_wei)

        assert result == tx_hash
        self.stargate.oft_contract.functions.quoteOFT.assert_called_with(send_param)
        self.stargate.oft_contract.functions.quoteSend.assert_called_with(
            send_param, False
        )
        self.flare_provider.erc20_balanceOf.assert_called_with(
            self.stargate.account_address, self.contracts.flare.weth
        )
        self.flare_provider.erc20_allowance.assert_called_with(
            owner_address=self.stargate.account_address,
            token_address=self.contracts.flare.weth,
            spender_address=self.contracts.flare.stargate_StargateOFTETH,
        )
        self.flare_provider.erc20_approve.assert_called_with(
            token_address=self.contracts.flare.weth,
            spender_address=self.contracts.flare.stargate_StargateOFTETH,
            amount=desired_amount_wei,
        )
        self.flare_provider.build_transaction.assert_called_with(
            function_call=self.stargate.oft_contract.functions.send.return_value,
            from_addr=self.flare_provider.address,
            custom_params={"value": messaging_fee[0]},
        )
        self.flare_provider.eth_call.assert_called_with(
            contract_abi=self.oft_abi, call_tx={"tx": "stubbed"}
        )
        self.flare_provider.sign_and_send_transaction.assert_called_with(
            {"tx": "stubbed"}
        )
        self.flare_provider.w3.eth.wait_for_transaction_receipt.assert_called_with(
            tx_hash
        )

    @pytest.mark.asyncio
    async def test_bridge_weth_to_chain_exceeds_max_limit(self):
        """Test bridge_weth_to_chain when the desired amount exceeds the maximum limit."""
        desired_amount_wei = 6000000000000000000  # 6 ETH
        min_amount_wei = int(desired_amount_wei * (1 - 0.01))  # 1% slippage
        oft_limits = (500000000000000000, 5000000000000000000)  # 0.5 ETH min, 5 ETH max
        oft_fee_details = (100, 200, 300)
        oft_receipt = (desired_amount_wei, 0)
        to_address = Web3.to_bytes(
            hexstr="0x000000000000000000000000" + self.settings.account_address[2:]
        )
        send_param = (
            self.chains.chains.base,
            to_address,
            desired_amount_wei,
            min_amount_wei,
            b"",
            b"",
            b"",
        )

        self.stargate.oft_contract.functions.quoteOFT = MagicMock()
        self.stargate.oft_contract.functions.quoteOFT.return_value.call = AsyncMock(
            return_value=(oft_limits, oft_fee_details, oft_receipt)
        )

        result = await self.stargate.bridge_weth_to_chain(desired_amount_wei)

        assert result is None
        self.stargate.oft_contract.functions.quoteOFT.assert_called_with(send_param)
        assert (
            not hasattr(self.stargate.oft_contract.functions, "quoteSend")
            or not self.stargate.oft_contract.functions.quoteSend.called
        )
        assert not self.flare_provider.erc20_balanceOf.called
        assert not self.flare_provider.erc20_allowance.called
        assert not self.flare_provider.erc20_approve.called
        assert not self.flare_provider.build_transaction.called
        assert not self.flare_provider.eth_call.called
        assert not self.flare_provider.sign_and_send_transaction.called
        assert not self.flare_provider.w3.eth.wait_for_transaction_receipt.called

    @pytest.mark.asyncio
    async def test_bridge_weth_to_chain_below_min_limit(self):
        """Test bridge_weth_to_chain when the desired amount is below the minimum limit."""
        desired_amount_wei = 100000000000000000  # 0.1 ETH
        min_amount_wei = int(desired_amount_wei * (1 - 0.01))  # 1% slippage
        oft_limits = (500000000000000000, 5000000000000000000)  # 0.5 ETH min, 5 ETH max
        oft_fee_details = (100, 200, 300)
        oft_receipt = (desired_amount_wei, 0)
        to_address = Web3.to_bytes(
            hexstr="0x000000000000000000000000" + self.settings.account_address[2:]
        )
        send_param = (
            self.chains.chains.base,
            to_address,
            desired_amount_wei,
            min_amount_wei,
            b"",
            b"",
            b"",
        )

        self.stargate.oft_contract.functions.quoteOFT = MagicMock()
        self.stargate.oft_contract.functions.quoteOFT.return_value.call = AsyncMock(
            return_value=(oft_limits, oft_fee_details, oft_receipt)
        )

        result = await self.stargate.bridge_weth_to_chain(desired_amount_wei)

        assert result is None
        self.stargate.oft_contract.functions.quoteOFT.assert_called_with(send_param)
        assert (
            not hasattr(self.stargate.oft_contract.functions, "quoteSend")
            or not self.stargate.oft_contract.functions.quoteSend.called
        )
        assert not self.flare_provider.erc20_balanceOf.called
        assert not self.flare_provider.erc20_allowance.called
        assert not self.flare_provider.erc20_approve.called
        assert not self.flare_provider.build_transaction.called
        assert not self.flare_provider.eth_call.called
        assert not self.flare_provider.sign_and_send_transaction.called
        assert not self.flare_provider.w3.eth.wait_for_transaction_receipt.called

    @pytest.mark.asyncio
    async def test_bridge_weth_to_chain_failed_simulation(self):
        """Test bridge_weth_to_chain with a failed transaction simulation."""
        desired_amount_wei = 1000000000000000000  # 1 ETH
        min_amount_wei = int(desired_amount_wei * (1 - 0.01))  # 1% slippage
        oft_limits = (500000000000000000, 5000000000000000000)  # 0.5 ETH min, 5 ETH max
        oft_fee_details = (100, 200, 300)
        oft_receipt = (desired_amount_wei, 0)
        messaging_fee = (1000000000000000, 0)  # nativeFee, lzTokenFee
        weth_balance = desired_amount_wei * 2
        allowance = desired_amount_wei // 2
        to_address = Web3.to_bytes(
            hexstr="0x000000000000000000000000" + self.settings.account_address[2:]
        )
        send_param = (
            self.chains.chains.base,
            to_address,
            desired_amount_wei,
            min_amount_wei,
            b"",
            b"",
            b"",
        )

        self.stargate.oft_contract.functions.quoteOFT = MagicMock()
        self.stargate.oft_contract.functions.quoteSend = MagicMock()
        self.stargate.oft_contract.functions.send = MagicMock()
        self.stargate.oft_contract.functions.quoteOFT.return_value.call = AsyncMock(
            return_value=(oft_limits, oft_fee_details, oft_receipt)
        )
        self.stargate.oft_contract.functions.quoteSend.return_value.call = AsyncMock(
            return_value=messaging_fee
        )
        self.flare_provider.erc20_balanceOf = AsyncMock(return_value=weth_balance)
        self.flare_provider.erc20_allowance = AsyncMock(return_value=allowance)
        self.flare_provider.erc20_approve = AsyncMock(return_value="0xapprovehash")
        self.flare_provider.build_transaction = AsyncMock(
            return_value={"tx": "stubbed"}
        )
        self.flare_provider.eth_call = AsyncMock(return_value=False)

        result = await self.stargate.bridge_weth_to_chain(desired_amount_wei)

        assert result is None
        self.stargate.oft_contract.functions.quoteOFT.assert_called_with(send_param)
        self.stargate.oft_contract.functions.quoteSend.assert_called_with(
            send_param, False
        )
        self.flare_provider.erc20_balanceOf.assert_called_with(
            self.stargate.account_address, self.contracts.flare.weth
        )
        self.flare_provider.erc20_allowance.assert_called_with(
            owner_address=self.stargate.account_address,
            token_address=self.contracts.flare.weth,
            spender_address=self.contracts.flare.stargate_StargateOFTETH,
        )
        self.flare_provider.erc20_approve.assert_called_with(
            token_address=self.contracts.flare.weth,
            spender_address=self.contracts.flare.stargate_StargateOFTETH,
            amount=desired_amount_wei,
        )
        self.flare_provider.build_transaction.assert_called_with(
            function_call=self.stargate.oft_contract.functions.send.return_value,
            from_addr=self.flare_provider.address,
            custom_params={"value": messaging_fee[0]},
        )
        self.flare_provider.eth_call.assert_called_with(
            contract_abi=self.oft_abi, call_tx={"tx": "stubbed"}
        )
        assert not self.flare_provider.sign_and_send_transaction.called
        assert not self.flare_provider.w3.eth.wait_for_transaction_receipt.called

    @pytest.mark.asyncio
    async def test_bridge_weth_to_chain_zero_amount(self):
        """Test bridge_weth_to_chain with zero amount (no error expected per provided stargate.py)."""
        desired_amount_wei = 0
        min_amount_wei = 0
        oft_limits = (500000000000000000, 5000000000000000000)  # 0.5 ETH min, 5 ETH max
        oft_fee_details = (100, 200, 300)
        oft_receipt = (desired_amount_wei, 0)
        to_address = Web3.to_bytes(
            hexstr="0x000000000000000000000000" + self.settings.account_address[2:]
        )
        send_param = (
            self.chains.chains.base,
            to_address,
            desired_amount_wei,
            min_amount_wei,
            b"",
            b"",
            b"",
        )

        self.stargate.oft_contract.functions.quoteOFT = MagicMock()
        self.stargate.oft_contract.functions.quoteOFT.return_value.call = AsyncMock(
            return_value=(oft_limits, oft_fee_details, oft_receipt)
        )

        result = await self.stargate.bridge_weth_to_chain(desired_amount_wei)

        assert result is None
        self.stargate.oft_contract.functions.quoteOFT.assert_called_with(send_param)
        assert (
            not hasattr(self.stargate.oft_contract.functions, "quoteSend")
            or not self.stargate.oft_contract.functions.quoteSend.called
        )
        assert not self.flare_provider.erc20_balanceOf.called
        assert not self.flare_provider.erc20_allowance.called
        assert not self.flare_provider.erc20_approve.called
        assert not self.flare_provider.build_transaction.called
        assert not self.flare_provider.eth_call.called
        assert not self.flare_provider.sign_and_send_transaction.called
        assert not self.flare_provider.w3.eth.wait_for_transaction_receipt.called
