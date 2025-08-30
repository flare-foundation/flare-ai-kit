"""ADK tool wrappers for Flare wallet operations."""

import structlog
from typing import Any

from flare_ai_kit.agent.tool import tool
from flare_ai_kit.wallet import PermissionEngine, TransactionPolicy, TurnkeyWallet
from flare_ai_kit.wallet.base import TransactionRequest
from flare_ai_kit.wallet.permissions import PolicyAction
from flare_ai_kit.wallet.turnkey_wallet import TurnkeySettings

logger = structlog.get_logger(__name__)


@tool
async def create_wallet(wallet_name: str) -> dict[str, str]:
    """
    Create a new non-custodial wallet using Turnkey.

    Args:
        wallet_name: Name for the new wallet

    Returns:
        Dictionary containing the wallet ID and creation status

    """
    logger.info("Creating new wallet", wallet_name=wallet_name)

    try:
        settings = TurnkeySettings()
        async with TurnkeyWallet(settings) as wallet:
            wallet_id = await wallet.create_wallet(wallet_name)

            return {
                "wallet_id": wallet_id,
                "wallet_name": wallet_name,
                "status": "success",
            }
    except Exception as e:
        logger.error("Failed to create wallet", error=str(e))
        return {
            "wallet_id": "",
            "wallet_name": wallet_name,
            "status": "error",
            "error": str(e),
        }


@tool
async def get_wallet_address(
    wallet_id: str, derivation_path: str = "m/44'/60'/0'/0/0"
) -> dict[str, Any]:
    """
    Get the address for a wallet at a specific derivation path.

    Args:
        wallet_id: The wallet ID (sub-organization ID)
        derivation_path: BIP32 derivation path (default: Ethereum first account)

    Returns:
        Dictionary containing the wallet address and metadata

    """
    logger.info(
        "Getting wallet address", wallet_id=wallet_id, derivation_path=derivation_path
    )

    try:
        settings = TurnkeySettings()
        async with TurnkeyWallet(settings) as wallet:
            wallet_address = await wallet.get_address(wallet_id, derivation_path)

            return {
                "address": wallet_address.address,
                "wallet_id": wallet_address.wallet_id,
                "derivation_path": wallet_address.derivation_path,
                "chain_id": wallet_address.chain_id,
                "status": "success",
            }
    except Exception as e:
        logger.error("Failed to get wallet address", error=str(e))
        return {
            "address": "",
            "wallet_id": wallet_id,
            "derivation_path": derivation_path,
            "chain_id": 0,
            "status": "error",
            "error": str(e),
        }


@tool
async def sign_transaction(
    wallet_id: str,
    to_address: str,
    value: str,
    chain_id: int = 1,
    gas_limit: str | None = None,
    gas_price: str | None = None,
    data: str | None = None,
    nonce: int | None = None,
) -> dict[str, str]:
    """
    Sign a transaction using the specified wallet.

    Args:
        wallet_id: The wallet ID to use for signing
        to_address: Recipient address
        value: Transaction value in wei
        chain_id: Blockchain chain ID (default: 1 for Ethereum mainnet)
        gas_limit: Gas limit for the transaction
        gas_price: Gas price in wei
        data: Transaction data for contract calls (optional)
        nonce: Transaction nonce (optional)

    Returns:
        Dictionary containing the signed transaction hash and raw transaction

    """
    logger.info(
        "Signing transaction", wallet_id=wallet_id, to_address=to_address, value=value
    )

    try:
        settings = TurnkeySettings()
        async with TurnkeyWallet(settings) as wallet:
            transaction = TransactionRequest(
                to=to_address,
                value=value,
                chain_id=chain_id,
                gas_limit=gas_limit,
                gas_price=gas_price,
                data=data,
                nonce=nonce,
            )

            signed_tx = await wallet.sign_transaction(wallet_id, transaction)

            return {
                "transaction_hash": signed_tx.transaction_hash,
                "signed_transaction": signed_tx.signed_transaction,
                "raw_transaction": signed_tx.raw_transaction,
                "status": "success",
            }
    except Exception as e:
        logger.error("Failed to sign transaction", error=str(e))
        return {
            "transaction_hash": "",
            "signed_transaction": "",
            "raw_transaction": "",
            "status": "error",
            "error": str(e),
        }


@tool
async def list_wallets() -> dict[str, Any]:
    """
    List all available wallets for the organization.

    Returns:
        Dictionary containing list of wallet IDs

    """
    logger.info("Listing wallets")

    try:
        settings = TurnkeySettings()
        async with TurnkeyWallet(settings) as wallet:
            wallet_ids = await wallet.list_wallets()

            return {
                "wallet_ids": wallet_ids,
                "count": len(wallet_ids),
                "status": "success",
            }
    except Exception as e:
        logger.error("Failed to list wallets", error=str(e))
        return {"wallet_ids": [], "count": 0, "status": "error", "error": str(e)}


@tool
async def validate_tee_attestation(
    wallet_id: str, attestation_token: str
) -> dict[str, bool | str]:
    """
    Validate a TEE attestation token for secure wallet operations.

    Args:
        wallet_id: The wallet ID for which to validate attestation
        attestation_token: The TEE attestation token to validate

    Returns:
        Dictionary containing validation result

    """
    logger.info("Validating TEE attestation", wallet_id=wallet_id)

    try:
        settings = TurnkeySettings()
        async with TurnkeyWallet(settings) as wallet:
            is_valid = await wallet.validate_tee_attestation(attestation_token)

            return {"wallet_id": wallet_id, "valid": is_valid, "status": "success"}
    except Exception as e:
        logger.error("Failed to validate TEE attestation", error=str(e))
        return {
            "wallet_id": wallet_id,
            "valid": False,
            "status": "error",
            "error": str(e),
        }


@tool
async def create_transaction_policy(
    policy_name: str,
    description: str,
    max_transaction_value: float | None = None,
    daily_spending_limit: float | None = None,
    allowed_destinations: list[str] | None = None,
    blocked_destinations: list[str] | None = None,
    allowed_hours_utc: list[int] | None = None,
    max_gas_price: str | None = None,
) -> dict[str, Any]:
    """
    Create a transaction policy for wallet permission management.

    Args:
        policy_name: Name of the policy
        description: Description of what the policy does
        max_transaction_value: Maximum value per transaction in ETH
        daily_spending_limit: Daily spending limit in ETH
        allowed_destinations: List of allowed destination addresses
        blocked_destinations: List of blocked destination addresses
        allowed_hours_utc: List of allowed hours (0-23 UTC)
        max_gas_price: Maximum gas price in wei

    Returns:
        Dictionary containing policy creation status

    """
    logger.info("Creating transaction policy", policy_name=policy_name)

    try:
        from decimal import Decimal

        policy = TransactionPolicy(
            name=policy_name,
            description=description,
            max_transaction_value=Decimal(str(max_transaction_value))
            if max_transaction_value
            else None,
            daily_spending_limit=Decimal(str(daily_spending_limit))
            if daily_spending_limit
            else None,
            allowed_destinations=allowed_destinations or [],
            allowed_contracts=None,
            blocked_destinations=blocked_destinations or [],
            allowed_hours_utc=allowed_hours_utc or [],
            max_gas_price=max_gas_price,
            max_gas_limit=None,
        )

        # In a real implementation, you would persist this policy
        # For now, we'll just validate it was created correctly

        return {
            "policy_name": policy.name,
            "description": policy.description,
            "enabled": policy.enabled,
            "status": "success",
        }
    except Exception as e:
        logger.error("Failed to create transaction policy", error=str(e))
        return {
            "policy_name": policy_name,
            "description": description,
            "enabled": False,
            "status": "error",
            "error": str(e),
        }


@tool
async def evaluate_transaction_permissions(
    to_address: str,
    value: str,
    chain_id: int = 1,
    gas_price: str | None = None,
    policy_names: list[str] | None = None,
) -> dict[str, Any]:
    """
    Evaluate if a transaction would be allowed under current policies.

    Args:
        to_address: Recipient address
        value: Transaction value in wei
        chain_id: Blockchain chain ID
        gas_price: Gas price in wei
        policy_names: List of policy names to evaluate (optional)

    Returns:
        Dictionary containing evaluation results and any policy violations

    """
    logger.info(
        "Evaluating transaction permissions", to_address=to_address, value=value
    )

    try:
        permission_engine = PermissionEngine()

        # Create a sample policy for demonstration
        if not policy_names:
            from decimal import Decimal

            sample_policy = TransactionPolicy(
                name="default_policy",
                description="Default security policy",
                max_transaction_value=Decimal("10.0"),  # 10 ETH max
                daily_spending_limit=Decimal("50.0"),  # 50 ETH daily
                allowed_destinations=[],
                allowed_contracts=None,
                blocked_destinations=[],
                allowed_hours_utc=[],
                max_gas_price=None,
                max_gas_limit=None,
            )
            permission_engine.add_policy(sample_policy)

        transaction = TransactionRequest(
            to=to_address, value=value, chain_id=chain_id, gas_price=gas_price
        )

        action, violations = await permission_engine.evaluate_transaction(
            transaction, "test_wallet"
        )

        return {
            "action": action.value,
            "allowed": action == PolicyAction.ALLOW,
            "requires_approval": action == PolicyAction.REQUIRE_APPROVAL,
            "denied": action == PolicyAction.DENY,
            "violations": [v.description for v in violations],
            "violation_count": len(violations),
            "status": "success",
        }
    except Exception as e:
        logger.error("Failed to evaluate transaction permissions", error=str(e))
        return {
            "action": "error",
            "allowed": False,
            "requires_approval": False,
            "denied": True,
            "violations": [],
            "violation_count": 0,
            "status": "error",
            "error": str(e),
        }
