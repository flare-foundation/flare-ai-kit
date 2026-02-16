from eth_typing import ChecksumAddress
from web3 import AsyncHTTPProvider, AsyncWeb3

from flare_ai_kit.common.utils import load_abi
from flare_ai_kit.config import AppSettings
from flare_ai_kit.ecosystem.settings import Contracts


class KineticClient:
    def __init__(self):
        self.settings = AppSettings().ecosystem
        self.client = AsyncWeb3(
            AsyncHTTPProvider(str(self.settings.web3_provider_url)),
        )
        self.contracts = Contracts()
        self.contract_address = self.contracts.flare.kinetic_comptroller
        self.ksflr_address = self.contracts.flare.kinetic_ksflr
        self.abi = load_abi("kineticComptroller")
        self.sflr_abi = load_abi("kineticSflr")
        self.contract = self.client.eth.contract(
            address=self.contract_address,
            abi=self.abi,
        )
        self.sflr_contract = self.client.eth.contract(
            address=self.ksflr_address,
            abi=self.sflr_abi,
        )

    async def describe_kinetic_services(self) -> str:
        return """
        Kinetic is a leading lending protocol on the Flare Network,
        reshaping decentralized finance (DeFi) with cutting-edge technology
        and strategic partnerships.
        Kinetic makes lending and borrowing digital assets like BTC, DOGE,
        and XRP simple and secure. 
        Leveraging the Flare Time Series Oracle (FTSOv2) and FAssets, 
        we enable users to unlock the value of non-native assets 
        within a decentralized, trustless framework. 
        FTSOv2 provides reliable, decentralized price feeds, while 
        FAssets expand the range of assets available for lending and borrowing.
        """

    async def get_kinetic_contract_address(self) -> ChecksumAddress | None:
        """
        Get the Kinetic contract address for the current network.
        """
        return self.contract_address

    async def get_assets_in(self, user: ChecksumAddress) -> list[str]:
        """
        Returns a list of markets the user has entered.
        """
        try:
            return await self.contract.functions.getAssetsIn(user).call()
        except Exception as e:
            raise RuntimeError(f"Failed to fetch assets in: {e}")

    async def get_account_liquidity(self, user: ChecksumAddress) -> dict[str, int]:
        """
        Returns the account's liquidity and shortfall values.
        """
        try:
            (
                err,
                liquidity,
                shortfall,
            ) = await self.contract.functions.getAccountLiquidity(user).call()
            return {"error_code": err, "liquidity": liquidity, "shortfall": shortfall}
        except Exception as e:
            raise RuntimeError(f"Failed to fetch account liquidity: {e}")

    async def check_membership(
        self, user: ChecksumAddress, ctoken_address: ChecksumAddress
    ) -> bool:
        """
        Checks whether a user has entered a specific market.
        """
        try:
            return await self.contract.functions.checkMembership(
                user, ctoken_address
            ).call()
        except Exception as e:
            raise RuntimeError(f"Failed to check membership: {e}")

    async def deposit(self, amount: int):
        """
        Deposits KSFLR tokens to the Kinetic protocol.
        """
        if self.settings.account_address is None:
            raise ValueError("Address is not set")
        try:
            tx = await self.sflr_contract.functions.mint(amount).build_transaction(
                {
                    "gas": 200000,
                    "gasPrice": await self.client.eth.gas_price,
                    "nonce": await self.client.eth.get_transaction_count(
                        self.settings.account_address
                    ),
                }
            )
            if self.settings.account_private_key is None:
                raise ValueError("Private key is not set")
            signed_tx = self.client.eth.account.sign_transaction(
                tx, private_key=self.settings.account_private_key.get_secret_value()
            )
            tx_hash = await self.client.eth.send_raw_transaction(
                signed_tx.raw_transaction
            )
            receipt = await self.client.eth.wait_for_transaction_receipt(tx_hash)
            return receipt
        except Exception as e:
            raise RuntimeError(f"Failed to deposit KSFLR: {e}")

    async def withdraw(self, amount: int):
        """
        Withdraws KSFLR tokens from the Kinetic protocol.
        """
        if self.settings.account_address is None:
            raise ValueError("Address is not set")
        try:
            tx = await self.sflr_contract.functions.redeemUnderlying(
                amount
            ).build_transaction(
                {
                    "gas": 200000,
                    "gasPrice": await self.client.eth.gas_price,
                    "nonce": await self.client.eth.get_transaction_count(
                        self.settings.account_address
                    ),
                }
            )
            if self.settings.account_private_key is None:
                raise ValueError("Private key is not set")
            signed_tx = self.client.eth.account.sign_transaction(
                tx, private_key=self.settings.account_private_key.get_secret_value()
            )
            tx_hash = await self.client.eth.send_raw_transaction(
                signed_tx.raw_transaction
            )
            receipt = await self.client.eth.wait_for_transaction_receipt(tx_hash)
            return receipt
        except Exception as e:
            raise RuntimeError(f"Failed to withdraw KSFLR: {e}")
