"""Interactions with Flare blockchain."""

import asyncio
from collections.abc import Callable
from functools import wraps
from typing import Any, TypeVar, cast

import structlog
from eth_typing import ChecksumAddress
from web3 import AsyncHTTPProvider, AsyncWeb3
from web3.contract.async_contract import AsyncContractFunction
from web3.exceptions import (
    ContractLogicError,
    TimeExhausted,
    TransactionNotFound,
    Web3Exception,
)
from web3.middleware import (
    ExtraDataToPOAMiddleware,  # pyright: ignore[reportUnknownVariableType]
)
from web3.types import TxParams

from flare_ai_kit.common import FlareTxError, FlareTxRevertedError, load_abi
from flare_ai_kit.ecosystem.settings import EcosystemSettings

logger = structlog.get_logger(__name__)

# This is safe to hard-code
# Same address across both testnet and mainnet
CONTRACT_REGISTRY_ADDRESS = "0xaD67FE66660Fb8dFE9d6b1b4240d8650e30F6019"

# Type variable for decorator use
F = TypeVar("F", bound=Callable[..., Any])


def with_web3_error_handling(operation_name: str) -> Callable[[F], F]:
    """
    Decorator to standardize Web3 error handling across methods.

    Args:
        operation_name: Human-readable name of the operation for error context

    Returns:
        Decorated function with standardized error handling

    """

    def decorator(func: F) -> F:
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            try:
                return await func(*args, **kwargs)
            except TimeExhausted as e:
                msg = f"{operation_name} timed out: {e}"
                logger.exception(msg)
                raise FlareTxError(msg) from e
            except TransactionNotFound as e:
                msg = f"{operation_name} transaction not found: {e}"
                logger.exception(msg)
                raise FlareTxError(msg) from e
            except ContractLogicError as e:
                msg = f"{operation_name} failed due to contract logic error: {e}"
                logger.exception(msg)
                raise FlareTxRevertedError(msg) from e
            except Web3Exception as e:
                msg = f"{operation_name} failed with Web3 error: {e}"
                logger.exception(msg)
                raise FlareTxError(msg) from e
            except Exception as e:
                msg = f"Unexpected error during {operation_name}: {e}"
                logger.exception(msg)
                raise FlareTxError(msg) from e

        return cast("F", wrapper)

    return decorator


class Flare:
    """Handles interactions with the Flare blockchain."""

    def __init__(self, settings: EcosystemSettings) -> None:
        """
        Initialize the Flare Provider and connect to the RPC endpoint.

        Args:
            settings: Instance of EcosystemSettings containing connection
                      and account details.

        Raises:
            FlareConnectionError: If the Web3 provider cannot be initialized.

        """
        self.address = settings.account_address
        self.private_key = settings.account_private_key
        self.web3_provider_url = str(settings.web3_provider_url)
        self.max_retries = settings.max_retries
        self.retry_delay = settings.retry_delay

        try:
            # Handle injecting PoA middlewares for testnets
            self.w3 = AsyncWeb3(
                AsyncHTTPProvider(
                    self.web3_provider_url,
                    request_kwargs={"timeout": settings.web3_provider_timeout},
                ),
                middleware=[ExtraDataToPOAMiddleware] if settings.is_testnet else [],
            )
            self.contract_registry = self.w3.eth.contract(
                address=self.w3.to_checksum_address(CONTRACT_REGISTRY_ADDRESS),
                abi=load_abi("FlareContractRegistry"),
            )
        except Exception as e:
            msg = "Failed to initialize Flare provider"
            logger.exception(msg)
            raise FlareTxError(msg) from e

    async def check_connection(self) -> bool:
        """
        Check the connection status to the configured RPC endpoint.

        Returns:
            True if connected, False otherwise.

        """
        for attempt in range(self.max_retries):
            try:
                is_connected = await self.w3.is_connected()
                if is_connected:
                    chain_id = await self.w3.eth.chain_id
                    logger.info(
                        "Connection successful",
                        web3_provider_url=self.web3_provider_url,
                        chain_id=chain_id,
                        attempt=attempt + 1,
                    )
                    return True
                logger.warning(
                    "Connection check returned false",
                    web3_provider_url=self.web3_provider_url,
                    attempt=attempt + 1,
                )
            except Exception:
                logger.exception(
                    "Connection check failed",
                    web3_provider_url=self.web3_provider_url,
                    attempt=attempt + 1,
                )

            # If this wasn't the last attempt, wait before retrying
            if attempt < self.max_retries - 1:
                await asyncio.sleep(
                    self.retry_delay * (2**attempt)
                )  # Exponential backoff

        logger.error(
            "Connection failed after all retries",
            web3_provider_url=self.web3_provider_url,
            max_retries=self.max_retries,
        )
        return False

    async def _prepare_base_tx_params(self, from_addr: ChecksumAddress) -> TxParams:
        """
        Fetches nonce, gas fees (EIP-1559), and chain ID for a transaction.

        Args:
            from_addr: The sender's checksummed address.

        Returns:
            A dictionary with essential transaction parameters ('from', 'nonce',
            'maxFeePerGas', 'maxPriorityFeePerGas', 'chainId').

        Raises:
            FlareTransactionError: If fetching blockchain data fails.

        """
        try:
            (
                nonce,
                gas_price,
                max_priority_fee,
                chain_id,
            ) = await asyncio.gather(
                self.w3.eth.get_transaction_count(from_addr),
                self.w3.eth.gas_price,  # Fetches current gas price
                self.w3.eth.max_priority_fee,  # Fetches max priority fee
                self.w3.eth.chain_id,
            )
            params: TxParams = {
                "from": from_addr,
                "nonce": nonce,
                "maxFeePerGas": gas_price,  # Use fetched gas_price as maxFeePerGas
                "maxPriorityFeePerGas": max_priority_fee,
                "chainId": chain_id,
                "type": 2,  # Explicitly set EIP-1559 transaction type
            }
            logger.debug("Prepared base transaction parameters", params=params)
        except Web3Exception as e:
            msg = f"Failed to fetch transaction parameters (nonce/gas/chainId): {e}"
            logger.exception(msg)
            raise FlareTxError(msg) from e
        else:
            return params

    @with_web3_error_handling("Building transaction")
    async def build_transaction(
        self, function_call: AsyncContractFunction, from_addr: ChecksumAddress
    ) -> TxParams | None:
        """Builds a transaction with dynamic gas and nonce parameters."""
        base_tx = await self._prepare_base_tx_params(from_addr)
        # Let web3.py handle gas estimation within build_transaction if not provided
        tx = await function_call.build_transaction(base_tx)
        logger.debug("Transaction built successfully", tx=tx)
        return tx

    @with_web3_error_handling("Signing and sending transaction")
    async def sign_and_send_transaction(self, tx: TxParams) -> str | None:
        """
        Sign and send a transaction to the network.

        Args:
            tx (TxParams): Transaction parameters to be sent

        Returns:
            str: Transaction hash of the sent transaction

        Raises:
            ValueError: If account is not initialized

        """
        if not self.private_key or not self.address:
            msg = "Account not initialized"
            raise ValueError(msg)

        try:
            signed_tx = self.w3.eth.account.sign_transaction(
                tx, private_key=self.private_key
            )
            logger.debug("Transaction signed.")
        except Web3Exception as e:
            msg = f"Failed to sign transaction: {e}"
            logger.exception(msg, tx_details=tx)
            raise FlareTxError(msg) from e

        try:
            tx_hash = await self.w3.eth.send_raw_transaction(signed_tx.raw_transaction)
            logger.info(
                "Transaction sent, waiting for receipt...", tx_hash=tx_hash.hex()
            )

            # Wait for the transaction receipt
            receipt = await self.w3.eth.wait_for_transaction_receipt(tx_hash)
            logger.info(
                "Transaction confirmed.", tx_hash=tx_hash.hex(), receipt=receipt
            )

            # Check status for success (status == 1)
            if receipt.get("status") == 0:
                msg = f"Transaction {tx_hash.hex()} failed (reverted)."
                logger.error(msg, receipt=receipt)
                raise FlareTxRevertedError(msg)

            return tx_hash.hex()

        except Web3Exception as e:
            msg = f"Failed to send transaction or get receipt: {e}"
            logger.exception(msg, tx_details=tx)
            raise FlareTxError(msg) from e

    @with_web3_error_handling("Checking balance")
    async def check_balance(self, address: str) -> float:
        """
        Check the balance of the current account.

        Returns:
            float: Account balance in FLR

        Raises:
            ValueError: If account does not exist

        """
        checksum_address = self.w3.to_checksum_address(address)
        balance_wei = await self.w3.eth.get_balance(checksum_address)
        balance_float = float(self.w3.from_wei(balance_wei, "ether"))
        logger.debug(
            "Account balance check",
            address=self.address,
            balance_wei=balance_wei,
            balance_float=balance_float,
        )
        return balance_float

    @with_web3_error_handling("Creating FLR transfer transaction")
    async def create_send_flr_tx(
        self, from_address: str, to_address: str, amount: float
    ) -> TxParams:
        """
        Create a transaction to send FLR tokens.

        Args:
            from_address (str): Sender address
            to_address (str): Recipient address
            amount (float): Amount of FLR to send

        Returns:
            TxParams: Transaction parameters for sending FLR

        Raises:
            ValueError: If account does not exist

        """
        if amount <= 0:
            msg = "Amount must be positive."
            raise ValueError(msg)

        checksum_from_address = self.w3.to_checksum_address(from_address)
        checksum_to_address = self.w3.to_checksum_address(to_address)

        tx = await self._prepare_base_tx_params(from_addr=checksum_from_address)

        tx["to"] = checksum_to_address
        tx["value"] = self.w3.to_wei(amount, unit="ether")
        tx["gas"] = 21000
        logger.debug("Created FLR transfer transaction parameters", tx=tx)
        return tx

    @with_web3_error_handling("Getting protocol contract address")
    async def get_protocol_contract_address(self, contract_name: str) -> str:
        """
        Retrieves the address for a given protocol contract name from the registry.

        Args:
            contract_name: The case-sensitive name of the contract as registered
                in the Flare Contract Registry (e.g., "FtsoV2", "FtsoManager").

        Returns:
            The blockchain address of the specified contract as a string.

        """
        address: ChecksumAddress = (
            await self.contract_registry.functions.getContractAddressByName(
                contract_name
            ).call()
        )
        logger.debug(
            "Retrieved contract address from registry",
            contract_name=contract_name,
            address=address,
        )
        return address
