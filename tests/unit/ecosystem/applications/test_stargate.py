import warnings
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from hexbytes import HexBytes
from web3 import Web3
from web3.contract.contract import Contract

from flare_ai_kit.ecosystem import ChainIdConfig, Contracts, EcosystemSettings
from flare_ai_kit.ecosystem.applications.stargate import Stargate
from flare_ai_kit.ecosystem.explorer import BlockExplorer
from flare_ai_kit.ecosystem.flare import Flare

# Suppress all websockets warnings
warnings.filterwarnings("ignore", category=DeprecationWarning, module=r"websockets.*")


class TestStargate:
    """Test suite for the Stargate class, covering initialization and cross-chain ETH transfers."""

    def setup_method(self):
        # Mock structlog to avoid logging issues
        self.logger_patcher = patch("structlog.get_logger", return_value=MagicMock())
        self.logger_patcher.start()

        self.settings = MagicMock(spec=EcosystemSettings)
        self.settings.account_address = "0x9e8318cc9c83427870ed8994d818Ba7A92739B99"

        self.contracts = MagicMock(spec=Contracts)
        self.contracts.flare = MagicMock()
        self.contracts.flare.stargate_StargateOFTETH = (
            "0x5555555555555555555555555555555555555555"
        )
        self.contracts.flare.weth = "0x6666666666666666666666666666666666666666"

        self.chains = MagicMock(spec=ChainIdConfig)
        self.chains.chains = MagicMock()
        self.chains.chains.base = 8453
        self.chain_id = 8453

        self.flare_explorer = MagicMock(spec=BlockExplorer)
        self.flare_provider = MagicMock(spec=Flare)
        self.flare_provider.address = self.settings.account_address
        self.flare_provider.w3 = MagicMock()
        self.flare_provider.w3.eth = MagicMock()

        self.oft_abi = [{"name": "quoteOFT"}, {"name": "quoteSend"}, {"name": "send"}]

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
        self.logger_patcher.stop()

    @pytest.mark.asyncio
    async def test_create(self):
        mock_oft_abi = [{"name": "someFunction"}]
        mock_oft_contract = MagicMock(spec=Contract, functions=MagicMock())

        contracts = MagicMock(spec=Contracts)
        contracts.flare = MagicMock()
        contracts.flare.stargate_StargateOFTETH = "0x" + "2" * 40

        settings = MagicMock(spec=EcosystemSettings)
        settings.account_address = "0x" + "1" * 40

        chains = MagicMock(spec=ChainIdConfig)
        chains.chains = MagicMock()
        chains.chains.base = self.chain_id

        explorer = MagicMock(spec=BlockExplorer)
        explorer.get_contract_abi = AsyncMock(return_value=mock_oft_abi)

        provider = MagicMock(spec=Flare)
        provider.w3 = MagicMock()
        provider.w3.eth = MagicMock()
        provider.w3.eth.contract = MagicMock(return_value=mock_oft_contract)

        stargate = await Stargate.create(
            settings=settings,
            contracts=contracts,
            chains=chains,
            flare_explorer=explorer,
            flare_provider=provider,
        )

        assert isinstance(stargate, Stargate)
        assert stargate.contracts == contracts
        assert stargate.chains == chains
        assert stargate.flare_explorer == explorer
        assert stargate.flare_provider == provider
        assert stargate.account_address == settings.account_address
        assert stargate.oft_abi == mock_oft_abi
        provider.w3.eth.contract.assert_called_with(
            address=contracts.flare.stargate_StargateOFTETH,
            abi=mock_oft_abi,
        )

    @pytest.mark.asyncio
    async def test_create_missing_account_address(self):
        settings = MagicMock(spec=EcosystemSettings)
        settings.account_address = None

        contracts = MagicMock(spec=Contracts)
        contracts.flare = MagicMock()
        contracts.flare.stargate_StargateOFTETH = "0x" + "2" * 40

        explorer = MagicMock(spec=BlockExplorer)
        explorer.get_contract_abi = AsyncMock(return_value=[{}])

        provider = MagicMock(spec=Flare)
        provider.w3 = MagicMock()
        provider.w3.eth = MagicMock()
        provider.w3.eth.contract = MagicMock()

        with pytest.raises(
            Exception, match="Please set settings.account_address in your .env file."
        ):
            await Stargate.create(
                settings=settings,
                contracts=contracts,
                chains=self.chains,
                flare_explorer=explorer,
                flare_provider=provider,
            )

    def test_init_missing_account_address(self):
        settings = MagicMock(spec=EcosystemSettings)
        settings.account_address = ""
        with pytest.raises(
            Exception, match="Please set settings.account_address in your .env file."
        ):
            Stargate(
                settings=settings,
                contracts=self.contracts,
                chains=self.chains,
                flare_explorer=self.flare_explorer,
                flare_provider=self.flare_provider,
                oft_abi=self.oft_abi,
            )

    @pytest.mark.asyncio
    async def test_bridge_weth_to_chain_success(self):
        desired_amount_wei = 10**18
        tx_hash = "0x1234567890abcdef"
        oft_limits = (5 * 10**17, 5 * 10**18)
        oft_fee_details = (100, 200, 300)
        oft_receipt = (desired_amount_wei, 0)
        messaging_fee = (10**15, 0)
        weth_balance = 2 * desired_amount_wei
        allowance = desired_amount_wei // 2

        to_address = Web3.to_bytes(
            hexstr="0x" + "0" * 24 + self.settings.account_address[2:]
        )
        send_param = (
            self.chain_id,
            to_address,
            desired_amount_wei,
            desired_amount_wei - int(desired_amount_wei * 0.01),
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
        self.flare_provider.erc20_approve = AsyncMock(return_value="0xapprove")
        self.flare_provider.build_transaction = AsyncMock(return_value={"tx": "stub"})
        self.flare_provider.eth_call = AsyncMock(return_value=True)
        self.flare_provider.sign_and_send_transaction = AsyncMock(return_value=tx_hash)
        self.flare_provider.w3.eth.wait_for_transaction_receipt = AsyncMock(
            return_value={"blockNumber": 1}
        )

        result = await self.stargate.bridge_weth_to_chain(
            desired_amount_wei, self.chain_id
        )
        assert result == tx_hash
        self.flare_provider.w3.eth.wait_for_transaction_receipt.assert_called_with(
            # Stargate now wraps hash in HexBytes before waiting
            HexBytes(tx_hash)
        )

    @pytest.mark.asyncio
    async def test_bridge_weth_to_chain_exceeds_max_limit(self):
        self.stargate.oft_contract.functions.quoteOFT = MagicMock()
        self.stargate.oft_contract.functions.quoteOFT.return_value.call = AsyncMock(
            return_value=((1, 5), (), (0,))
        )
        with pytest.raises(ValueError, match="Desired send amount exceeds max limit"):
            await self.stargate.bridge_weth_to_chain(6, self.chain_id)

    @pytest.mark.asyncio
    async def test_bridge_weth_to_chain_below_min_limit(self):
        self.stargate.oft_contract.functions.quoteOFT = MagicMock()
        self.stargate.oft_contract.functions.quoteOFT.return_value.call = AsyncMock(
            return_value=((1, 5), (), (0,))
        )
        with pytest.raises(
            ValueError, match="Desired send amount is less than min limit"
        ):
            await self.stargate.bridge_weth_to_chain(0, self.chain_id)

    @pytest.mark.asyncio
    async def test_bridge_weth_to_chain_failed_simulation(self):
        desired_amount_wei = 10**18
        # ensure limits allow simulation path
        self.stargate.oft_contract.functions.quoteOFT = MagicMock()
        self.stargate.oft_contract.functions.quoteOFT.return_value.call = AsyncMock(
            return_value=((1, 2 * desired_amount_wei), (), (desired_amount_wei,))
        )
        self.stargate.oft_contract.functions.quoteSend = MagicMock()
        self.stargate.oft_contract.functions.quoteSend.return_value.call = AsyncMock(
            return_value=(10**15, 0)
        )
        self.flare_provider.erc20_balanceOf = AsyncMock(
            return_value=2 * desired_amount_wei
        )
        self.flare_provider.erc20_allowance = AsyncMock(return_value=desired_amount_wei)
        self.flare_provider.erc20_approve = AsyncMock(return_value="0xapprove")
        self.flare_provider.build_transaction = AsyncMock(return_value={"tx": "stub"})
        self.flare_provider.eth_call = AsyncMock(return_value=False)

        with pytest.raises(
            Exception,
            match="We stop here because the simulated send transaction was not sucessfull",
        ):
            await self.stargate.bridge_weth_to_chain(desired_amount_wei, self.chain_id)
