"""Base wallet interface for all wallet implementations."""

from abc import ABC, abstractmethod
from typing import Any

from pydantic import BaseModel


class WalletAddress(BaseModel):
    """Represents a wallet address with associated metadata."""

    address: str
    wallet_id: str
    derivation_path: str | None = None
    chain_id: int | None = None


class TransactionRequest(BaseModel):
    """Represents a transaction request."""

    to: str
    value: str
    data: str | None = None
    gas_limit: str | None = None
    gas_price: str | None = None
    nonce: int | None = None
    chain_id: int


class SignedTransaction(BaseModel):
    """Represents a signed transaction."""

    transaction_hash: str
    signed_transaction: str
    raw_transaction: str


class WalletInterface(ABC):
    """Abstract base class for wallet implementations."""

    @abstractmethod
    async def create_wallet(self, wallet_name: str) -> str:
        """Create a new wallet and return its ID."""

    @abstractmethod
    async def get_address(
        self, wallet_id: str, derivation_path: str = "m/44'/60'/0'/0/0"
    ) -> WalletAddress:
        """Get wallet address for specified derivation path."""

    @abstractmethod
    async def sign_transaction(
        self, wallet_id: str, transaction: TransactionRequest
    ) -> SignedTransaction:
        """Sign a transaction with the specified wallet."""

    @abstractmethod
    async def export_wallet(self, wallet_id: str, password: str) -> dict[str, Any]:
        """Export wallet with encryption."""

    @abstractmethod
    async def import_wallet(
        self, encrypted_wallet: dict[str, Any], password: str
    ) -> str:
        """Import an encrypted wallet and return its ID."""

    @abstractmethod
    async def list_wallets(self) -> list[str]:
        """List all available wallet IDs."""

    @abstractmethod
    async def delete_wallet(self, wallet_id: str) -> bool:
        """Delete a wallet and return success status."""
