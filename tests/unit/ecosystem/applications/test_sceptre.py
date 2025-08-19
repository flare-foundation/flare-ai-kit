from unittest.mock import ANY, AsyncMock, MagicMock

import pytest
from typing import cast
from web3.types import TxParams

from flare_ai_kit.ecosystem.applications.sceptre import Sceptre


class TestSceptre:
    """Test suite for Sceptre staking functionality."""

    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test fixtures."""
        # Setup basic mocks
        self.settings = MagicMock()
        self.contracts = MagicMock()
        self.flare_explorer = AsyncMock()
        self.flare_provider = AsyncMock()

        # Setup Web3 mock with contract
        self.mock_web3 = MagicMock()
        self.mock_web3.eth = MagicMock()

        # Create a mock contract
        self.mock_contract = MagicMock()
        self.mock_contract.functions = MagicMock()
        self.mock_submit = MagicMock()
        self.mock_contract.functions.submit.return_value = self.mock_submit

        # Make contract() return our mock contract (synchronously)
        self.mock_web3.eth.contract = MagicMock(return_value=self.mock_contract)

        # Setup async methods
        self.flare_provider.w3 = self.mock_web3
        self.flare_provider.address = "0x123"
        self.flare_provider.build_transaction = AsyncMock(return_value={"tx": "data"})
        self.flare_provider.eth_call = AsyncMock()
        self.flare_provider.sign_and_send_transaction = AsyncMock()

        # Mock the wait_for_transaction_receipt method
        self.mock_wait_for_receipt = AsyncMock()
        self.mock_web3.eth.wait_for_transaction_receipt = self.mock_wait_for_receipt

        # Initialize Sceptre with our mocks
        self.sceptre = Sceptre(
            settings=self.settings,
            contracts=self.contracts,
            flare_explorer=self.flare_explorer,
            flare_provider=self.flare_provider,
        )

    @pytest.mark.asyncio
    async def test_stake_success(self):
        """Test successful stake operation."""
        # Setup
        amount_flr = 10.0
        amount_wei = 10**18 * 10
        tx_hash = "0x123abc"

        self.mock_web3.to_wei.return_value = amount_wei
        self.flare_provider.eth_call.return_value = True
        self.flare_provider.sign_and_send_transaction.return_value = tx_hash

        # Execute
        result = await self.sceptre.stake(amount_wei)

        # Verify
        assert result == tx_hash
        self.mock_web3.eth.contract.assert_called_with(
            address=self.contracts.flare.sflr, abi=ANY
        )
        self.mock_contract.functions.submit.assert_called_once()
        self.flare_provider.build_transaction.assert_awaited_with(
            function_call=self.mock_submit,
            from_addr=self.flare_provider.address,
            custom_params=cast(TxParams, {"value": amount_wei}),
        )
        self.flare_provider.eth_call.assert_awaited_once()
        self.flare_provider.sign_and_send_transaction.assert_awaited_once()
        self.mock_wait_for_receipt.assert_awaited_once_with(tx_hash)

    @pytest.mark.asyncio
    async def test_stake_failed_simulation(self):    
        self.flare_provider.eth_call = AsyncMock(return_value=False)

        with pytest.raises(
            Exception,
            match="We stop here because the simulated transaction was not sucessfull"
        ):
            await self.sceptre.stake(10.0)

        # since we bail on simulation, no send or receipt lookup
        self.flare_provider.sign_and_send_transaction.assert_not_called()
        self.mock_wait_for_receipt.assert_not_called()        

    @pytest.mark.asyncio
    async def test_stake_invalid_amount(self):
        """Test stake with invalid amounts."""
        with pytest.raises(ValueError, match="Amount to stake must be positive"):
            await self.sceptre.stake(0)

        with pytest.raises(ValueError, match="Amount to stake must be positive"):
            await self.sceptre.stake(-1)
