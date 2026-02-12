"""Cyclo protocol connector for non-liquidating leverage on Flare."""

from typing import TYPE_CHECKING, Self

import structlog
from eth_typing import ChecksumAddress

from flare_ai_kit.common import CycloError, load_abi
from flare_ai_kit.ecosystem.flare import Flare
from flare_ai_kit.ecosystem.settings import EcosystemSettings

if TYPE_CHECKING:
    from web3.contract.contract import Contract

logger = structlog.get_logger(__name__)


class Cyclo(Flare):
    """
    Cyclo protocol connector for non-liquidating leverage.

    Cyclo allows users to lock collateral (sFLR) and mint cy* tokens that trade
    between $0-$1. Users can unlock collateral by burning cy* tokens + receipt NFTs.
    """

    def __init__(self, settings: EcosystemSettings) -> None:
        """Initialize Cyclo connector."""
        super().__init__(settings)
        self.vault_contract: Contract | None = None  # pyright: ignore[reportUnknownVariableType, reportGeneralTypeIssues]
        self.receipt_contract: Contract | None = None  # pyright: ignore[reportUnknownVariableType, reportGeneralTypeIssues]

    @classmethod
    async def create(cls, settings: EcosystemSettings) -> Self:
        """
        Create and initialize a new Cyclo instance.

        Args:
            settings: Ecosystem settings

        Returns:
            Initialized Cyclo instance

        Raises:
            CycloError: If initialization fails

        """
        instance = cls(settings)
        logger.info("Initializing Cyclo...")

        try:
            # Get addresses from settings
            vault_address = (
                settings.contracts.coston2.cyclo_cysflr_vault
                if settings.is_testnet
                else settings.contracts.flare.cyclo_cysflr_vault
            )
            receipt_address = (
                settings.contracts.coston2.cyclo_cysflr_receipt
                if settings.is_testnet
                else settings.contracts.flare.cyclo_cysflr_receipt
            )

            if not vault_address or not receipt_address:
                msg = "Cyclo contract addresses not configured in settings"
                raise CycloError(msg)

            # Initialize cysFLR vault contract
            instance.vault_contract = instance.w3.eth.contract(  # pyright: ignore[reportUnknownMemberType, reportAttributeAccessIssue]
                address=instance.w3.to_checksum_address(vault_address),
                abi=load_abi("CycloVaultSFLR"),
            )

            # Initialize cysFLR receipt contract (ERC1155)
            instance.receipt_contract = instance.w3.eth.contract(  # pyright: ignore[reportUnknownMemberType, reportAttributeAccessIssue]
                address=instance.w3.to_checksum_address(receipt_address),
                abi=load_abi("CycloReceiptSFLR"),
            )

            logger.debug(
                "Cyclo initialized",
                vault_address=vault_address,
                receipt_address=receipt_address,
            )
            return instance  # noqa: TRY300

        except Exception as e:
            msg = f"Failed to initialize Cyclo: {e}"
            logger.exception(msg)
            raise CycloError(msg) from e

    async def deposit_sflr(
        self,
        assets: int,
        recipient: str,
        min_share_ratio: int = 0,
        receipt_info: bytes = b"",
    ) -> str:
        """
        Lock sFLR and mint cysFLR tokens + receipt NFT.

        Args:
            assets: Amount of sFLR to lock (in wei, 18 decimals)
            recipient: Address to receive cysFLR tokens and receipt NFT
            min_share_ratio: Minimum acceptable share ratio (for slippage protection)
            receipt_info: Optional metadata for the receipt

        Returns:
            Transaction hash

        Raises:
            CycloError: If deposit fails

        """
        if not self.vault_contract:
            msg = "Cyclo vault contract not initialized"
            raise CycloError(msg)

        logger.info(
            "Depositing sFLR to Cyclo",
            assets=assets,
            recipient=recipient,
            min_share_ratio=min_share_ratio,
        )

        try:
            # Build the deposit transaction
            function_call = self.vault_contract.functions.deposit(
                assets, recipient, min_share_ratio, receipt_info
            )

            # Execute the transaction
            tx = await self.build_transaction(function_call, self.address)  # pyright: ignore[reportArgumentType]
            if not tx:
                msg = "Failed to build deposit transaction"
                raise CycloError(msg)

            tx_hash = await self.sign_and_send_transaction(tx)
            if not tx_hash:
                msg = "Failed to send deposit transaction"
                raise CycloError(msg)

            logger.info("sFLR deposit successful", tx_hash=tx_hash)
            return tx_hash  # noqa: TRY300

        except Exception as e:
            msg = f"Failed to deposit sFLR to Cyclo: {e}"
            logger.exception(msg)
            raise CycloError(msg) from e

    async def redeem_sflr(
        self,
        shares: int,
        recipient: str,
        owner: str,
        receipt_id: int,
        receipt_info: bytes = b"",
    ) -> str:
        """
        Burn cysFLR tokens + receipt NFT to unlock sFLR.

        Args:
            shares: Amount of cysFLR tokens to burn (in wei, 18 decimals)
            recipient: Address to receive unlocked sFLR
            owner: Address that owns the cysFLR tokens and receipt NFT
            receipt_id: ID of the receipt NFT (price at time of lock)
            receipt_info: Optional metadata

        Returns:
            Transaction hash

        Raises:
            CycloError: If redemption fails

        """
        if not self.vault_contract:
            msg = "Cyclo vault contract not initialized"
            raise CycloError(msg)

        logger.info(
            "Redeeming sFLR from Cyclo",
            shares=shares,
            recipient=recipient,
            owner=owner,
            receipt_id=receipt_id,
        )

        try:
            # Build the redeem transaction
            function_call = self.vault_contract.functions.redeem(
                shares, recipient, owner, receipt_id, receipt_info
            )

            # Execute the transaction
            tx = await self.build_transaction(function_call, self.address)  # pyright: ignore[reportArgumentType]
            if not tx:
                msg = "Failed to build redeem transaction"
                raise CycloError(msg)

            tx_hash = await self.sign_and_send_transaction(tx)
            if not tx_hash:
                msg = "Failed to send redeem transaction"
                raise CycloError(msg)

            logger.info("sFLR redemption successful", tx_hash=tx_hash)
            return tx_hash  # noqa: TRY300

        except Exception as e:
            msg = f"Failed to redeem sFLR from Cyclo: {e}"
            logger.exception(msg)
            raise CycloError(msg) from e

    async def get_cysflr_balance(self, address: str) -> int:
        """
        Get cysFLR token balance for an address.

        Args:
            address: Address to check balance for

        Returns:
            Balance in wei (18 decimals)

        Raises:
            CycloError: If balance query fails

        """
        if not self.vault_contract:
            msg = "Cyclo vault contract not initialized"
            raise CycloError(msg)

        try:
            checksum_address = self.w3.to_checksum_address(address)
            balance: int = await self.vault_contract.functions.balanceOf(  # pyright: ignore[reportUnknownVariableType, reportGeneralTypeIssues]
                checksum_address
            ).call()
            logger.debug("cysFLR balance retrieved", address=address, balance=balance)
            return balance  # noqa: TRY300

        except Exception as e:
            msg = f"Failed to get cysFLR balance: {e}"
            logger.exception(msg)
            raise CycloError(msg) from e

    async def get_receipt_balance(self, address: str, receipt_id: int) -> int:
        """
        Get receipt NFT balance for a specific ID.

        Args:
            address: Address to check balance for
            receipt_id: ID of the receipt NFT

        Returns:
            Balance (number of receipt NFTs with this ID)

        Raises:
            CycloError: If balance query fails

        """
        if not self.receipt_contract:
            msg = "Cyclo receipt contract not initialized"
            raise CycloError(msg)

        try:
            checksum_address = self.w3.to_checksum_address(address)
            balance: int = await self.receipt_contract.functions.balanceOf(  # pyright: ignore[reportUnknownVariableType, reportGeneralTypeIssues]
                checksum_address, receipt_id
            ).call()
            logger.debug(
                "Receipt balance retrieved",
                address=address,
                receipt_id=receipt_id,
                balance=balance,
            )
            return balance  # noqa: TRY300

        except Exception as e:
            msg = f"Failed to get receipt balance: {e}"
            logger.exception(msg)
            raise CycloError(msg) from e

    async def get_vault_asset(self) -> ChecksumAddress:
        """
        Get the underlying asset address (sFLR) for the vault.

        Returns:
            Checksum address of the underlying asset

        Raises:
            CycloError: If query fails

        """
        if not self.vault_contract:
            msg = "Cyclo vault contract not initialized"
            raise CycloError(msg)

        try:
            asset: ChecksumAddress = await self.vault_contract.functions.asset().call()  # pyright: ignore[reportUnknownVariableType, reportGeneralTypeIssues]
            logger.debug("Vault asset retrieved", asset=asset)
            return asset  # noqa: TRY300

        except Exception as e:
            msg = f"Failed to get vault asset: {e}"
            logger.exception(msg)
            raise CycloError(msg) from e
