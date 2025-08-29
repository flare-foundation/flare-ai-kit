from unittest.mock import AsyncMock, MagicMock

import pytest
import pytest_asyncio
from hexbytes import HexBytes

from flare_ai_kit.ecosystem.applications.kinetic import Kinetic


@pytest.fixture
def mock_contracts():
    mock = MagicMock()
    mock.flare.sflr = "0x0000000000000000000000000000000000000001"
    mock.flare.kinetic_ksflr = "0x0000000000000000000000000000000000000002"
    mock.flare.sparkdex_swap_router = "0x0000000000000000000000000000000000000003"
    mock.flare.kinetic_Unitroller = "0x0000000000000000000000000000000000000004"
    return mock


@pytest.fixture
def mock_settings():
    mock = MagicMock()
    mock.account_address = "0x0000000000000000000000000000000000000005"
    return mock


@pytest.fixture
def mock_flare_provider():
    mock = MagicMock()
    mock.address = "0x0000000000000000000000000000000000000005"
    mock.erc20_allowance = AsyncMock(return_value=0)
    mock.erc20_approve = AsyncMock()
    mock.build_transaction = AsyncMock(return_value={"built": True})
    mock.eth_call = AsyncMock(return_value=True)
    mock.sign_and_send_transaction = AsyncMock(
        return_value=HexBytes(
            "0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
        )
    )
    mock.w3.eth.wait_for_transaction_receipt = AsyncMock(
        return_value={"blockNumber": 123}
    )

    mock_mint_function = AsyncMock()
    mock_redeem_function = AsyncMock()
    mock_enter_function = AsyncMock()
    mock_exit_function = AsyncMock()

    mock_functions = MagicMock()
    mock_functions.mint.return_value = mock_mint_function
    mock_functions.redeemUnderlying.return_value = mock_redeem_function
    mock_functions.enterMarkets.return_value = mock_enter_function
    mock_functions.exitMarket.return_value = mock_exit_function

    mock_contract_instance = MagicMock()
    mock_contract_instance.functions = mock_functions

    mock.w3.eth.contract.return_value = mock_contract_instance
    return mock


@pytest.fixture
def mock_explorer():
    return MagicMock()


@pytest_asyncio.fixture
async def kinetic(mock_settings, mock_contracts, mock_explorer, mock_flare_provider):
    return await Kinetic.create(
        settings=mock_settings,
        contracts=mock_contracts,
        flare_explorer=mock_explorer,
        flare_provider=mock_flare_provider,
    )


def test_get_addresses(kinetic):
    token, lending = kinetic.get_addresses("sflr")
    assert token == "0x0000000000000000000000000000000000000001"
    assert lending == "0x0000000000000000000000000000000000000002"


@pytest.mark.asyncio
async def test_supply_executes_correctly(kinetic):
    tx_hash = await kinetic.supply("sflr", 1000)
    assert tx_hash == HexBytes(
        "0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
    )


@pytest.mark.asyncio
async def test_withdraw_executes_correctly(kinetic):
    tx_hash = await kinetic.withdraw("sflr", 1000)
    assert tx_hash == HexBytes(
        "0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
    )


@pytest.mark.asyncio
async def test_enable_collateral_executes_correctly(kinetic):
    tx_hash = await kinetic.enable_collateral("sflr")
    assert tx_hash == HexBytes(
        "0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
    )


@pytest.mark.asyncio
async def test_disable_collateral_executes_correctly(kinetic):
    tx_hash = await kinetic.disable_collateral("sflr")
    assert tx_hash == HexBytes(
        "0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
    )


@pytest.mark.asyncio
async def test_supply_raises_on_failed_simulation(kinetic, mock_flare_provider):
    mock_flare_provider.eth_call.return_value = False
    with pytest.raises(Exception, match="simulated transaction was not sucessfull"):
        await kinetic.supply("sflr", 1000)


@pytest.mark.asyncio
async def test_enable_collateral_raises_on_failed_simulation(
    kinetic, mock_flare_provider
):
    mock_flare_provider.eth_call.return_value = False
    with pytest.raises(Exception, match="simulated transaction was not sucessfull"):
        await kinetic.enable_collateral("sflr")
