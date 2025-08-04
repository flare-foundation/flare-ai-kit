from eth_typing import ChecksumAddress
from web3 import AsyncHTTPProvider, AsyncWeb3
from web3.middleware import (
    ExtraDataToPOAMiddleware,  # pyright: ignore[reportUnknownVariableType]
)

from flare_ai_kit.common.utils import load_abi
from flare_ai_kit.config import AppSettings
from flare_ai_kit.ecosystem.settings import Contracts


class CyloClient:
    """
    Client for interacting with the Cylo protocol.
    """

    def __init__(self):
        self.settings = AppSettings().ecosystem
        self.client = AsyncWeb3(
            AsyncHTTPProvider(str(self.settings.web3_provider_url)),
        )
        self.client.middleware_onion.inject(ExtraDataToPOAMiddleware, layer=0)  # pyright: ignore[reportUnknownArgumentType]
        self.contracts = Contracts()
        self.address = self.settings.account_address
        self.private_key = self.settings.account_private_key
        self.contract_address = self.contracts.flare.cylo_cysflr
        self.abi = load_abi("cylo")
        self.contract = self.client.eth.contract(
            address=self.contract_address,
            abi=self.abi,
        )

    def describe_cylo_services(self) -> str:
        return """
        Cylo is a decentralized protocol on the Flare Network,
        enabling users to create and manage synthetic assets.
        It allows for the creation of synthetic assets that track the value of real-world assets,
        providing a bridge between traditional finance and decentralized finance (DeFi).
        Cylo leverages the Flare Time Series Oracle (FTSOv2) for accurate price feeds,
        ensuring that synthetic assets are always pegged to their underlying assets.
        """

    async def convert_to_shares(self, assets: int, id: int) -> int:
        return await self.contract.functions.convertToShares(assets, id).call()

    async def convert_to_assets(self, shares: int, id: int) -> int:
        return await self.contract.functions.convertToAssets(shares, id).call()

    async def deposit(
        self,
        amount: int,
        receiver: ChecksumAddress,
        min_share_ratio: int,
        receipt_data: bytes,
    ):
        """
        Deposit assets into the Cylo protocol.
        """
        if self.address is None:
            raise ValueError("Account address is not set")
        nonce = await self.client.eth.get_transaction_count(self.address)
        tx = await self.contract.functions.deposit(
            amount, receiver, min_share_ratio, receipt_data
        ).build_transaction(
            {
                "from": self.address,
                "nonce": nonce,
                "gas": 3000000,
                "gasPrice": self.client.to_wei(50, "gwei"),
            }
        )
        if self.private_key is None:
            raise ValueError("Private key is not set")
        signed = self.client.eth.account.sign_transaction(
            tx, self.private_key.get_secret_value()
        )
        return await self.client.eth.send_raw_transaction(signed.raw_transaction)

    async def mint(
        self,
        shares: int,
        receiver: ChecksumAddress,
        min_share_ratio: int,
        receipt_data: bytes,
    ):
        if self.address is None:
            raise ValueError("Account address is not set")
        nonce = await self.client.eth.get_transaction_count(self.address)
        tx = await self.contract.functions.mint(
            shares, receiver, min_share_ratio, receipt_data
        ).build_transaction(
            {
                "from": self.address,
                "nonce": nonce,
                "gas": 3000000,
                "gasPrice": self.client.to_wei(50, "gwei"),
            }
        )
        if self.private_key is None:
            raise ValueError("Private key is not set")
        signed = self.client.eth.account.sign_transaction(
            tx, self.private_key.get_secret_value()
        )
        return await self.client.eth.send_raw_transaction(signed.raw_transaction)

    async def withdraw(
        self,
        assets: int,
        receiver: ChecksumAddress,
        owner: ChecksumAddress,
        id: int,
        receipt_data: bytes,
    ):
        if self.address is None:
            raise ValueError("Account address is not set")
        nonce = await self.client.eth.get_transaction_count(self.address)
        tx = await self.contract.functions.withdraw(
            assets, receiver, owner, id, receipt_data
        ).build_transaction(
            {
                "from": self.address,
                "nonce": nonce,
                "gas": 3000000,
                "gasPrice": self.client.to_wei(50, "gwei"),
            }
        )
        if self.private_key is None:
            raise ValueError("Private key is not set")
        signed = self.client.eth.account.sign_transaction(
            tx, self.private_key.get_secret_value()
        )
        return await self.client.eth.send_raw_transaction(signed.raw_transaction)

    async def redeem(
        self,
        shares: int,
        receiver: ChecksumAddress,
        owner: ChecksumAddress,
        id: int,
        receipt_data: bytes,
    ):
        if self.address is None:
            raise ValueError("Account address is not set")
        nonce = await self.client.eth.get_transaction_count(self.address)
        tx = await self.contract.functions.redeem(
            shares, receiver, owner, id, receipt_data
        ).build_transaction(
            {
                "from": self.address,
                "nonce": nonce,
                "gas": 3000000,
                "gasPrice": self.client.to_wei(50, "gwei"),
            }
        )
        if self.private_key is None:
            raise ValueError("Private key is not set")
        signed = self.client.eth.account.sign_transaction(
            tx, self.private_key.get_secret_value()
        )
        return await self.client.eth.send_raw_transaction(signed.raw_transaction)
