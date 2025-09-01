import re
from typing import Any, cast

import structlog
from hexbytes import HexBytes
from web3 import Web3
from web3.types import TxParams

from flare_ai_kit.ecosystem import (
    ChainIdConfig,
    Contracts,
    EcosystemSettings,
)
from flare_ai_kit.ecosystem.explorer import BlockExplorer
from flare_ai_kit.ecosystem.flare import Flare

logger = structlog.get_logger(__name__)


class Stargate:
    @classmethod
    async def create(
        cls,
        settings: EcosystemSettings,
        contracts: Contracts,
        chains: ChainIdConfig,
        flare_explorer: BlockExplorer,
        flare_provider: Flare,
    ) -> "Stargate":
        """
        Asynchronously create a Stargate instance with the provided configuration.

        Fetches the ABI for the StargateOFTETH contract from the block explorer and initializes a
        Stargate instance with the provided settings, contracts, chains, explorer, and provider.

        Args:
            settings (EcosystemSettings): Configuration settings, including account details.
            contracts (Contracts): Contract addresses for the Flare blockchain.
            chains (ChainIdConfig): Chain ID configuration for cross-chain operations.
            flare_explorer (BlockExplorer): Block explorer instance for querying contract ABIs.
            flare_provider (Flare): Provider instance for blockchain interactions.

        Returns:
            Stargate: An initialized Stargate instance configured for cross-chain ETH transfers.

        Raises:
            Exception: If the StargateOFTETH contract ABI cannot be fetched or initialization fails.

        """
        # Fetch ABI for StargateOFTETH contract
        oft_abi = await flare_explorer.get_contract_abi(
            contracts.flare.stargate_StargateOFTETH
        )

        # Create Stargate instance
        instance = cls(
            settings=settings,
            contracts=contracts,
            chains=chains,
            flare_explorer=flare_explorer,
            flare_provider=flare_provider,
            oft_abi=oft_abi,
        )
        return instance

    def __init__(
        self,
        settings: EcosystemSettings,
        contracts: Contracts,
        chains: ChainIdConfig,
        flare_explorer: BlockExplorer,
        flare_provider: Flare,
        oft_abi: list[dict[str, Any]],
    ) -> None:
        """
        Initialize a Stargate instance with the provided configuration and ABI.

        Sets up the Stargate instance with the necessary attributes for cross-chain ETH transfers,
        including account details, contract addresses, chain configurations, and the StargateOFTETH
        contract instance. Validates that account address and private key are set.

        Args:
            settings (EcosystemSettings): Configuration settings, including account details.
            contracts (Contracts): Contract addresses for the Flare blockchain.
            chains (ChainIdConfig): Chain ID configuration for cross-chain operations.
            flare_explorer (BlockExplorer): Block explorer instance for querying contract ABIs.
            flare_provider (Flare): Provider instance for blockchain interactions.
            oft_abi (list): ABI for the StargateOFTETH contract.

        Raises:
            Exception: If account_address is not set in the settings.

        """
        if not settings.account_address:
            raise Exception("Please set settings.account_address in your .env file.")
        self.contracts = contracts
        self.chains = chains
        self.account_address = settings.account_address
        self.flare_explorer = flare_explorer
        self.flare_provider = flare_provider
        self.oft_abi = oft_abi

        # Create Web3 contract instance to check version
        self.oft_contract = flare_provider.w3.eth.contract(
            address=contracts.flare.stargate_StargateOFTETH, abi=oft_abi
        )
        # Call oftVersion synchronously (view function)
        # version = oft_contract.functions.oftVersion().call()
        # structlog.get_logger().info("OFT Version", version=version)

    async def bridge_weth_to_chain(
        self,
        desired_amount_WEI: int,
        chain_id: int,
        max_slippage: float = 0.01,
    ) -> str:
        """
        Send ETH to the Base chain using the StargateOFTETH contract.

        Builds and executes a cross-chain transaction to transfer the specified amount of ETH to the
        Base chain by calling the `send` function on the StargateOFTETH contract. The transaction is
        simulated before execution to ensure it will succeed. Checks WETH balance and allowance,
        approving additional allowance if needed. Returns None if the amount exceeds limits or simulation fails.

        Args:
            desired_amount_WEI (int): The amount of ETH to send, in wei.
            max_slippage (float, optional): Maximum slippage tolerance as a fraction (default: 0.01).
            approve_buffer (float, optional): Buffer for approval amount (default: 0.2).

        Returns:
            str: The hexadecimal transaction hash of the send operation, or None if the amount is outside
                the allowed limits or the simulation fails.

        Raises:
            Exception: If transaction building or execution fails.

        """
        if self.flare_provider.address is None:
            raise ValueError("Wallet address cannot be None.")

        #
        # === Define parameter for the quoteOFT in the contract ===
        #
        address_hex = self.account_address[2:].lower()
        if not Web3.is_address(address_hex):
            raise ValueError(
                f"Invalid Ethereum address derived from account_address: {address_hex}"
            )
        padded_hex = "0x" + "000000000000000000000000" + address_hex
        if not re.match(r"^0x[0-9a-fA-F]{64}$", padded_hex):
            raise ValueError(f"Invalid padded hex string: {padded_hex}")
        to_address = Web3.to_bytes(hexstr=padded_hex)  # type: ignore

        amount = int(desired_amount_WEI)
        min_amount = int(desired_amount_WEI - (desired_amount_WEI * max_slippage))
        extra_options = b""
        compose_msg = b""
        oft_cmd = b""
        send_param = (
            chain_id,
            to_address,
            amount,
            min_amount,
            extra_options,
            compose_msg,
            oft_cmd,
        )
        #
        # === Call the quoteOFT function ===
        #
        (
            oftLimits,
            oftFeeDetails,
            oftReceipt,
        ) = await self.oft_contract.functions.quoteOFT(send_param).call()
        logger.info(
            "QuoteOFT result",
            oft_limits=oftLimits,
            oft_fee_details=oftFeeDetails,
            oft_receipt=oftReceipt,
        )
        if desired_amount_WEI > oftLimits[1]:
            logger.warning(
                "Desired send amount exceeds max limit",
                desired_amount_wei=desired_amount_WEI,
                min_limit_eth=oftLimits[0] / 1e18,
                max_limit_eth=oftLimits[1] / 1e18,
            )
            raise ValueError("Desired send amount exceeds max limit")

        if desired_amount_WEI < oftLimits[0]:
            logger.warning(
                "Desired send amount is less than min limit",
                desired_amount_wei=desired_amount_WEI,
                min_limit_eth=oftLimits[0] / 1e18,
                max_limit_eth=oftLimits[1] / 1e18,
            )
            raise ValueError("Desired send amount is less than min limit")
        #
        # === Call the quoteSend function ===
        #
        messagingFee = await self.oft_contract.functions.quoteSend(
            send_param, False
        ).call()
        nativeFee, lzTokenFee = messagingFee
        logger.info("QuoteSend result", native_fee=nativeFee, lz_token_fee=lzTokenFee)
        #
        # === Check allowance and balance ===
        #
        weth_balance = await self.flare_provider.erc20_balanceOf(
            self.account_address, self.contracts.flare.weth
        )
        allowance = await self.flare_provider.erc20_allowance(
            owner_address=self.account_address,
            token_address=self.contracts.flare.weth,
            spender_address=self.contracts.flare.stargate_StargateOFTETH,
        )
        logger.debug(
            "WETH balance check",
            weth_balance_eth=weth_balance / 1e18,
            percentage_of_desired=round(100 * weth_balance / desired_amount_WEI, 2),
            weth_balance_wei=weth_balance,
            desired_amount_wei=desired_amount_WEI,
        )
        logger.debug(
            "Allowance check",
            allowance_wei=allowance,
            percentage_of_desired=round(100 * allowance / desired_amount_WEI, 2),
            desired_amount_wei=desired_amount_WEI,
        )
        # === Call the approve function in the token contract, if needed ===
        #
        if desired_amount_WEI > allowance:
            _tx_approval_hash = await self.flare_provider.erc20_approve(
                token_address=self.contracts.flare.weth,
                spender_address=self.contracts.flare.stargate_StargateOFTETH,
                amount=desired_amount_WEI,
            )
        #
        # === Create send transaction ===#
        #
        send_fn = self.oft_contract.functions.send(
            send_param, messagingFee, self.flare_provider.address
        )
        send_tx = await self.flare_provider.build_transaction(
            function_call=send_fn,
            from_addr=self.flare_provider.address,
            custom_params=cast("TxParams", {"value": nativeFee}),
        )
        #
        # === Simulate send transaction ===
        #
        simulation_ok = await self.flare_provider.eth_call(
            contract_abi=self.oft_abi, call_tx=send_tx
        )

        if not simulation_ok:
            logger.warning(
                "We stop here because the simulated send transaction was not sucessfull"
            )
            raise Exception(
                "We stop here because the simulated send transaction was not sucessfull"
            )
        #
        # === Call the send function ===
        #
        send_tx_hash = await self.flare_provider.sign_and_send_transaction(send_tx)
        receipt = await self.flare_provider.w3.eth.wait_for_transaction_receipt(
            HexBytes(send_tx_hash)
        )
        logger.debug("Send transaction mined", block_number=receipt["blockNumber"])
        logger.debug(
            "Transaction URLs",
            flarescan_url=f"https://flarescan.com/tx/0x{send_tx_hash}",
            layerzeroscan_url=f"https://layerzeroscan.com/tx/0x{send_tx_hash}",
        )
        return send_tx_hash
