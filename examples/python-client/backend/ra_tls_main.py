# ra_tls_main.py

import asyncio
import json
import pathlib
import re
import socket
import traceback
from concurrent.futures import ThreadPoolExecutor
from typing import Any

import h11
import structlog
from flare_ai_kit.ecosystem.applications.cyclo import Cyclo
from flare_ai_kit.ecosystem.applications.flare_portal import FlarePortal
from flare_ai_kit.ecosystem.applications.kinetic import Kinetic
from flare_ai_kit.ecosystem.applications.openocean import OpenOcean
from flare_ai_kit.ecosystem.applications.sceptre import Sceptre
from flare_ai_kit.ecosystem.applications.sparkdex import SparkDEX
from flare_ai_kit.ecosystem.applications.stargate import Stargate
from flare_ai_kit.ecosystem.explorer import BlockExplorer
from flare_ai_kit.ecosystem.flare import Flare
from flare_ai_kit.ecosystem.settings import (
    ChainIdConfig,
    Contracts,
    EcosystemSettings,
)
from flare_ai_kit.tee.attestation import VtpmAttestation
from tlslite.api import (
    X509,
    HandshakeSettings,
    TLSConnection,
    X509CertChain,
    parsePEMKey,
)
from tlslite.extensions import (
    SupportedGroupsExtension,
)

from generate_certs import generate_certificate
from settings import settings

###########################################################################
# Constants
###########################################################################

EVM_ADDRESS_PATTERN = re.compile(r"^0x[a-fA-F0-9]{40}$", re.IGNORECASE)

BASE_DIR = pathlib.Path(__file__).parent
SERVER_CERT_NAME = "serverCert.pem"
SERVER_KEY_NAME = "serverKey.pem"
CERT_PATH = BASE_DIR / SERVER_CERT_NAME
KEY_PATH = BASE_DIR / SERVER_KEY_NAME
SIM_TOKEN_PATH = BASE_DIR / "sim_token.txt"

###########################################################################
# Init global variables and objects
###########################################################################

logger = structlog.get_logger(__name__)

# Thread pool for synchronous TLS operations
executor = ThreadPoolExecutor(max_workers=10)

attestation = VtpmAttestation(simulate=settings.simulate_attestation)
attestation_token = bytes(attestation.get_token([]), encoding="utf-8")

# Check if certificates exist and create if not

if not CERT_PATH.exists() or not KEY_PATH.exists():
    generate_certificate(
        ip_address="0.0.0.0",
        output_dir=BASE_DIR,
        cert_name=SERVER_CERT_NAME,
        key_name=SERVER_KEY_NAME,
    )

# Load certificate and private key from files
cert = X509()
with open(CERT_PATH, "rb") as f:
    decoded = f.read().decode()
    cert.parse(decoded)


cert_chain = X509CertChain([cert])
with open(KEY_PATH, "rb") as f:
    key_bytes = f.read()
    decoded = key_bytes.decode()
    private_key = parsePEMKey(decoded, private=True)


# Configure handshake settings for TLS 1.3
tls_settings = HandshakeSettings()
tls_settings.minVersion = (3, 4)  # TLS 1.3
tls_settings.maxVersion = (3, 4)  # TLS 1.3
supported_groups = SupportedGroupsExtension()
supported_groups.create([23, 24])  # secp256r1 (23), secp384r1 (24)
tls_settings.extensions = [supported_groups]

# Create ecosystem settings, chains, contracts, explorer, and provider
ecosystem_settings = EcosystemSettings()
chains = ChainIdConfig()
contracts = Contracts()
flare_explorer = BlockExplorer(ecosystem_settings)
flare_provider = Flare(ecosystem_settings)

###########################################################################
# Handler functions for API routes
###########################################################################


# We use the Any type because the http header contains attributes with several different types.
async def handle_bridge(request: dict[str, Any]) -> dict[str, Any]:
    """
    Handle a bridge request.

    Args:
        request: A dictionary containing the request data, including a 'body' key with bytes.

    Request JSON args:
        chain_id: This is the endpoint ID from here: https://docs.stargate.finance/resources/contracts/mainnet-contracts
        amount_wei: This is the amount of WETH to bridge, in wei

    """
    try:
        valid, result = check_valid_json(request)
        if not valid:
            return result

        # Extract amount and chain
        amount_wei = result.get("amount_wei")
        chain_id = result.get("chain_id")
        if not isinstance(amount_wei, int) or amount_wei <= 0:
            return build_response(
                400,
                json.dumps(
                    {"error": "Invalid or missing 'amount' (must be a positive number)"}
                ).encode(),
            )
        if not isinstance(chain_id, int) or not chain_id:
            return build_response(
                400,
                json.dumps(
                    {"error": "Invalid or missing 'chain' (must be a non-empty string)"}
                ).encode(),
            )

        # Initialize Stargate
        stargate = await Stargate.create(
            settings=ecosystem_settings,
            contracts=contracts,
            chains=chains,
            flare_explorer=flare_explorer,
            flare_provider=flare_provider,
        )

        # Call bridge_weth_to_chain
        try:
            tx_hash = await stargate.bridge_weth_to_chain(amount_wei, chain_id)
            return build_response(
                201, json.dumps({"success": True, "tx_hash": tx_hash}).encode()
            )
        except Exception as e:
            logger.error(f"Transaction failed: {e}\n{''.join(traceback.format_exc())}")
            return build_response(
                500, json.dumps({"error": f"Transaction failed: {e!s}"}).encode()
            )

    except Exception as e:
        # Catch any unexpected errors
        logger.error(f"Server error: {e}\n{''.join(traceback.format_exc())}")
        return build_response(
            500, json.dumps({"error": "Unexpected server error"}).encode()
        )


async def handle_swap(request: dict[str, Any]) -> dict[str, Any]:
    try:
        valid, result = check_valid_json(request)
        if not valid:
            return result

        # Extract parameters
        token_in_addr = result.get("token_in_addr")
        token_out_addr = result.get("token_out_addr")
        amount_in_WEI = result.get("amount_in_WEI")
        amount_out_min_WEI = result.get("amount_out_min_WEI")
        if (
            not isinstance(token_in_addr, str)
            or not token_in_addr
            or not EVM_ADDRESS_PATTERN.match(token_in_addr)
        ):
            return build_response(
                400,
                json.dumps(
                    {
                        "error": "Invalid or missing 'token_in_addr' (must be a valid EVM address, e.g., 0x1234567890abcdef1234567890abcdef12345678)"
                    }
                ).encode(),
            )
        if (
            not isinstance(token_out_addr, str)
            or not token_out_addr
            or not EVM_ADDRESS_PATTERN.match(token_out_addr)
        ):
            return build_response(
                400,
                json.dumps(
                    {
                        "error": "Invalid or missing 'token_out_addr' (must be a valid EVM address, e.g., 0x1234567890abcdef1234567890abcdef12345678)"
                    }
                ).encode(),
            )
        if not isinstance(amount_in_WEI, int) or amount_in_WEI <= 0:
            return build_response(
                400,
                json.dumps(
                    {
                        "error": "Invalid or missing 'amount_in_WEI' (must be a positive number)"
                    }
                ).encode(),
            )
        if not isinstance(amount_out_min_WEI, int) or amount_out_min_WEI < 0:
            return build_response(
                400,
                json.dumps(
                    {
                        "error": "Invalid or missing 'amount_out_min_WEI' (must be a positive number)"
                    }
                ).encode(),
            )

        # Initialize
        sparkdex = await SparkDEX.create(
            settings=ecosystem_settings,
            contracts=contracts,
            flare_explorer=flare_explorer,
            flare_provider=flare_provider,
        )

        # Call function
        try:
            tx_hash = await sparkdex.swap_erc20_tokens(
                token_in_addr=token_in_addr,
                token_out_addr=token_out_addr,
                amount_in_WEI=amount_in_WEI,
                amount_out_min_WEI=amount_out_min_WEI,
            )
            return build_response(
                201, json.dumps({"success": True, "tx_hash": tx_hash}).encode()
            )
        except Exception as e:
            logger.error(f"Transaction failed: {e}\n{''.join(traceback.format_exc())}")
            return build_response(
                500, json.dumps({"error": f"Transaction failed: {e!s}"}).encode()
            )

    except Exception as e:
        # Catch any unexpected errors
        logger.error(f"Server error: {e}\n{''.join(traceback.format_exc())}")
        return build_response(
            500, json.dumps({"error": "Unexpected server error"}).encode()
        )


async def handle_wrap(request: dict[str, Any]) -> dict[str, Any]:
    try:
        valid, result = check_valid_json(request)
        if not valid:
            return result

        # Extract parameters
        amount_WEI = result.get("amount_WEI")
        if not isinstance(amount_WEI, int) or amount_WEI < 0:
            return build_response(
                400,
                json.dumps(
                    {
                        "error": "Invalid or missing 'amount_WEI' (must be a positive number)"
                    }
                ).encode(),
            )

        # Initialize
        flare_portal = await FlarePortal.create(
            settings=ecosystem_settings,
            contracts=contracts,
            flare_explorer=flare_explorer,
            flare_provider=flare_provider,
        )

        # Call function
        try:
            tx_hash = await flare_portal.wrap_flr_to_wflr(amount_WEI)
            return build_response(
                201, json.dumps({"success": True, "tx_hash": tx_hash}).encode()
            )
        except Exception as e:
            logger.error(f"Transaction failed: {e}\n{''.join(traceback.format_exc())}")
            return build_response(
                500, json.dumps({"error": f"Transaction failed: {e!s}"}).encode()
            )

    except Exception as e:
        # Catch any unexpected errors
        logger.error(f"Server error: {e}\n{''.join(traceback.format_exc())}")
        return build_response(
            500, json.dumps({"error": "Unexpected server error"}).encode()
        )


async def handle_unwrap(request: dict[str, Any]) -> dict[str, Any]:
    try:
        valid, result = check_valid_json(request)
        if not valid:
            return result

        # Extract parameters
        amount_WEI = result.get("amount_WEI")
        if not isinstance(amount_WEI, int) or amount_WEI <= 0:
            return build_response(
                400,
                json.dumps(
                    {
                        "error": "Invalid or missing 'amount_WEI' (must be a positive number)"
                    }
                ).encode(),
            )

        # Initialize
        flare_portal = await FlarePortal.create(
            settings=ecosystem_settings,
            contracts=contracts,
            flare_explorer=flare_explorer,
            flare_provider=flare_provider,
        )

        # Call function
        try:
            tx_hash = await flare_portal.unwrap_wflr_to_flr(amount_WEI)
            return build_response(
                201, json.dumps({"success": True, "tx_hash": tx_hash}).encode()
            )
        except Exception as e:
            logger.error(f"Transaction failed: {e}\n{''.join(traceback.format_exc())}")
            return build_response(
                500, json.dumps({"error": f"Transaction failed: {e!s}"}).encode()
            )

    except Exception as e:
        # Catch any unexpected errors
        logger.error(f"Server error: {e}\n{''.join(traceback.format_exc())}")
        return build_response(
            500, json.dumps({"error": "Unexpected server error"}).encode()
        )


async def handle_stake(request: dict[str, Any]) -> dict[str, Any]:
    try:
        valid, result = check_valid_json(request)
        if not valid:
            return result

        # Extract parameters
        amount_WEI = result.get("amount_WEI")
        if not isinstance(amount_WEI, int) or amount_WEI <= 0:
            return build_response(
                400,
                json.dumps(
                    {
                        "error": "Invalid or missing 'amount_WEI' (must be a positive number)"
                    }
                ).encode(),
            )

        # Initialize
        sceptre = await Sceptre.create(
            settings=ecosystem_settings,
            contracts=contracts,
            flare_explorer=flare_explorer,
            flare_provider=flare_provider,
        )

        # Call function
        try:
            tx_hash = await sceptre.stake(amount_WEI)
            return build_response(
                201, json.dumps({"success": True, "tx_hash": tx_hash}).encode()
            )
        except Exception as e:
            logger.error(f"Transaction failed: {e}\n{''.join(traceback.format_exc())}")
            return build_response(
                500, json.dumps({"error": f"Transaction failed: {e!s}"}).encode()
            )

    except Exception as e:
        # Catch any unexpected errors
        logger.error(f"Server error: {e}\n{''.join(traceback.format_exc())}")
        return build_response(
            500, json.dumps({"error": "Unexpected server error"}).encode()
        )


async def handle_unstake(request: dict[str, Any]) -> dict[str, Any]:
    try:
        valid, result = check_valid_json(request)
        if not valid:
            return result

        # Extract parameters
        amount_WEI = result.get("amount_WEI")
        if not isinstance(amount_WEI, int) or amount_WEI <= 0:
            return build_response(
                400,
                json.dumps(
                    {
                        "error": "Invalid or missing 'amount_WEI' (must be a positive number)"
                    }
                ).encode(),
            )

        # Initialize
        sceptre = await Sceptre.create(
            settings=ecosystem_settings,
            contracts=contracts,
            flare_explorer=flare_explorer,
            flare_provider=flare_provider,
        )

        # Call function
        try:
            tx_hash = await sceptre.unstake(amount_WEI)
            return build_response(
                201, json.dumps({"success": True, "tx_hash": tx_hash}).encode()
            )
        except Exception as e:
            logger.error(f"Transaction failed: {e}\n{''.join(traceback.format_exc())}")
            return build_response(
                500, json.dumps({"error": f"Transaction failed: {e!s}"}).encode()
            )

    except Exception as e:
        # Catch any unexpected errors
        logger.error(f"Server error: {e}\n{''.join(traceback.format_exc())}")
        return build_response(
            500, json.dumps({"error": "Unexpected server error"}).encode()
        )


async def handle_kinetic_supply(request: dict[str, Any]) -> dict[str, Any]:
    try:
        valid, result = check_valid_json(request)
        if not valid:
            return result

        # Extract parameters
        token_symbol = result.get("token_symbol")
        amount_WEI = result.get("amount_WEI")
        if not isinstance(token_symbol, str) or not token_symbol:
            return build_response(
                400, json.dumps({"error": "Invalid or missing 'token_symbol'"}).encode()
            )
        if not isinstance(amount_WEI, int) or amount_WEI <= 0:
            return build_response(
                400,
                json.dumps(
                    {
                        "error": "Invalid or missing 'amount_WEI' (must be a positive number)"
                    }
                ).encode(),
            )

        # Initialize
        kinetic = await Kinetic.create(
            settings=ecosystem_settings,
            contracts=contracts,
            flare_explorer=flare_explorer,
            flare_provider=flare_provider,
        )

        # Call function
        try:
            tx_hash = await kinetic.supply(token=token_symbol, amount_WEI=amount_WEI)
            return build_response(
                201, json.dumps({"success": True, "tx_hash": tx_hash}).encode()
            )
        except Exception as e:
            logger.error(f"Transaction failed: {e}\n{''.join(traceback.format_exc())}")
            return build_response(
                500, json.dumps({"error": f"Transaction failed: {e!s}"}).encode()
            )

    except Exception as e:
        # Catch any unexpected errors
        logger.error(f"Server error: {e}\n{''.join(traceback.format_exc())}")
        return build_response(
            500, json.dumps({"error": "Unexpected server error"}).encode()
        )


async def handle_kinetic_withdraw(request: dict[str, Any]) -> dict[str, Any]:
    try:
        valid, result = check_valid_json(request)
        if not valid:
            return result

        # Extract parameters
        token_symbol = result.get("token_symbol")
        amount_WEI = result.get("amount_WEI")
        if not isinstance(token_symbol, str) or not token_symbol:
            return build_response(
                400, json.dumps({"error": "Invalid or missing 'token_symbol'"}).encode()
            )
        if not isinstance(amount_WEI, int) or amount_WEI <= 0:
            return build_response(
                400,
                json.dumps(
                    {
                        "error": "Invalid or missing 'amount_WEI' (must be a positive number)"
                    }
                ).encode(),
            )

        # Initialize
        kinetic = await Kinetic.create(
            settings=ecosystem_settings,
            contracts=contracts,
            flare_explorer=flare_explorer,
            flare_provider=flare_provider,
        )

        # Call function
        try:
            tx_hash = await kinetic.withdraw(token=token_symbol, amount_WEI=amount_WEI)
            return build_response(
                201, json.dumps({"success": True, "tx_hash": tx_hash}).encode()
            )
        except Exception as e:
            logger.error(f"Transaction failed: {e}\n{''.join(traceback.format_exc())}")
            return build_response(
                500, json.dumps({"error": f"Transaction failed: {e!s}"}).encode()
            )

    except Exception as e:
        # Catch any unexpected errors
        logger.error(f"Server error: {e}\n{''.join(traceback.format_exc())}")
        return build_response(
            500, json.dumps({"error": "Unexpected server error"}).encode()
        )


async def handle_kinetic_enable_collateral(request: dict[str, Any]) -> dict[str, Any]:
    try:
        valid, result = check_valid_json(request)
        if not valid:
            return result

        # Extract parameters
        token_symbol = result.get("token_symbol")
        if not isinstance(token_symbol, str) or not token_symbol:
            return build_response(
                400, json.dumps({"error": "Invalid or missing 'token_symbol'"}).encode()
            )
        # Initialize
        kinetic = await Kinetic.create(
            settings=ecosystem_settings,
            contracts=contracts,
            flare_explorer=flare_explorer,
            flare_provider=flare_provider,
        )

        # Call function
        try:
            tx_hash = await kinetic.enable_collateral(token=token_symbol)
            return build_response(
                201, json.dumps({"success": True, "tx_hash": tx_hash}).encode()
            )
        except Exception as e:
            logger.error(f"Transaction failed: {e}\n{''.join(traceback.format_exc())}")
            return build_response(
                500, json.dumps({"error": f"Transaction failed: {e!s}"}).encode()
            )

    except Exception as e:
        # Catch any unexpected errors
        logger.error(f"Server error: {e}\n{''.join(traceback.format_exc())}")
        return build_response(
            500, json.dumps({"error": "Unexpected server error"}).encode()
        )


async def handle_kinetic_disable_collateral(request: dict[str, Any]) -> dict[str, Any]:
    try:
        valid, result = check_valid_json(request)
        if not valid:
            return result

        # Extract parameters
        token_symbol = result.get("token_symbol")
        if not isinstance(token_symbol, str) or not token_symbol:
            return build_response(
                400, json.dumps({"error": "Invalid or missing 'token_symbol'"}).encode()
            )
        # Initialize
        kinetic = await Kinetic.create(
            settings=ecosystem_settings,
            contracts=contracts,
            flare_explorer=flare_explorer,
            flare_provider=flare_provider,
        )

        # Call function
        try:
            tx_hash = await kinetic.disable_collateral(token=token_symbol)
            return build_response(
                201, json.dumps({"success": True, "tx_hash": tx_hash}).encode()
            )
        except Exception as e:
            logger.error(f"Transaction failed: {e}\n{''.join(traceback.format_exc())}")
            return build_response(
                500, json.dumps({"error": f"Transaction failed: {e!s}"}).encode()
            )

    except Exception as e:
        # Catch any unexpected errors
        logger.error(f"Server error: {e}\n{''.join(traceback.format_exc())}")
        return build_response(
            500, json.dumps({"error": "Unexpected server error"}).encode()
        )


async def handle_cyclo_lock(request: dict[str, Any]) -> dict[str, Any]:
    try:
        valid, result = check_valid_json(request)
        if not valid:
            return result

        # Extract parameters
        token_symbol = result.get("token_symbol")
        amount_WEI = result.get("amount_WEI")
        if not isinstance(token_symbol, str) or not token_symbol:
            return build_response(
                400, json.dumps({"error": "Invalid or missing 'token_symbol'"}).encode()
            )
        if not isinstance(amount_WEI, int) or amount_WEI <= 0:
            return build_response(
                400,
                json.dumps(
                    {
                        "error": "Invalid or missing 'amount_WEI' (must be a positive number)"
                    }
                ).encode(),
            )

        # Initialize
        cyclo = await Cyclo.create(
            settings=ecosystem_settings,
            contracts=contracts,
            flare_explorer=flare_explorer,
            flare_provider=flare_provider,
        )

        # Call function
        try:
            tx_hash, deposit_id = await cyclo.lock(
                token=token_symbol, amount_WEI=amount_WEI
            )
            return build_response(
                201,
                json.dumps(
                    {"success": True, "tx_hash": tx_hash, "deposit_id": deposit_id}
                ).encode(),
            )
        except Exception as e:
            logger.error(f"Transaction failed: {e}\n{''.join(traceback.format_exc())}")
            return build_response(
                500, json.dumps({"error": f"Transaction failed: {e!s}"}).encode()
            )

    except Exception as e:
        # Catch any unexpected errors
        logger.error(f"Server error: {e}\n{''.join(traceback.format_exc())}")
        return build_response(
            500, json.dumps({"error": "Unexpected server error"}).encode()
        )


async def handle_cyclo_unlock(request: dict[str, Any]) -> dict[str, Any]:
    try:
        valid, result = check_valid_json(request)
        if not valid:
            return result

        # Extract parameters
        token_symbol = result.get("token_symbol")
        deposit_id = result.get("deposit_id")
        unlock_proportion = result.get("unlock_proportion")
        if not isinstance(token_symbol, str) or not token_symbol:
            return build_response(
                400, json.dumps({"error": "Invalid or missing 'token_symbol'"}).encode()
            )
        if not isinstance(deposit_id, int):
            return build_response(
                400, json.dumps({"error": "Invalid or missing 'deposit_id'"}).encode()
            )
        if (
            not isinstance(unlock_proportion, float)
            or unlock_proportion <= 0.0
            or unlock_proportion > 1.0
        ):
            return build_response(
                400,
                json.dumps(
                    {
                        "error": "Invalid or missing 'unlock_proportion' (must be a positive number between 0 and 1)"
                    }
                ).encode(),
            )

        # Initialize
        cyclo = await Cyclo.create(
            settings=ecosystem_settings,
            contracts=contracts,
            flare_explorer=flare_explorer,
            flare_provider=flare_provider,
        )

        # Call function
        try:
            tx_hash = await cyclo.unlock(
                token=token_symbol,
                deposit_id=deposit_id,
                unlock_proportion=unlock_proportion,
            )
            return build_response(
                201, json.dumps({"success": True, "tx_hash": tx_hash}).encode()
            )
        except Exception as e:
            logger.error(f"Transaction failed: {e}\n{''.join(traceback.format_exc())}")
            return build_response(
                500, json.dumps({"error": f"Transaction failed: {e!s}"}).encode()
            )

    except Exception as e:
        # Catch any unexpected errors
        logger.error(f"Server error: {e}\n{''.join(traceback.format_exc())}")
        return build_response(
            500, json.dumps({"error": "Unexpected server error"}).encode()
        )


async def handle_openocean_swap(request: dict[str, Any]) -> dict[str, Any]:
    try:
        valid, result = check_valid_json(request)
        if not valid:
            return result

        # Extract parameters
        # token_in_str: str, token_out_str: str, amount: float, speed: str
        token_in_str = result.get("token_in_str")
        token_out_str = result.get("token_out_str")
        amount = result.get("amount")
        speed = result.get("speed")
        if not isinstance(token_in_str, str) or not token_in_str:
            return build_response(
                400, json.dumps({"error": "Invalid or missing 'token_in_str'"}).encode()
            )
        if not isinstance(token_out_str, str) or not token_out_str:
            return build_response(
                400,
                json.dumps({"error": "Invalid or missing 'token_out_str'"}).encode(),
            )
        if not isinstance(amount, int) or amount <= 0:
            return build_response(
                400,
                json.dumps(
                    {"error": "Invalid or missing 'amount' (must be a positive number)"}
                ).encode(),
            )
        if not isinstance(speed, str):
            return build_response(
                400,
                json.dumps(
                    {
                        "error": "Invalid or missing 'speed' (should be 'low', 'medium', or 'high')"
                    }
                ).encode(),
            )

        # Initialize
        openocean = await OpenOcean.create(
            settings=ecosystem_settings,
            contracts=contracts,
            flare_explorer=flare_explorer,
            provider=flare_provider,
        )

        # Call function
        try:
            tx_hash = await openocean.swap(
                token_in_str=token_in_str,
                token_out_str=token_out_str,
                amount=amount,
                speed=speed,
            )
            return build_response(
                201, json.dumps({"success": True, "tx_hash": tx_hash}).encode()
            )
        except Exception as e:
            logger.error(f"Transaction failed: {e}\n{''.join(traceback.format_exc())}")
            return build_response(
                500, json.dumps({"error": f"Transaction failed: {e!s}"}).encode()
            )

    except Exception as e:
        # Catch any unexpected errors
        logger.error(f"Server error: {e}\n{''.join(traceback.format_exc())}")
        return build_response(
            500, json.dumps({"error": "Unexpected server error"}).encode()
        )


###########################################################################
# Helper functions for handler functions
###########################################################################


def build_response(status: int, body: bytes) -> dict[str, Any]:
    return {
        "status": status,
        "headers": [(b"Content-Type", b"application/json"), (b"Connection", b"close")],
        "body": body,
    }


def check_valid_json(
    request: dict[str, Any],
) -> tuple[bool, dict[str, Any]]:
    """
    Validates and parses the JSON body of a request.

    Args:
        request: A dictionary containing the request data, including a 'body' key with bytes.

    Returns:
        A tuple of (is_valid, result):
        - is_valid: True if the body is valid JSON, False otherwise.
        - result: If valid, the parsed JSON as Dict[str, Any]. If invalid, a response dict with error details.
    """
    body = request.get("body", b"")
    if not body:
        return False, build_response(
            400, json.dumps({"error": "Empty request body"}).encode()
        )
    try:
        parsed_json = json.loads(body.decode("utf-8"))
        return True, parsed_json
    except json.JSONDecodeError:
        return False, build_response(
            400, json.dumps({"error": "Invalid JSON in request body"}).encode()
        )


###########################################################################
# Defining the API routes and map to handler functions
###########################################################################

routes = {
    ("POST", "/bridge"): handle_bridge,
    ("POST", "/swap"): handle_swap,
    ("POST", "/wrap"): handle_wrap,
    ("POST", "/unwrap"): handle_unwrap,
    ("POST", "/stake"): handle_stake,
    ("POST", "/unstake"): handle_unstake,
    ("POST", "/kinetic_supply"): handle_kinetic_supply,
    ("POST", "/kinetic_withdraw"): handle_kinetic_withdraw,
    ("POST", "/kinetic_enable_collateral"): handle_kinetic_enable_collateral,
    ("POST", "/kinetic_disable_collateral"): handle_kinetic_disable_collateral,
    ("POST", "/cyclo_lock"): handle_cyclo_lock,
    ("POST", "/cyclo_unlock"): handle_cyclo_unlock,
    ("POST", "/openocean_swap"): handle_openocean_swap,
}


###########################################################################
# Function to handle incoming connections
###########################################################################


async def handle_connection(client_sock: socket.socket, addr: str) -> None:
    logger.debug(f"Accepted connection from {addr}")
    tls_conn = TLSConnection(client_sock)

    try:
        # Perform TLS handshake in a thread
        def do_handshake():
            tls_conn.handshakeServer(
                None,
                cert_chain,
                private_key,
                settings=tls_settings,
                attestation_token=attestation_token,
            )

        await asyncio.get_event_loop().run_in_executor(executor, do_handshake)
        logger.info("TLS handshake complete! ({addr})")

        # HTTP/1.1 connection state
        h11_conn = h11.Connection(our_role=h11.SERVER)

        # Process one request per connection
        try:
            # Read request data
            data = await asyncio.get_event_loop().run_in_executor(
                executor, lambda: tls_conn.recv(4096)
            )
            if not data:
                return  # Client closed connection

            h11_conn.receive_data(data)
            request_received = False
            method = None
            path = None
            headers = None
            body = b""

            # Parse request
            while True:
                event = h11_conn.next_event()
                if event is h11.NEED_DATA:
                    # Fetch more data if needed
                    more_data = await asyncio.get_event_loop().run_in_executor(
                        executor, lambda: tls_conn.recv(4096)
                    )
                    if not more_data:
                        break
                    h11_conn.receive_data(more_data)
                    continue
                if isinstance(event, h11.Request):
                    method = event.method.decode()
                    path = event.target.decode()
                    headers = dict(event.headers)
                    request_received = True
                elif isinstance(event, h11.Data):
                    body += event.data
                elif isinstance(event, h11.EndOfMessage):
                    break
                elif isinstance(event, h11.ConnectionClosed):
                    return

            if not request_received:
                return  # No valid request received

            # Route request
            handler = routes.get((method, path))
            if handler:
                request = {
                    "method": method,
                    "path": path,
                    "headers": headers,
                    "body": body,
                }
                response = (
                    await handler(request)
                    if asyncio.iscoroutinefunction(handler)
                    else handler(request)
                )
            else:
                response = {
                    "status": 404,
                    "headers": [
                        (b"Content-Type", b"text/plain"),
                        (b"Connection", b"close"),
                    ],
                    "body": b"Not Found",
                }

            # Ensure Content-Length is set
            content_length = (
                len(response["body"])
                if isinstance(response["body"], (bytes, list))
                else 0
            )
            # content_length = len(response["body"])
            response["headers"] = [
                h for h in response["headers"] if h[0].lower() != b"content-length"
            ] + [(b"Content-Length", str(content_length).encode())]

            # Debug response
            logger.debug(
                f"Sending response: status={response['status']}, headers={response['headers']}, body={response['body']}"
            )

            # Send response
            resp_event = h11.Response(
                status_code=response["status"], headers=response["headers"]
            )
            await asyncio.get_event_loop().run_in_executor(
                executor, lambda: tls_conn.sendall(h11_conn.send(resp_event))
            )
            await asyncio.get_event_loop().run_in_executor(
                executor,
                lambda: tls_conn.sendall(
                    h11_conn.send(h11.Data(data=response["body"]))
                ),
            )
            await asyncio.get_event_loop().run_in_executor(
                executor, lambda: tls_conn.sendall(h11_conn.send(h11.EndOfMessage()))
            )

        except Exception as e:
            logger.error(
                f"HTTP processing error: {e}\n{''.join(traceback.format_exc())}"
            )

    except Exception as e:
        logger.error(f"Connection error: {e}\n{''.join(traceback.format_exc())}")
    finally:
        try:
            await asyncio.get_event_loop().run_in_executor(executor, tls_conn.close)
        except:
            pass
        client_sock.close()


###########################################################################
# Main
###########################################################################


async def main() -> None:
    # Set up TCP socket
    server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    host = "0.0.0.0"
    port = 4433
    server_sock.bind((host, port))
    server_sock.listen(5)
    server_sock.setblocking(False)
    logger.debug(f"Server listening on {host}:{port}")

    loop = asyncio.get_event_loop()
    while True:
        client_sock, addr = await loop.sock_accept(server_sock)
        loop.create_task(handle_connection(client_sock, addr))


if __name__ == "__main__":
    asyncio.run(main())


def start() -> None:
    asyncio.run(main())
