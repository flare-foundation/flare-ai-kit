import re

import structlog
from decimal import Decimal

from flare_ai_kit.ecosystem import (
    Contracts,
    EcosystemSettingsModel,
)
from flare_ai_kit.ecosystem.explorer import BlockExplorer
from flare_ai_kit.ecosystem.flare import Flare

logger = structlog.get_logger(__name__)


class Cyclo:
    @classmethod
    async def create(
        cls,
        settings: EcosystemSettingsModel,
        contracts: Contracts,
        flare_explorer: BlockExplorer,
        flare_provider: Flare,
    ) -> "Cyclo":
        instance = cls(
            settings=settings,
            contracts=contracts,
            flare_explorer=flare_explorer,
            flare_provider=flare_provider,
        )
        return instance

    def __init__(
        self,
        settings: EcosystemSettingsModel,
        contracts: Contracts,
        flare_explorer: BlockExplorer,
        flare_provider: Flare,
    ) -> None:
        self.contracts = contracts
        self.account_address = settings.account_address
        self.flare_explorer = flare_explorer
        self.flare_provider = flare_provider

    def get_addresses(self, token: str) -> (str, str):
        """
        Retrieve the token address and corresponding Cyclo contract address for a specified token.

        Args:
            token (str): The token symbol (case-insensitive). Supported values are "sflr" or "weth".

        Returns:
            Tuple[str, str]: A tuple containing:
                - token_address (str): The Ethereum address of the specified token.
                - cyclo_address (str): The Ethereum address of the corresponding Cyclo contract.

        Raises:
            Exception: If the token is not "sflr" or "weth", raises an exception with the message "Unsupported token".

        """
        token = token.lower()
        match token:
            case "sflr":
                token_address = self.contracts.flare.sflr
                cyclo_address = self.contracts.flare.cyclo_cysFLR
            case "weth":
                token_address = self.contracts.flare.weth
                cyclo_address = self.contracts.flare.cyclo_cywETH
            case _:
                raise Exception("Unsupported token")

        return token_address, cyclo_address

    async def lock(self, token: str, amount_WEI: float) -> str:
        """
        Lock a specified amount of tokens in a Cyclo contract and return the transaction hash and deposit ID.

        Args:
            token (str): The token to lock (case-insensitive, "sflr" or "weth").
            amount_WEI (int): The amount of tokens to lock, in wei.

        Returns:
            Tuple[str, int]: A tuple containing:
                - transaction_hash (str): The hexadecimal transaction hash of the lock operation.
                - deposit_id (int): The deposit ID from the Deposit event.

        Raises:
            Exception: If the token is unsupported, balance is insufficient, or transaction building fails.
            ValueError: If the transaction fails with a ZeroSharesAmount error or no Deposit event is found.

        """

        # ======== Get addresses from token string ==============
        token_address, cyclo_address = self.get_addresses(token)

        # ======== Checking token balance ==============
        balance = await self.flare_provider.erc20_balanceOf(
            self.flare_provider.address, token_address
        )
        logger.debug(
            f"Token balance is {round(balance / 1e18, 4)} ({round(100 * balance / amount_WEI, 2)}%) of desired amount. balance={balance} amount={amount_WEI}"
        )
        if balance < amount_WEI:
            raise Exception("Not enough funds to lock.")

        # ============= Give allowance if needed  ===============
        allowance = await self.flare_provider.erc20_allowance(
            owner_address=self.flare_provider.address,
            token_address=token_address,
            spender_address=cyclo_address,
        )
        logger.debug(
            f"Allowance is {allowance}. This is {round(100 * allowance / amount_WEI, 2)}% of amount."
        )

        if allowance < amount_WEI:
            await self.flare_provider.erc20_approve(
                token_address=token_address,
                spender_address=cyclo_address,
                amount=amount_WEI,
            )

        # ============= Build transaction ================
        cyclo_contract = self.flare_provider.w3.eth.contract(
            address=cyclo_address, abi=self.get_cyclo_contract_abi()
        )

        amount = amount_WEI
        receiver = self.flare_provider.address
        deposit_min_share_ratio = 0
        receipt_information = b""
        lock_fn = cyclo_contract.functions.deposit(
            amount, receiver, deposit_min_share_ratio, receipt_information
        )

        try:
            lock_tx = await self.flare_provider.build_transaction(
                function_call=lock_fn, from_addr=self.flare_provider.address
            )
            logger.debug(f"lock_tx sucessful: {lock_tx}")
        except Exception as e:
            hex_match = re.search(r"0x[a-fA-F0-9]+", str(e))
            if hex_match and hex_match.group() == "0xfc8c8063":
                raise ValueError(
                    "Lock build_transaction failed: ZeroSharesAmount()"
                ) from e
            raise Exception(f"Building transaction failed: {e!s}") from e

        logger.debug("lock", tx=lock_tx)

        # ============= Simulate transaction ================
        simulation_ok = await self.flare_provider.eth_call(
            contract_abi=self.get_cyclo_contract_abi(), call_tx=lock_tx
        )
        if not simulation_ok:
            logger.warning(
                "We stop here because the simulated transaction was not sucessfull"
            )
            return None

        # ============= Execute transaction ================
        lock_tx_hash = await self.flare_provider.sign_and_send_transaction(lock_tx)
        receipt = await self.flare_provider.w3.eth.wait_for_transaction_receipt(
            lock_tx_hash
        )
        logger.debug(f"Lock transaction mined in block {receipt['blockNumber']}")
        logger.debug(f"https://flarescan.com/tx/0x{lock_tx_hash}")

        deposit_event = cyclo_contract.events.Deposit()
        for log in receipt.get("logs", []):
            event_data = deposit_event.process_log(log)
            if event_data:
                deposit_id = event_data["args"]["id"]
                logger.debug(f"Lock transaction deposit id: {deposit_id}")
                return receipt["transactionHash"].hex(), deposit_id
        raise ValueError("No Deposit event found in transaction receipt")

    async def unlock(
        self, token: str, deposit_id: int, unlock_proportion: float
    ) -> str:
        """
        Unlock a proportion of tokens from a Cyclo contract and return the transaction hash.

        Args:
            token (str): The token to unlock (case-insensitive, "sflr" or "weth").
            deposit_id (int): The deposit ID from a previous lock operation.
            unlock_proportion (float): The proportion of the deposit to unlock (0.0 to 1.0).

        Returns:
            str: The hexadecimal transaction hash of the unlock operation.

        Raises:
            Exception: If the token is unsupported or transaction building fails.

        """
        # ============= Map token string to addresses ================
        _token_address, cyclo_address = self.get_addresses(token)

        # ============= Build transaction ================
        cyclo_contract = self.flare_provider.w3.eth.contract(
            address=cyclo_address, abi=self.get_cyclo_contract_abi()
        )

        # (uint256 shares, address receiver, address owner, uint256 id, bytes receiptInformation)
        shares = int(Decimal(str(deposit_id)) * Decimal(str(unlock_proportion)))
        receiver = self.flare_provider.address
        owner = self.flare_provider.address
        id = deposit_id
        receiptInformation = b""
        unlock_fn = cyclo_contract.functions.redeem(
            shares, receiver, owner, id, receiptInformation
        )
        logger.debug("unlock_fn", tx=unlock_fn)
        unlock_tx = await self.flare_provider.build_transaction(
            function_call=unlock_fn, from_addr=self.flare_provider.address
        )

        logger.debug("Unlock", tx=unlock_tx)

        # ============= Simulate transaction ================
        simulation_ok = await self.flare_provider.eth_call(
            contract_abi=self.get_cyclo_contract_abi(), call_tx=unlock_tx
        )
        if not simulation_ok:
            logger.warning(
                "We stop here because the simulated transaction was not sucessfull"
            )
            return None

        # ============= Execute transaction ================
        unlock_tx_hash = await self.flare_provider.sign_and_send_transaction(unlock_tx)
        receipt = await self.flare_provider.w3.eth.wait_for_transaction_receipt(
            unlock_tx_hash
        )
        logger.debug(f"unlock transaction mined in block {receipt['blockNumber']}")
        logger.debug(f"https://flarescan.com/tx/0x{unlock_tx_hash}")

        return unlock_tx_hash

    def get_cyclo_contract_abi(self) -> list:
        """
        Retrieve the ABI for the Cyclo contract.

        Returns:
            list: The ABI (Application Binary Interface) for the Cyclo contract, defining the deposit and redeem functions.

        """
        return [
            {
                "inputs": [
                    {"internalType": "uint256", "name": "assets", "type": "uint256"},
                    {"internalType": "address", "name": "receiver", "type": "address"},
                    {
                        "internalType": "uint256",
                        "name": "depositMinShareRatio",
                        "type": "uint256",
                    },
                    {
                        "internalType": "bytes",
                        "name": "receiptInformation",
                        "type": "bytes",
                    },
                ],
                "name": "deposit",
                "outputs": [{"internalType": "uint256", "name": "", "type": "uint256"}],
                "stateMutability": "payable",
                "type": "function",
            },
            {
                "inputs": [
                    {"internalType": "uint256", "name": "shares", "type": "uint256"},
                    {"internalType": "address", "name": "receiver", "type": "address"},
                    {"internalType": "address", "name": "owner", "type": "address"},
                    {"internalType": "uint256", "name": "id", "type": "uint256"},
                    {
                        "internalType": "bytes",
                        "name": "receiptInformation",
                        "type": "bytes",
                    },
                ],
                "name": "redeem",
                "outputs": [{"internalType": "uint256", "name": "", "type": "uint256"}],
                "stateMutability": "nonpayable",
                "type": "function",
            },
            {
                "anonymous": False,
                "inputs": [
                    {
                        "indexed": False,
                        "internalType": "address",
                        "name": "sender",
                        "type": "address",
                    },
                    {
                        "indexed": False,
                        "internalType": "address",
                        "name": "owner",
                        "type": "address",
                    },
                    {
                        "indexed": False,
                        "internalType": "uint256",
                        "name": "assets",
                        "type": "uint256",
                    },
                    {
                        "indexed": False,
                        "internalType": "uint256",
                        "name": "shares",
                        "type": "uint256",
                    },
                    {
                        "indexed": False,
                        "internalType": "uint256",
                        "name": "id",
                        "type": "uint256",
                    },
                    {
                        "indexed": False,
                        "internalType": "bytes",
                        "name": "receiptInformation",
                        "type": "bytes",
                    },
                ],
                "name": "Deposit",
                "type": "event",
            },
        ]
