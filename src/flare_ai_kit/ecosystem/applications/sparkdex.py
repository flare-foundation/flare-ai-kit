import structlog
from hexbytes import HexBytes
from web3 import Web3
from web3.contract.async_contract import AsyncContract

from flare_ai_kit.common import load_abi
from flare_ai_kit.ecosystem import (
    Contracts,
    EcosystemSettings,
)
from flare_ai_kit.ecosystem.explorer import BlockExplorer
from flare_ai_kit.ecosystem.flare import Flare

logger = structlog.get_logger(__name__)


class SparkDEX:
    @classmethod
    async def create(
        cls,
        settings: EcosystemSettings,
        contracts: Contracts,
        flare_explorer: BlockExplorer,
        flare_provider: Flare,
    ) -> "SparkDEX":
        """
        Asynchronously create a SparkDEX instance with the provided configuration.

        Initializes the universal router and swap router contracts using the provided Flare provider
        and contract addresses, then constructs a SparkDEX instance.

        Args:
            settings (EcosystemSettings): Configuration settings, including account details.
            contracts (Contracts): Contract addresses for the Flare blockchain.
            flare_explorer (BlockExplorer): Block explorer instance for transaction queries.
            flare_provider (Flare): Provider instance for blockchain interactions.

        Returns:
            SparkDEX: An initialized SparkDEX instance with configured contracts.

        """
        universalrouter_contract = flare_provider.w3.eth.contract(
            address=contracts.flare.sparkdex_universal_router,
            abi=load_abi("SparkDEXUniversalRouter"),
        )
        swaprouter_contract = flare_provider.w3.eth.contract(
            address=contracts.flare.sparkdex_swap_router,
            abi=load_abi("SparkDEXSwapRouter"),
        )

        # Create SparkDEX instance
        instance = cls(
            settings=settings,
            contracts=contracts,
            flare_explorer=flare_explorer,
            flare_provider=flare_provider,
            universalrouter_contract=universalrouter_contract,
            swaprouter_contract=swaprouter_contract,
        )
        return instance

    def __init__(
        self,
        settings: EcosystemSettings,
        contracts: Contracts,
        flare_explorer: BlockExplorer,
        flare_provider: Flare,
        universalrouter_contract: AsyncContract,
        swaprouter_contract: AsyncContract,
    ) -> None:
        if not flare_provider.address:
            raise Exception("Please set settings.account_address in your .env file.")
        self.settings = settings
        self.contracts = contracts
        self.flare_explorer = flare_explorer
        self.flare_provider = flare_provider
        self.account_address = flare_provider.address
        self.universalrouter_contract = universalrouter_contract
        self.swaprouter_contract = swaprouter_contract

    async def swap_erc20_tokens(
        self,
        token_in_addr: str,
        token_out_addr: str,
        amount_in_WEI: int,
        amount_out_min_WEI: int,
    ) -> str:
        """
        Perform an ERC-20 token swap using the SparkDEX swap router.

        This method approves the swap router to spend the input tokens if necessary, builds an exact input
        single swap transaction, simulates it, and executes it on the Flare blockchain.

        Args:
            token_in_addr (str): The Ethereum address of the input token to swap from.
            token_out_addr (str): The Ethereum address of the output token to swap to.
            amount_in_WEI (int): The amount of input tokens to swap, in wei.
            amount_out_min_WEI (int): The minimum amount of output tokens to receive, in wei.

        Returns:
            str: The hexadecimal transaction hash of the swap operation, or None if the simulation fails.

        Raises:
            Exception: If the token addresses are invalid or transaction building fails.

        """
        if self.flare_provider.address is None:
            raise ValueError("Wallet address cannot be None.")

        # =========== Approve SparkDEX to spend token_in  ==============
        allowance = await self.flare_provider.erc20_allowance(
            owner_address=self.flare_provider.address,
            token_address=Web3.to_checksum_address(token_in_addr),
            spender_address=self.contracts.flare.sparkdex_swap_router,
        )
        logger.debug(f"allowance={allowance}, amount_in_WEI={amount_in_WEI}")

        if allowance < amount_in_WEI:
            await self.flare_provider.erc20_approve(
                token_address=token_in_addr,
                spender_address=self.contracts.flare.sparkdex_swap_router,
                amount=amount_in_WEI,
            )

        # =============== Build swap transaction ==================
        fee_tier = 500  # Assuming 0.05% pool fee

        block = await self.flare_provider.w3.eth.get_block("latest")
        if "timestamp" in block:
            deadline = block["timestamp"] + 300
        else:
            raise ValueError(
                'Block fetched with w3.eth.get_block("latest") has no timestamp.'
            )

        params = (
            token_in_addr,  # Token In
            token_out_addr,  # Token Out
            fee_tier,  # Pool Fee Tier (0.05%)
            self.flare_provider.address,  # Recipient
            deadline,  # Deadline (5 min)
            amount_in_WEI,  # Amount In (exact wFLR amount)
            amount_out_min_WEI,  # Minimum amount of JOULE expected
            0,  # sqrtPriceLimitX96 (0 = no limit)
        )
        swap_fn = self.swaprouter_contract.functions.exactInputSingle(params)
        swap_tx = await self.flare_provider.build_transaction(
            swap_fn, self.flare_provider.address, custom_params={"type": 2}
        )
        # ======================= Simulate swap =========================

        simulation_ok = await self.flare_provider.eth_call(
            contract_abi=load_abi("SparkDEXSwapRouter"), call_tx=swap_tx
        )

        if not simulation_ok:
            logger.warning(
                "We stop here because the simulated send transaction was not sucessfull"
            )
            raise Exception(
                "We stop here because the simulated transaction was not sucessfull"
            )
        # ======================= Execute swap =========================
        swap_tx_hash = await self.flare_provider.sign_and_send_transaction(swap_tx)
        receipt = await self.flare_provider.w3.eth.wait_for_transaction_receipt(
            HexBytes(swap_tx_hash)
        )
        logger.debug(f"Swap transaction mined in block {receipt['blockNumber']}")
        logger.debug(f"https://flarescan.com/tx/0x{swap_tx_hash}")
        return swap_tx_hash
