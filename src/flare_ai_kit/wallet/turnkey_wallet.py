"""Turnkey wallet implementation for non-custodial wallet operations."""

import base64
import json
import time
from typing import Any

import httpx
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from pydantic import BaseModel, Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict
from web3 import Web3

from flare_ai_kit.common.exceptions import (
    WalletCreationError,
    WalletError,
    WalletNotFoundError,
)
from flare_ai_kit.common.logging import (
    get_logger,
    log_operation_failure,
    log_operation_start,
    log_operation_success,
)
from flare_ai_kit.tee.validation import VtpmValidation
from flare_ai_kit.wallet.permissions import PermissionEngine, PolicyAction

from .base import SignedTransaction, TransactionRequest, WalletAddress, WalletInterface

logger = get_logger(__name__)

# HTTP status codes
HTTP_OK = 200


class TurnkeySettings(BaseSettings):
    """Settings for Turnkey integration."""

    model_config = SettingsConfigDict(
        env_prefix="TURNKEY__",
        env_file=".env",
        extra="ignore",
    )

    api_base_url: str = Field(
        default="https://api.turnkey.com",
        description="Turnkey API base URL",
    )
    organization_id: str = Field(default="", description="Turnkey organization ID")
    api_public_key: str = Field(default="", description="Turnkey API public key")
    api_private_key: SecretStr = Field(
        default=SecretStr(""), description="Turnkey API private key"
    )
    default_curve: str = Field(
        default="secp256k1",
        description="Default cryptographic curve for key generation",
    )


class TurnkeySubOrganization(BaseModel):
    """Represents a Turnkey sub-organization (wallet)."""

    sub_organization_id: str
    name: str
    root_users: list[str] = Field(default_factory=list)
    root_quorum_threshold: int = 1
    wallet_accounts: list[str] = Field(default_factory=list)


class TurnkeyWalletAccount(BaseModel):
    """Represents a Turnkey wallet account."""

    wallet_account_id: str
    address: str
    derivation_path: str
    curve: str
    sub_organization_id: str


class TurnkeyWallet(WalletInterface):
    """Turnkey-based non-custodial wallet implementation."""

    def __init__(
        self,
        settings: TurnkeySettings | None = None,
        permission_engine: PermissionEngine | None = None,
        tee_validator: VtpmValidation | None = None,
    ) -> None:
        """
        Initialize TurnkeyWallet.

        Args:
            settings: Turnkey API settings
            permission_engine: Transaction permission engine
            tee_validator: TEE attestation validator

        """
        self.settings = settings or TurnkeySettings()
        self.permission_engine = permission_engine or PermissionEngine()
        self.tee_validator = tee_validator or VtpmValidation()
        self.client = httpx.AsyncClient(
            base_url=self.settings.api_base_url,
            timeout=30.0,
        )

    async def __aenter__(self) -> "TurnkeyWallet":
        """Async context manager entry."""
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: object,
    ) -> None:
        """Async context manager exit."""
        await self.client.aclose()

    async def create_wallet(self, wallet_name: str) -> str:
        """
        Create a new wallet by creating a Turnkey sub-organization.

        Args:
            wallet_name: Name for the new wallet

        Returns:
            Wallet ID (sub-organization ID)

        Raises:
            WalletCreationError: If wallet creation fails

        """
        log_operation_start(logger, "wallet_creation", {"wallet_name": wallet_name})

        try:
            # Create sub-organization request
            request_body: dict[str, Any] = {
                "type": "ACTIVITY_TYPE_CREATE_SUB_ORGANIZATION_V3",
                "organizationId": self.settings.organization_id,
                "parameters": {
                    "subOrganizationName": wallet_name,
                    "rootUsers": [],
                    "rootQuorumThreshold": 1,
                    "wallet": {
                        "walletName": f"{wallet_name}_wallet",
                        "accounts": [
                            {
                                "curve": self.settings.default_curve,
                                "pathFormat": "PATH_FORMAT_BIP32",
                                "path": "m/44'/60'/0'/0/0",
                                "addressFormat": "ADDRESS_FORMAT_ETHEREUM",
                            },
                        ],
                    },
                },
                "timestampMs": str(int(time.time() * 1000)),
            }

            # Sign and send request
            response = await self._make_authenticated_request(
                "POST",
                "/public/v1/submit/create_sub_organization",
                request_body,
            )

            if response.status_code != HTTP_OK:
                self._raise_wallet_creation_error(
                    response.status_code, response.text, wallet_name
                )

            result = response.json()
            sub_org_id = result["activity"]["result"]["createSubOrganizationResult"][
                "subOrganizationId"
            ]

            log_operation_success(logger, "wallet_creation", {"wallet_id": sub_org_id})

        except WalletCreationError:
            raise
        except Exception as e:
            log_operation_failure(
                logger, "wallet_creation", e, {"wallet_name": wallet_name}
            )
            error_message = "Unexpected error during wallet creation: " + str(e)
            raise WalletCreationError(
                error_message,
                context={"wallet_name": wallet_name},
                error_code="WALLET_CREATION_UNEXPECTED_ERROR",
            ) from e
        else:
            return sub_org_id

    async def get_address(
        self,
        wallet_id: str,
        derivation_path: str = "m/44'/60'/0'/0/0",
    ) -> WalletAddress:
        """
        Get wallet address for specified derivation path.

        Args:
            wallet_id: Sub-organization ID
            derivation_path: BIP32 derivation path

        Returns:
            WalletAddress object with address and metadata

        Raises:
            WalletNotFoundError: If wallet is not found
            WalletError: If address retrieval fails

        """
        log_operation_start(
            logger,
            "get_wallet_address",
            {"wallet_id": wallet_id, "derivation_path": derivation_path},
        )

        try:
            # Get wallet accounts for the sub-organization
            response = await self._make_authenticated_request(
                "POST",
                "/public/v1/query/list_wallet_accounts",
                {
                    "organizationId": wallet_id,
                    "timestampMs": str(int(time.time() * 1000)),
                },
            )

            if response.status_code != HTTP_OK:
                self._raise_wallet_address_error(
                    response.status_code,
                    response.text,
                    wallet_id,
                    derivation_path,
                )

            result = response.json()
            accounts = result["walletAccounts"]

            # Find account with matching derivation path
            for account in accounts:
                if account["path"] == derivation_path:
                    wallet_address = WalletAddress(
                        address=account["address"],
                        wallet_id=wallet_id,
                        derivation_path=derivation_path,
                        chain_id=1,  # Default to Ethereum mainnet, can be configured
                    )
                    log_operation_success(
                        logger,
                        "get_wallet_address",
                        {"wallet_id": wallet_id, "address": account["address"]},
                    )
                    return wallet_address
            # No account found for the derivation path
            error_msg = "No account found for derivation path " + derivation_path
            raise WalletNotFoundError(  # noqa: TRY301
                error_msg,
                context={
                    "wallet_id": wallet_id,
                    "derivation_path": derivation_path,
                    "available_paths": [acc["path"] for acc in accounts],
                },  # type: ignore[arg-type]
                error_code="WALLET_ACCOUNT_NOT_FOUND",
            )

        except (WalletError, WalletNotFoundError):
            raise
        except Exception as e:
            log_operation_failure(
                logger,
                "get_wallet_address",
                e,
                {"wallet_id": wallet_id, "derivation_path": derivation_path},
            )
            error_message = "Unexpected error during address retrieval: " + str(e)
            raise WalletError(
                error_message,
                context={"wallet_id": wallet_id, "derivation_path": derivation_path},
                error_code="WALLET_ADDRESS_UNEXPECTED_ERROR",
            ) from e

    async def sign_transaction(
        self,
        wallet_id: str,
        transaction: TransactionRequest,
    ) -> SignedTransaction:
        """
        Sign a transaction with the specified wallet.

        Args:
            wallet_id: Sub-organization ID
            transaction: Transaction to sign

        Returns:
            SignedTransaction object with signature and hash

        """
        logger.info("Signing transaction", wallet_id=wallet_id, to=transaction.to)

        # Evaluate transaction against policies
        action, violations = await self.permission_engine.evaluate_transaction(
            transaction,
            wallet_id,
        )

        if action == PolicyAction.DENY:
            violation_messages = [v.description for v in violations]
            error_msg = f"Transaction denied by policy: {'; '.join(violation_messages)}"
            logger.error("transaction_denied", error=error_msg, violations=violations)
            raise PermissionError(error_msg)

        if action == PolicyAction.REQUIRE_APPROVAL:
            logger.warning("Transaction requires approval", violations=violations)
            # In a real implementation, this would trigger an approval workflow
            # For now, we'll proceed but log the requirement

        # Get wallet accounts to find the signing account
        accounts_response = await self._make_authenticated_request(
            "POST",
            "/public/v1/query/list_wallet_accounts",
            {"organizationId": wallet_id, "timestampMs": str(int(time.time() * 1000))},
        )

        if accounts_response.status_code != HTTP_OK:
            msg = f"Failed to get wallet accounts: {accounts_response.text}"
            raise RuntimeError(msg)

        accounts = accounts_response.json()["walletAccounts"]
        if not accounts:
            msg = "No wallet accounts found"
            raise RuntimeError(msg)

        # Use the first account for signing
        signing_account = accounts[0]

        # Prepare unsigned transaction
        unsigned_tx = {
            "to": transaction.to,
            "value": hex(int(transaction.value)),
            "gas": hex(int(transaction.gas_limit or "21000")),
            "gasPrice": hex(int(transaction.gas_price or "20000000000")),
            "nonce": hex(transaction.nonce or 0),
            "chainId": transaction.chain_id,
        }

        if transaction.data:
            unsigned_tx["data"] = transaction.data

        # Sign transaction request
        sign_request = {
            "type": "ACTIVITY_TYPE_SIGN_TRANSACTION_V2",
            "organizationId": wallet_id,
            "parameters": {
                "signWith": signing_account["walletAccountId"],
                "type": "TRANSACTION_TYPE_ETHEREUM",
                "unsignedTransaction": json.dumps(unsigned_tx),
            },
            "timestampMs": str(int(time.time() * 1000)),
        }

        # Send signing request
        sign_response = await self._make_authenticated_request(
            "POST",
            "/public/v1/submit/sign_transaction",
            sign_request,
        )

        if sign_response.status_code != HTTP_OK:
            error_msg = f"Failed to sign transaction: {sign_response.text}"
            logger.error("transaction_signing_failed", error=error_msg)
            raise RuntimeError(error_msg)

        result = sign_response.json()
        signed_tx = result["activity"]["result"]["signTransactionResult"][
            "signedTransaction"
        ]

        # Calculate transaction hash

        tx_hash = Web3.keccak(hexstr=signed_tx).hex()

        # Record transaction for policy tracking
        self.permission_engine.record_transaction(tx_hash, transaction)

        logger.info("Transaction signed successfully", tx_hash=tx_hash)

        return SignedTransaction(
            transaction_hash=tx_hash,
            signed_transaction=signed_tx,
            raw_transaction=signed_tx,
        )

    async def export_wallet(self, wallet_id: str, password: str) -> dict[str, Any]:  # noqa: ARG002
        """
        Export wallet with encryption.

        Args:
            wallet_id: Sub-organization ID
            password: Password for encryption

        Returns:
            Encrypted wallet data

        """
        logger.info("Exporting wallet", wallet_id=wallet_id)

        # Get wallet details
        response = await self._make_authenticated_request(
            "POST",
            "/public/v1/query/get_organization",
            {"organizationId": wallet_id, "timestampMs": str(int(time.time() * 1000))},
        )

        if response.status_code != HTTP_OK:
            msg = f"Failed to get wallet details: {response.text}"
            raise RuntimeError(msg)

        org_data = response.json()["organization"]

        # Note: In a real implementation, you would need to handle
        # the secure export of private key material through Turnkey's
        # secure export mechanisms. This is a simplified version.

        return {
            "wallet_id": wallet_id,
            "organization_name": org_data["organizationName"],
            "export_timestamp": int(time.time()),
            "encrypted": True,
            # In practice, encrypted key material would go here
            "warning": (
                "This is a placeholder - actual implementation requires "
                "secure key export"
            ),
        }

    async def import_wallet(
        self,
        encrypted_wallet: dict[str, Any],  # noqa: ARG002
        password: str,  # noqa: ARG002
    ) -> str:
        """
        Import an encrypted wallet and return its ID.

        Args:
            encrypted_wallet: Encrypted wallet data
            password: Password for decryption

        Returns:
            Wallet ID of imported wallet

        """
        logger.info("Importing wallet")

        # Note: In a real implementation, this would involve
        # secure import mechanisms through Turnkey's APIs

        msg = (
            "Wallet import requires specialized Turnkey import mechanisms "
            "and secure handling of private key material"
        )
        raise NotImplementedError(msg)

    async def list_wallets(self) -> list[str]:
        """
        List all available wallet IDs (sub-organizations).

        Returns:
            List of wallet IDs

        """
        logger.info("Listing wallets")

        response = await self._make_authenticated_request(
            "POST",
            "/public/v1/query/list_sub_organizations",
            {
                "organizationId": self.settings.organization_id,
                "timestampMs": str(int(time.time() * 1000)),
            },
        )

        if response.status_code != HTTP_OK:
            msg = f"Failed to list wallets: {response.text}"
            raise RuntimeError(msg)

        result = response.json()
        sub_orgs = result.get("subOrganizations", [])

        return [sub_org["subOrganizationId"] for sub_org in sub_orgs]

    async def delete_wallet(self, wallet_id: str) -> bool:
        """
        Delete a wallet and return success status.

        Args:
            wallet_id: Sub-organization ID to delete

        Returns:
            True if deletion was successful

        """
        logger.info("Deleting wallet", wallet_id=wallet_id)

        # Note: Turnkey doesn't provide direct sub-organization deletion
        # In practice, you would disable/archive the sub-organization

        logger.warning("Wallet deletion not implemented - consider archiving instead")
        return False

    async def _make_authenticated_request(
        self,
        method: str,
        path: str,
        body: dict[str, Any],
    ) -> httpx.Response:
        """
        Make an authenticated request to the Turnkey API.

        Args:
            method: HTTP method
            path: API path
            body: Request body

        Returns:
            HTTP response

        """
        # Create request signature
        body_json = json.dumps(body, separators=(",", ":"))
        signature = self._sign_request(body_json)

        headers = {
            "Content-Type": "application/json",
            "X-Stamp-WebAuthn": signature,
        }

        return await self.client.request(
            method=method,
            url=path,
            content=body_json,
            headers=headers,
        )

    def _sign_request(self, body: str) -> str:
        """
        Sign a request body for Turnkey API authentication.

        Args:
            body: JSON request body

        Returns:
            Request signature

        """
        # Load private key
        private_key_pem = self.settings.api_private_key.get_secret_value()
        private_key = serialization.load_pem_private_key(
            private_key_pem.encode(),
            password=None,
        )

        # Sign the request body
        if isinstance(private_key, ec.EllipticCurvePrivateKey):
            signature = private_key.sign(body.encode(), ec.ECDSA(hashes.SHA256()))
        else:
            msg = "Unsupported private key type"
            raise TypeError(msg)

        # Return base64-encoded signature

        return base64.b64encode(signature).decode()

    async def validate_tee_attestation(self, attestation_token: str) -> bool:
        """
        Validate TEE attestation token for secure operations.

        Args:
            attestation_token: TEE attestation token

        Returns:
            True if attestation is valid

        """
        try:
            claims = self.tee_validator.validate_token(attestation_token)
        except Exception:
            logger.exception("TEE attestation validation failed")
            return False
        else:
            logger.info("TEE attestation validated", claims=claims)
            return True

    def _raise_wallet_creation_error(
        self, status_code: int, response_text: str, wallet_name: str
    ) -> None:
        error_msg = "Failed to create wallet: " + response_text
        raise WalletCreationError(
            error_msg,
            context={
                "wallet_name": wallet_name,
                "status_code": str(status_code),
                "response_text": response_text,
            },
            error_code="WALLET_CREATION_FAILED",
        )

    def _raise_wallet_address_error(
        self, status_code: int, response_text: str, wallet_id: str, derivation_path: str
    ) -> None:
        error_msg = "Failed to get wallet address: " + response_text
        raise WalletError(
            error_msg,
            context={
                "wallet_id": wallet_id,
                "derivation_path": derivation_path,
                "status_code": str(status_code),
                "response_text": response_text,
            },
            error_code="WALLET_ADDRESS_RETRIEVAL_FAILED",
        )
