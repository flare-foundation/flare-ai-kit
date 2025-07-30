"""Interactions with Flare blockchain."""

import asyncio
import statistics
from collections.abc import Callable
from functools import wraps
from typing import Any, TypeVar, cast

import structlog
from eth_typing import ChecksumAddress
from eth_utils import keccak
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
from web3.types import TxParams, TxReceipt, Wei

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

        if not settings.account_address:
            raise ValueError("account_address must be set and non-empty")

        try:
            # Handle injecting PoA middlewares for testnets
            self.w3 = AsyncWeb3(
                AsyncHTTPProvider(
                    self.web3_provider_url,
                    request_kwargs={"timeout": settings.web3_provider_timeout},
                ),
                middleware=[ExtraDataToPOAMiddleware] if settings.is_testnet else [],
            )
            # Inject geth_poa_middleware to handle Flare's oversized extraData
            self.w3.middleware_onion.inject(ExtraDataToPOAMiddleware, layer=0)
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
            nonce, max_fee_per_gas, chain_id = await asyncio.gather(
                self.w3.eth.get_transaction_count(from_addr),
                self.estimate_gas_price(
                    gas_priority_multiple=1.2
                ),  # Use estimate_gas_price
                self.w3.eth.chain_id,
            )
            max_priority_fee_per_gas = await self.w3.eth.max_priority_fee
            # Add 20% buffer to maxFeePerGas to account for base fee fluctuations
            max_fee_per_gas = Wei(int(max_fee_per_gas * 1.2))
            # Ensure maxFeePerGas is at least baseFee + maxPriorityFeePerGas
            latest_block = await self.w3.eth.get_block("latest")
            base_fee_per_gas = latest_block.get("baseFeePerGas")
            if base_fee_per_gas is None:
                raise ValueError("baseFeePerGas not found in latest block")
            max_fee_per_gas = max(max_fee_per_gas, base_fee_per_gas + max_priority_fee_per_gas)
            params: TxParams = {
                "from": from_addr,
                "nonce": nonce,
                "maxFeePerGas": max_fee_per_gas,
                "maxPriorityFeePerGas": max_priority_fee_per_gas,
                "chainId": chain_id,
                "type": 2,
            }
            logger.debug("Prepared base transaction parameters", params=params)
        except Web3Exception as e:
            msg = f"Failed to fetch transaction parameters (nonce/gas/chainId): {e}"
            logger.exception(msg)
            raise FlareTxError(msg) from e
        return params

    @with_web3_error_handling("Building transaction")
    async def build_transaction(
        self,
        function_call: AsyncContractFunction,
        from_addr: ChecksumAddress,
        custom_params: TxParams | None = None,
    ) -> TxParams | None:
        """Builds a transaction with dynamic gas and nonce parameters."""
        base_tx = await self._prepare_base_tx_params(from_addr)
        # Merge custom parameters, if provided, overriding base_tx values
        if custom_params is not None:
            base_tx.update(custom_params)
        # sys.exit()
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
                tx, private_key=self.private_key.get_secret_value()
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
                "Transaction confirmed.",
                gas_cost_FLR=self.get_gas_cost_from_receipt(receipt),
                tx_hash=tx_hash.hex(),
                receipt=receipt,
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

    @with_web3_error_handling("Estimating transaction gas limit")
    async def estimate_gas(self, tx: TxParams, gas_buffer: float = 0.2) -> int | None:
        try:
            gas_estimate = await self.w3.eth.estimate_gas(tx)
            gas_limit = int(gas_estimate * (1 + gas_buffer))
            return gas_limit
        except Exception as e:
            logger.warning(f"Gas estimation failed: {e}")
            return None

    @with_web3_error_handling("Estimating gas price")
    async def estimate_gas_price(self, gas_priority_multiple: float = 1) -> int:
        fee_history = await self.w3.eth.fee_history(
            10, "latest", reward_percentiles=[50]
        )  # Median reward for last 10 blocks
        base_fee = fee_history["baseFeePerGas"][-1]  # Most recent base fee
        priority_fee = (
            int(statistics.median(fee_history["reward"][0])) * gas_priority_multiple
        )  # Median priority fee
        gas_price = base_fee + priority_fee  # EIP-1559 compatible gas price
        return int(gas_price)

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

    async def erc20_balanceOf(self, wallet_address: str, token_address: str) -> int:
        # Minimal ABI for balanceOf (you don't need the full ABI for just this call)
        erc20_abi = [
            {
                "constant": True,
                "inputs": [{"name": "account", "type": "address"}],
                "name": "balanceOf",
                "outputs": [{"name": "", "type": "uint256"}],
                "type": "function",
            }
        ]

        # Create contract instance
        token_contract = self.w3.eth.contract(
            address=self.w3.to_checksum_address(token_address), abi=erc20_abi
        )

        # Call balanceOf
        balance = await token_contract.functions.balanceOf(wallet_address).call()

        return balance

    async def erc20_allowance(
        self,
        owner_address: ChecksumAddress,
        token_address: ChecksumAddress,
        spender_address: ChecksumAddress,
    ) -> int:
        erc20_abi = [
            {
                "constant": True,
                "inputs": [
                    {"name": "owner", "type": "address"},
                    {"name": "spender", "type": "address"},
                ],
                "name": "allowance",
                "outputs": [{"name": "remaining", "type": "uint256"}],
                "type": "function",
            }
        ]

        # Create contract instance
        token_contract = self.w3.eth.contract(
            address=self.w3.to_checksum_address(token_address), abi=erc20_abi
        )

        # Query the allowance
        allowance = await token_contract.functions.allowance(
            owner_address, spender_address
        ).call()

        return allowance

    async def erc20_approve(
        self,
        token_address: str,
        spender_address: str,
        amount: int,
        approve_buffer: float = 0.2,
    ) -> str:
        erc20_abi = [
            {
                "constant": False,
                "inputs": [
                    {"name": "spender", "type": "address"},
                    {"name": "value", "type": "uint256"},
                ],
                "name": "approve",
                "outputs": [{"name": "success", "type": "bool"}],
                "type": "function",
            }
        ]

        token_contract = self.w3.eth.contract(
            address=self.w3.to_checksum_address(token_address), abi=erc20_abi
        )
        approve_amount = int(amount * (1 + approve_buffer))
        function_call = token_contract.functions.approve(
            spender_address, approve_amount
        )
        tx_approval = await self.build_transaction(
            function_call=function_call, from_addr=self.address
        )
        tx_approval_hash = await self.sign_and_send_transaction(tx_approval)
        logger.debug(f"Approval tx hash: https://flarescan.com/tx/0x{tx_approval}")

        logger.debug("Waiting for approval tx to be mined...")
        approve_receipt = await self.w3.eth.wait_for_transaction_receipt(
            tx_approval_hash
        )
        # logger.info("Approval tx mined", blockNumber=approve_receipt.blockNumber)
        logger.debug(
            f"Approve transaction mined in block {approve_receipt['blockNumber']}"
        )

        return tx_approval

    async def eth_call(self, contract_abi, call_tx) -> bool:
        try:
            await self.w3.eth.call(call_tx)
            logger.info("eth_call successful")
            return True
        except Exception as e:
            # Check if the error has a revert reason or data
            if hasattr(e, "args") and e.args:
                signature = self.get_fn_from_signature(contract_abi, e.args[0])
                logger.warning(
                    "Call failed or reverted. Error: ",
                    e,
                    " - Contract function signature: ",
                    signature,
                )
            else:
                logger.warning(
                    "Call failed or reverted. No revert data found. Error: ", e
                )
            return False

    def get_fn_from_signature(self, abi, target_signature) -> str | None:
        selectors = {}

        for item in abi:
            if item["type"] in ["function", "error"]:
                name = item["name"]
                types = ",".join([input["type"] for input in item.get("inputs", [])])
                signature = f"{name}({types})"

                # Compute the 4-byte selector
                selector = "0x" + keccak(text=signature).hex()[:8]
                selectors[selector] = signature

        # Print the selector-to-signature mapping
        for sel, sig in selectors.items():
            # print(f"{sel} => {sig}")
            if target_signature == sel:
                return sig

    def get_gas_cost_from_receipt(self, receipt: TxReceipt) -> float | None:
        if receipt:
            gas_used = receipt.get("gasUsed", 0)
            effective_gas_price = receipt.get("effectiveGasPrice", 0)
            gas_cost_wei = gas_used * effective_gas_price
            gas_cost_flr = self.w3.from_wei(gas_cost_wei, "ether")
            return float(gas_cost_flr)
        logger.warning("No receipt found")
        return None
