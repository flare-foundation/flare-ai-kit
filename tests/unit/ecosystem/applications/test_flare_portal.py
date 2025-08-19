import warnings
from unittest.mock import AsyncMock, MagicMock

import pytest
from typing import cast
from web3 import Web3
from web3.types import TxParams
from web3.contract.contract import Contract

from flare_ai_kit.ecosystem import Contracts, EcosystemSettings
from flare_ai_kit.ecosystem.applications.flare_portal import FlarePortal
from flare_ai_kit.ecosystem.explorer import BlockExplorer
from flare_ai_kit.ecosystem.flare import Flare

# Suppress websockets warnings
warnings.filterwarnings("ignore", category=DeprecationWarning, module=r"websockets.*")


class TestFlarePortal:
    """Test suite for the FlarePortal class, covering initialization and WFLR operations."""

    def setup_method(self):
        """Set up test fixtures before each test method."""
        self.settings = MagicMock(spec=EcosystemSettings)
        self.settings.account_address = "0x9e8318cc9c83427870ed8994d818Ba7A92739B99"
        self.settings.account_private_key = (
            "0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef"
        )

        self.contracts = MagicMock(spec=Contracts)
        self.contracts.flare = MagicMock()
        self.contracts.flare.wflr = "0x6666666666666666666666666666666666666666"

        self.flare_explorer = MagicMock(spec=BlockExplorer)
        self.flare_provider = MagicMock(spec=Flare)
        self.flare_provider.address = "0x9e8318cc9c83427870ed8994d818Ba7A92739B99"
        self.flare_provider.w3 = MagicMock(spec=Web3)
        self.flare_provider.w3.eth = MagicMock()

        self.wflr_abi = [
            {
                "name": "deposit",
                "inputs": [],
                "outputs": [],
                "stateMutability": "payable",
                "type": "function",
            },
            {
                "name": "withdraw",
                "inputs": [{"type": "uint256"}],
                "outputs": [],
                "stateMutability": "nonpayable",
                "type": "function",
            },
        ]

        self.flare_portal = FlarePortal(
            settings=self.settings,
            contracts=self.contracts,
            flare_explorer=self.flare_explorer,
            flare_provider=self.flare_provider,
            wflr_abi=self.wflr_abi,
        )
        self.flare_portal.wflr_contract = MagicMock(
            spec=Contract, functions=MagicMock()
        )

    @pytest.mark.asyncio
    async def test_create(self):
        """Test the create classmethod to ensure it initializes a FlarePortal instance correctly."""
        mock_wflr_abi = [{"name": "deposit"}, {"name": "withdraw"}]
        mock_wflr_contract = MagicMock(spec=Contract, functions=MagicMock())
        self.flare_explorer.get_contract_abi = AsyncMock(return_value=mock_wflr_abi)
        self.flare_provider.w3.eth.contract = MagicMock(return_value=mock_wflr_contract)

        flare_portal = await FlarePortal.create(
            settings=self.settings,
            contracts=self.contracts,
            flare_explorer=self.flare_explorer,
            flare_provider=self.flare_provider,
        )

        assert isinstance(flare_portal, FlarePortal)
        assert flare_portal.settings == self.settings
        assert flare_portal.contracts == self.contracts
        assert flare_portal.flare_explorer == self.flare_explorer
        assert flare_portal.flare_provider == self.flare_provider
        assert flare_portal.account_address == self.flare_provider.address
        assert flare_portal.wflr_abi == mock_wflr_abi
        assert flare_portal.wflr_contract == mock_wflr_contract
        self.flare_explorer.get_contract_abi.assert_called_with(
            self.contracts.flare.wflr
        )
        self.flare_provider.w3.eth.contract.assert_called_with(
            address=self.contracts.flare.wflr, abi=mock_wflr_abi
        )

    def test_init_valid(self):
        """Test the __init__ method with valid settings to ensure attributes are set correctly."""
        assert self.flare_portal.settings == self.settings
        assert self.flare_portal.contracts == self.contracts
        assert self.flare_portal.flare_explorer == self.flare_explorer
        assert self.flare_portal.flare_provider == self.flare_provider
        assert self.flare_portal.account_address == self.flare_provider.address
        assert self.flare_portal.wflr_abi == self.wflr_abi
        self.flare_provider.w3.eth.contract.assert_called_with(
            address=self.contracts.flare.wflr, abi=self.wflr_abi
        )

    def test_init_missing_address(self):
        """Test the __init__ method with missing account address to ensure it raises an Exception."""
        flare_provider_no_address = MagicMock(spec=Flare)
        flare_provider_no_address.address = None
        flare_provider_no_address.w3 = MagicMock(spec=Web3)
        flare_provider_no_address.w3.eth = MagicMock()

        with pytest.raises(
            Exception, match="Flare provider must have a valid account address set."
        ):
            FlarePortal(
                settings=self.settings,
                contracts=self.contracts,
                flare_explorer=self.flare_explorer,
                flare_provider=flare_provider_no_address,
                wflr_abi=self.wflr_abi,
            )

    @pytest.mark.asyncio
    async def test_wrap_flr_to_wflr_success(self):
        """Test wrap_flr_to_wflr with a successful transaction simulation."""
        amount_flr = 1.5
        amount_wei = int(1.5 * 10**18)
        block_number = 123
        tx_hash = "0x1234567890abcdef"

        self.flare_portal.wflr_contract.functions.deposit = MagicMock()
        self.flare_provider.w3.to_wei = MagicMock(return_value=amount_wei)
        self.flare_provider.build_transaction = AsyncMock(
            return_value={"tx": "stubbed"}
        )
        self.flare_provider.eth_call = AsyncMock(return_value=True)
        self.flare_provider.sign_and_send_transaction = AsyncMock(return_value=tx_hash)
        self.flare_provider.w3.eth.wait_for_transaction_receipt = AsyncMock(
            return_value={"blockNumber": block_number}
        )

        result = await self.flare_portal.wrap_flr_to_wflr(amount_wei)

        assert result == tx_hash
        self.flare_provider.build_transaction.assert_called_with(
            function_call=self.flare_portal.wflr_contract.functions.deposit.return_value,
            from_addr=self.flare_provider.address,
            custom_params=cast(TxParams, {"value": amount_wei}),
        )
        self.flare_provider.eth_call.assert_called_with(
            contract_abi=self.wflr_abi, call_tx={"tx": "stubbed"}
        )
        self.flare_provider.sign_and_send_transaction.assert_called_with(
            {"tx": "stubbed"}
        )
        self.flare_provider.w3.eth.wait_for_transaction_receipt.assert_called_with(
            tx_hash
        )

    @pytest.mark.asyncio
    async def test_wrap_flr_to_wflr_failed_simulation(self):
        """Test wrap_flr_to_wflr when the transaction simulation fails."""
        amount_flr = 1.5
        amount_wei = int(1.5 * 10**18)

        self.flare_portal.wflr_contract.functions.deposit = MagicMock()
        self.flare_provider.w3.to_wei = MagicMock(return_value=amount_wei)
        self.flare_provider.build_transaction = AsyncMock(
            return_value={"tx": "stubbed"}
        )
        self.flare_provider.eth_call = AsyncMock(return_value=False)

        result = await self.flare_portal.wrap_flr_to_wflr(amount_wei)

        assert result is None
        self.flare_provider.build_transaction.assert_called_with(
            function_call=self.flare_portal.wflr_contract.functions.deposit.return_value,
            from_addr=self.flare_provider.address,
            custom_params=cast(TxParams, {"value": amount_wei}),
        )
        self.flare_provider.eth_call.assert_called_with(
            contract_abi=self.wflr_abi, call_tx={"tx": "stubbed"}
        )
        assert not self.flare_provider.sign_and_send_transaction.called
        assert not self.flare_provider.w3.eth.wait_for_transaction_receipt.called

    @pytest.mark.asyncio
    async def test_unwrap_wflr_to_flr_success(self):
        """Test unwrap_wflr_to_flr with a successful transaction simulation."""
        amount_flr = 2.0
        amount_wei = int(2.0 * 10**18)
        block_number = 456
        tx_hash = "0xabcdef1234567890"

        self.flare_portal.wflr_contract.functions.withdraw = MagicMock()
        self.flare_provider.w3.to_wei = MagicMock(return_value=amount_wei)
        self.flare_provider.build_transaction = AsyncMock(
            return_value={"tx": "stubbed"}
        )
        self.flare_provider.eth_call = AsyncMock(return_value=True)
        self.flare_provider.sign_and_send_transaction = AsyncMock(return_value=tx_hash)
        self.flare_provider.w3.eth.wait_for_transaction_receipt = AsyncMock(
            return_value={"blockNumber": block_number}
        )

        result = await self.flare_portal.unwrap_wflr_to_flr(amount_wei)

        assert result == tx_hash
        self.flare_portal.wflr_contract.functions.withdraw.assert_called_with(
            amount_wei
        )
        self.flare_provider.build_transaction.assert_called_with(
            function_call=self.flare_portal.wflr_contract.functions.withdraw.return_value,
            from_addr=self.flare_provider.address,
        )
        self.flare_provider.eth_call.assert_called_with(
            contract_abi=self.wflr_abi, call_tx={"tx": "stubbed"}
        )
        self.flare_provider.sign_and_send_transaction.assert_called_with(
            {"tx": "stubbed"}
        )
        self.flare_provider.w3.eth.wait_for_transaction_receipt.assert_called_with(
            tx_hash
        )

    @pytest.mark.asyncio
    async def test_unwrap_wflr_to_flr_failed_simulation(self):
        """Test unwrap_wflr_to_flr when the transaction simulation fails."""
        amount_flr = 2.0
        amount_wei = int(2.0 * 10**18)

        self.flare_portal.wflr_contract.functions.withdraw = MagicMock()
        self.flare_provider.w3.to_wei = MagicMock(return_value=amount_wei)
        self.flare_provider.build_transaction = AsyncMock(
            return_value={"tx": "stubbed"}
        )
        self.flare_provider.eth_call = AsyncMock(return_value=False)

        result = await self.flare_portal.unwrap_wflr_to_flr(amount_wei)

        assert result is None
        self.flare_portal.wflr_contract.functions.withdraw.assert_called_with(
            amount_wei
        )
        self.flare_provider.build_transaction.assert_called_with(
            function_call=self.flare_portal.wflr_contract.functions.withdraw.return_value,
            from_addr=self.flare_provider.address,
        )
        self.flare_provider.eth_call.assert_called_with(
            contract_abi=self.wflr_abi, call_tx={"tx": "stubbed"}
        )
        assert not self.flare_provider.sign_and_send_transaction.called
        assert not self.flare_provider.w3.eth.wait_for_transaction_receipt.called
