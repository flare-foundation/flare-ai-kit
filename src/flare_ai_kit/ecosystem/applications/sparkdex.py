"""SparkDEX V3 connector for token swaps on Flare."""

from typing import Self

import structlog
from eth_typing import ChecksumAddress

from flare_ai_kit.common import FlareTxError, load_abi
from flare_ai_kit.ecosystem.flare import Flare
from flare_ai_kit.ecosystem.settings import EcosystemSettings

logger = structlog.get_logger(__name__)

# Common fee tiers in Uniswap V3 (in basis points, 1 basis point = 0.01%)
FEE_LOW = 500  # 0.05%
FEE_MEDIUM = 3000  # 0.3%
FEE_HIGH = 10000  # 1%


class SparkDEX(Flare):
    """
    SparkDEX V3 connector for executing token swaps.

    SparkDEX is a Uniswap V3 fork deployed on Flare.
    This connector provides methods to swap tokens using the V3 SwapRouter.
    """

    def __init__(self, settings: EcosystemSettings) -> None:
        super().__init__(settings)
        self.swap_router = None  # Will be initialized in 'create'

    @classmethod
    async def create(cls, settings: EcosystemSettings) -> Self:
        """
        Asynchronously creates and initializes a SparkDEX instance.

        Args:
            settings: Instance of EcosystemSettings.

        Returns:
            A fully initialized SparkDEX instance.

        """
        instance = cls(settings)
        logger.info("Initializing SparkDEX...")

        # Get SwapRouter address from settings
        if settings.is_testnet:
            router_address = settings.contracts.coston2.sparkdex_swap_router
        else:
            router_address = settings.contracts.flare.sparkdex_swap_router

        if not router_address:
            msg = "SparkDEX SwapRouter address not configured"
            raise FlareTxError(msg)

        instance.swap_router = instance.w3.eth.contract(
            address=instance.w3.to_checksum_address(router_address),
            abi=load_abi("SparkDEXRouter"),
        )
        logger.debug("SparkDEX initialized", address=router_address)
        return instance

    async def swap_exact_input_single(  # noqa: PLR0913
        self,
        token_in: str,
        token_out: str,
        fee: int,
        recipient: str,
        amount_in: int,
        amount_out_minimum: int,
        deadline: int,
        sqrt_price_limit_x96: int = 0,
    ) -> str:
        """
        Swap an exact amount of input tokens for output tokens (single pool).

        Args:
            token_in: Address of the token to swap from.
            token_out: Address of the token to swap to.
            fee: Pool fee tier (500 for 0.05%, 3000 for 0.3%, 10000 for 1%).
            recipient: Address to receive the output tokens.
            amount_in: Amount of input tokens to swap (in wei).
            amount_out_minimum: Minimum amount of output tokens (slippage protection).
            deadline: Unix timestamp after which the transaction will revert.
            sqrt_price_limit_x96: Price limit (0 = no limit).

        Returns:
            Transaction hash as a hex string.

        Raises:
            FlareTxError: If the swap transaction fails.

        """
        if not self.swap_router:
            msg = "SparkDEX instance not fully initialized. Use SparkDEX.create()."
            raise AttributeError(msg)

        if not self.address:
            msg = "Account not initialized"
            raise ValueError(msg)

        checksum_token_in = self.w3.to_checksum_address(token_in)
        checksum_token_out = self.w3.to_checksum_address(token_out)
        checksum_recipient = self.w3.to_checksum_address(recipient)

        # Build the swap parameters struct
        params = {
            "tokenIn": checksum_token_in,
            "tokenOut": checksum_token_out,
            "fee": fee,
            "recipient": checksum_recipient,
            "deadline": deadline,
            "amountIn": amount_in,
            "amountOutMinimum": amount_out_minimum,
            "sqrtPriceLimitX96": sqrt_price_limit_x96,
        }

        logger.info(
            "Executing exactInputSingle swap",
            token_in=token_in,
            token_out=token_out,
            amount_in=amount_in,
            amount_out_minimum=amount_out_minimum,
        )

        # Build and send the transaction
        function_call = self.swap_router.functions.exactInputSingle(params)
        tx = await self.build_transaction(function_call, self.address)

        if not tx:
            msg = "Failed to build swap transaction"
            raise FlareTxError(msg)

        tx_hash = await self.sign_and_send_transaction(tx)

        if not tx_hash:
            msg = "Failed to send swap transaction"
            raise FlareTxError(msg)

        logger.info("Swap executed successfully", tx_hash=tx_hash)
        return tx_hash

    async def swap_exact_output_single(  # noqa: PLR0913
        self,
        token_in: str,
        token_out: str,
        fee: int,
        recipient: str,
        amount_out: int,
        amount_in_maximum: int,
        deadline: int,
        sqrt_price_limit_x96: int = 0,
    ) -> str:
        """
        Swap tokens to receive an exact amount of output tokens (single pool).

        Args:
            token_in: Address of the token to swap from.
            token_out: Address of the token to swap to.
            fee: Pool fee tier (500 for 0.05%, 3000 for 0.3%, 10000 for 1%).
            recipient: Address to receive the output tokens.
            amount_out: Exact amount of output tokens desired (in wei).
            amount_in_maximum: Maximum amount of input tokens (slippage protection).
            deadline: Unix timestamp after which the transaction will revert.
            sqrt_price_limit_x96: Price limit (0 = no limit).

        Returns:
            Transaction hash as a hex string.

        Raises:
            FlareTxError: If the swap transaction fails.

        """
        if not self.swap_router:
            msg = "SparkDEX instance not fully initialized. Use SparkDEX.create()."
            raise AttributeError(msg)

        if not self.address:
            msg = "Account not initialized"
            raise ValueError(msg)

        checksum_token_in = self.w3.to_checksum_address(token_in)
        checksum_token_out = self.w3.to_checksum_address(token_out)
        checksum_recipient = self.w3.to_checksum_address(recipient)

        params = {
            "tokenIn": checksum_token_in,
            "tokenOut": checksum_token_out,
            "fee": fee,
            "recipient": checksum_recipient,
            "deadline": deadline,
            "amountOut": amount_out,
            "amountInMaximum": amount_in_maximum,
            "sqrtPriceLimitX96": sqrt_price_limit_x96,
        }

        logger.info(
            "Executing exactOutputSingle swap",
            token_in=token_in,
            token_out=token_out,
            amount_out=amount_out,
            amount_in_maximum=amount_in_maximum,
        )

        function_call = self.swap_router.functions.exactOutputSingle(params)
        tx = await self.build_transaction(function_call, self.address)

        if not tx:
            msg = "Failed to build swap transaction"
            raise FlareTxError(msg)

        tx_hash = await self.sign_and_send_transaction(tx)

        if not tx_hash:
            msg = "Failed to send swap transaction"
            raise FlareTxError(msg)

        logger.info("Swap executed successfully", tx_hash=tx_hash)
        return tx_hash

    async def get_factory_address(self) -> ChecksumAddress:
        """
        Get the SparkDEX V3 factory contract address.

        Returns:
            Factory contract address.

        Raises:
            FlareTxError: If the contract call fails.

        """
        if not self.swap_router:
            msg = "SparkDEX instance not fully initialized. Use SparkDEX.create()."
            raise AttributeError(msg)

        try:
            factory_address = await self.swap_router.functions.factory().call()  # pyright: ignore[reportUnknownVariableType,reportGeneralTypeIssues]
            logger.debug("Retrieved factory address", address=factory_address)
        except Exception as e:
            msg = f"Failed to get factory address: {e}"
            raise FlareTxError(msg) from e
        else:
            return factory_address  # pyright: ignore[reportUnknownVariableType]

    async def get_weth9_address(self) -> ChecksumAddress:
        """
        Get the WETH9 (Wrapped FLR) contract address.

        Returns:
            WETH9 contract address.

        Raises:
            FlareTxError: If the contract call fails.

        """
        if not self.swap_router:
            msg = "SparkDEX instance not fully initialized. Use SparkDEX.create()."
            raise AttributeError(msg)

        try:
            weth9_address = await self.swap_router.functions.WETH9().call()  # pyright: ignore[reportUnknownVariableType,reportGeneralTypeIssues]
            logger.debug("Retrieved WETH9 address", address=weth9_address)
        except Exception as e:
            msg = f"Failed to get WETH9 address: {e}"
            raise FlareTxError(msg) from e
        else:
            return weth9_address  # pyright: ignore[reportUnknownVariableType]
