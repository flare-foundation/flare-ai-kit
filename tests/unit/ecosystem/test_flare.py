"""Unit tests for the Flare blockchain module."""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio
from pydantic import HttpUrl
from web3.exceptions import (
    ContractLogicError,
    TimeExhausted,
    TransactionNotFound,
    Web3Exception,
)

from flare_ai_kit.common import FlareTxError, FlareTxRevertedError
from flare_ai_kit.ecosystem.flare import Flare, with_web3_error_handling
from flare_ai_kit.ecosystem.settings import EcosystemSettings


# ---------- Fixtures ----------
@pytest_asyncio.fixture
async def settings():
    return EcosystemSettings(
        is_testnet=True,
        web3_provider_url=HttpUrl("https://flare.example.com"),
        web3_provider_timeout=5,
        block_explorer_url=HttpUrl("https://explorer.example.com/api"),
        block_explorer_timeout=5,
        account_address="0x1234567890abcdef1234567890abcdef12345678",
        account_private_key="0xabcdefabcdefabcdefabcdefabcdefabcdef",
        max_retries=2,
        retry_delay=1,  # Short delay for tests
    )


@pytest_asyncio.fixture
async def flare(settings):
    # Patch AsyncWeb3 to avoid real connection
    with patch("flare_ai_kit.ecosystem.flare.AsyncWeb3") as mock_web3_cls:
        mock_w3 = MagicMock()

        # Async methods (actually awaited in Flare)
        mock_w3.is_connected = AsyncMock(return_value=True)
        mock_w3.eth = MagicMock()
        mock_w3.eth.get_transaction_count = AsyncMock(return_value=1)
        mock_w3.eth.gas_price = asyncio.Future()
        mock_w3.eth.gas_price = set_value(100)
        mock_w3.eth.max_priority_fee = asyncio.Future()
        mock_w3.eth.max_priority_fee.set_result(2)
        mock_w3.eth.get_balance = AsyncMock(return_value=10**18)
        mock_w3.eth.wait_for_transaction_receipt = AsyncMock(return_value={"status": 1})
        mock_w3.eth.chain_id = asyncio.Future()
        mock_w3.eth.chain_id.set_result(1234)
        mock_w3.eth.send_raw_transaction = AsyncMock(return_value=b"\x12" * 32)

        # Sync helpers/properties
        mock_w3.to_checksum_address = MagicMock(side_effect=lambda x: x)
        mock_w3.from_wei = MagicMock(side_effect=lambda v, _: v / 10**18)
        mock_w3.to_wei = MagicMock(side_effect=lambda v, _: int(v * 10**18))
        mock_w3.eth.account = MagicMock()
        mock_w3.eth.account.sign_transaction = MagicMock(
            return_value=MagicMock(raw_transaction=b"signedtx")
        )

        # Contract registry setup
        mock_contract = MagicMock()
        mock_contract.functions = MagicMock()
        mock_w3.eth.contract = MagicMock(return_value=mock_contract)

        mock_web3_cls.return_value = mock_w3
        f = Flare(settings)
        f.w3 = mock_w3
        yield f


# ---------- Tests ----------
class TestFlareInitialization:
    @pytest.mark.asyncio
    async def test_initialization_success(self, settings):
        with patch("flare_ai_kit.ecosystem.flare.AsyncWeb3") as mock_web3_cls:
            mock_web3_cls.return_value = MagicMock()
            f = Flare(settings)
            assert f.web3_provider_url == "https://flare.example.com/"
            assert f.address == settings.account_address

    @pytest.mark.asyncio
    async def test_initialization_failure(self, settings):
        with (
            patch(
                "flare_ai_kit.ecosystem.flare.AsyncWeb3",
                side_effect=Exception("init fail"),
            ),
            pytest.raises(FlareTxError, match="Failed to initialize Flare provider"),
        ):
            Flare(settings)


class TestSignAndSendTransaction:
    @pytest.mark.asyncio
    async def test_sign_and_send_transaction_success(self, flare):
        tx = {"from": "0xabc"}
        tx_hash = await flare.sign_and_send_transaction(tx)
        assert isinstance(tx_hash, str)
        flare.w3.eth.account.sign_transaction.assert_called_once()

    @pytest.mark.asyncio
    async def test_sign_and_send_transaction_no_account(self, flare):
        flare.private_key = None
        with pytest.raises(FlareTxError, match="Account not initialized"):
            await flare.sign_and_send_transaction({"from": "0xabc"})

    @pytest.mark.asyncio
    async def test_sign_failure(self, flare):
        flare.w3.eth.account.sign_transaction.side_effect = Web3Exception("sign fail")
        with pytest.raises(FlareTxError):
            await flare.sign_and_send_transaction({"from": "0xabc"})

    @pytest.mark.asyncio
    async def test_tx_reverted_status(self, flare):
        flare.w3.eth.wait_for_transaction_receipt = AsyncMock(
            return_value={"status": 0}
        )
        with pytest.raises(FlareTxError, match="failed \\(reverted\\)"):
            await flare.sign_and_send_transaction({"from": "0xabc"})


class TestCheckBalance:
    @pytest.mark.asyncio
    async def test_check_balance_success(self, flare):
        bal = await flare.check_balance("0xabc")
        assert isinstance(bal, float)
        flare.w3.eth.get_balance.assert_awaited_once()


class TestGetProtocolContractAddress:
    @pytest.mark.asyncio
    async def test_get_protocol_contract_address_success(self, flare):
        mock_func = MagicMock()
        mock_func.call = AsyncMock(return_value="0xcontract")
        flare.contract_registry.functions.getContractAddressByName = MagicMock(
            return_value=mock_func
        )
        addr = await flare.get_protocol_contract_address("FtsoV2")
        assert addr == "0xcontract"
        mock_func.call.assert_awaited_once()


class TestDecorator:
    @pytest.mark.asyncio
    async def test_with_web3_error_handling_contract_logic_error(self):
        @with_web3_error_handling("testop")
        async def sample():
            message = "execution reverted: logic fail"
            raise ContractLogicError(message)

        with pytest.raises(FlareTxRevertedError):
            await sample()

    @pytest.mark.asyncio
    async def test_with_web3_error_handling_time_exhausted(self):
        @with_web3_error_handling("testop")
        async def sample():
            message = "Transaction receipt wait timeout"
            raise TimeExhausted(message)

        with pytest.raises(FlareTxError):
            await sample()

    @pytest.mark.asyncio
    async def test_with_web3_error_handling_transaction_not_found(self):
        @with_web3_error_handling("testop")
        async def sample():
            message = "Transaction not found"
            raise TransactionNotFound(message)

        with pytest.raises(FlareTxError):
            await sample()

    @pytest.mark.asyncio
    async def test_with_web3_error_handling_generic_web3(self):
        @with_web3_error_handling("testop")
        async def sample():
            message = "Some generic web3 error"
            raise Web3Exception(message)

        with pytest.raises(FlareTxError):
            await sample()

    @pytest.mark.asyncio
    async def test_with_web3_error_handling_unexpected(self):
        @with_web3_error_handling("testop")
        async def sample():
            message = "An unexpected error"
            raise RuntimeError(message)

        with pytest.raises(FlareTxError):
            await sample()
