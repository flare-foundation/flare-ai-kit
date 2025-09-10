import asyncio
import json
import socket
import sys
from typing import Any

import h11
import structlog
from tlslite.api import HandshakeSettings, TLSConnection
from tlslite.extensions import SupportedGroupsExtension

logger = structlog.get_logger(__name__)

# Reading the host IP argument which may have been provided.
ip = sys.argv[1] if len(sys.argv) > 1 else None


token_address = {
    "wflr": "0x1D80c49BbBCd1C0911346656B529DF9E5c2F783d",
    "joule": "0xE6505f92583103AF7ed9974DEC451A7Af4e3A3bE",
    "usdc": "0xFbDa5F676cB37624f28265A144A48B0d6e87d3b6",
    "usdt": "0x0B38e83B86d491735fEaa0a791F65c2B99535396",
    "weth": "0x1502FA4be69d526124D453619276FacCab275d3D",
}


async def send_request(
    host: str = "127.0.0.1",
    port: int = 4433,
    method: str = "GET",
    path: str = "/",
    body: str | bytes | None = None,
    local_attestation_token: bytes | None = None,
) -> tuple[h11.Response | None, bytes]:
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.setblocking(False)
    loop = None
    tls_conn = None
    try:
        #
        # We start by connecting the socket to the server. This creates a TCP connection.
        #
        loop = asyncio.get_event_loop()
        await loop.sock_connect(sock, (host, port))
        logger.debug(f"Connected to {host}:{port}")

        #
        # We then execute the TLS handshake to secure the connection.
        #
        tls_conn = TLSConnection(sock)
        settings = HandshakeSettings()
        settings.minVersion = (3, 4)  # TLS 1.3
        settings.maxVersion = (3, 4)  # TLS 1.3
        supported_groups = SupportedGroupsExtension()
        supported_groups.create([23, 24])  # secp256r1 (23), secp384r1 (24)
        settings.extensions = [supported_groups]

        def do_handshake():
            tls_conn.handshakeClientCert(settings=settings)

        await loop.run_in_executor(None, do_handshake)
        logger.debug("TLS handshake complete!")

        #
        # We validate the attestation token we recieved and compare it to the token we have locally.
        #
        # This is done by reading AttestationTokenExtension from Certificate message of handshake.
        if hasattr(tls_conn, "_server_certificate") and tls_conn._server_certificate:
            cert_entry = tls_conn._server_certificate.certificate_list[0]
            for ext in cert_entry.extensions:
                if ext.extType == 65280:  # AttestationTokenExtension
                    if local_attestation_token:
                        if local_attestation_token == ext.token:
                            logger.debug(
                                "The attestation token from the TLS handshake matches the local token."
                            )
                        else:
                            logger.debug(
                                "",
                                one=type(local_attestation_token),
                                two=type(ext.token),
                            )
                            logger.debug(
                                "The attestation token from the TLS handshake DOES NOT MATCH the local token.",
                                local_attestation_token=local_attestation_token,
                                handshake_token=ext.token,
                            )
                    else:
                        logger.debug("No local attestation token to compare with.")
        else:
            logger.debug(
                "  No AttestationTokenExtension found (Certificate message not stored)"
            )

        #
        # We construct a HTTP request
        #
        h11_conn = h11.Connection(our_role=h11.CLIENT)
        headers = [
            (b"Host", f"{host}:{port}".encode()),
            (b"Accept", b"*/*"),
            (b"Connection", b"close"),
        ]
        if body and isinstance(body, str):
            headers.append((b"Content-Length", str(len(body.encode())).encode()))
        elif body:
            headers.append((b"Content-Length", str(len(body)).encode()))

        request = h11.Request(method=method, target=path, headers=headers)

        #
        # We send the HTTP request.
        #
        await loop.run_in_executor(
            None, lambda: tls_conn.sendall(h11_conn.send(request))
        )
        if body:
            data = h11.Data(data=body.encode() if isinstance(body, str) else body)
            await loop.run_in_executor(
                None, lambda: tls_conn.sendall(h11_conn.send(data))
            )
            await loop.run_in_executor(
                None, lambda: tls_conn.sendall(h11_conn.send(h11.EndOfMessage()))
            )
            logger.debug("Sent request", request=request, data=data)
        else:
            logger.debug("Sent request", request=request)

        #
        # We wait for a response, parse data if received, and return
        #
        response = None
        body = b""
        while True:
            try:
                data = await loop.run_in_executor(None, lambda: tls_conn.recv(4096))
                if not data:
                    break
            except Exception as e:
                logger.debug(f"Receive error: {e}")
                break

            h11_conn.receive_data(data)
            while True:
                event = h11_conn.next_event()
                if event is h11.NEED_DATA:
                    break
                if isinstance(event, h11.Response):
                    response = event
                elif isinstance(event, h11.Data):
                    body += event.data
                elif isinstance(event, h11.EndOfMessage) or isinstance(
                    event, h11.ConnectionClosed
                ):
                    break

            if response and h11_conn.our_state is h11.DONE:
                break

        if response:
            logger.debug(
                f"Received response: status={response.status_code}, headers={dict(response.headers)}, body={body}"
            )
            return response, body
        logger.debug("No response received")
        return None, b""

    except Exception as e:
        logger.debug(f"Error: {e}")
    finally:
        try:
            if loop is not None and tls_conn is not None:
                await loop.run_in_executor(None, tls_conn.close)
            else:
                raise RuntimeError("Event loop or tls_conn is not available")
        except:
            pass
        sock.close()


def parse_from_response(response: Any, body: Any, var_name: str) -> Any | None:
    if response and response.status_code == 201:
        try:
            body_json = json.loads(body.decode("utf-8"))
            if isinstance(body_json, dict):
                result = body_json.get(var_name)
                if result is not None:
                    return result
                logger.warning("deposit_id missing in response", body=body_json)
        except (json.JSONDecodeError, UnicodeDecodeError) as e:
            logger.error(
                f"JSON parse error: {e}", body=body.decode("utf-8", errors="replace")
            )
    elif response:
        logger.error(
            "Request failed",
            status=response.status_code,
            body=body.decode("utf-8", errors="replace"),
        )
    else:
        logger.error("No response received")


async def stargate_bridge(
    chain_id: int, amount: float, attestation_token: bytes | None
) -> str | None:
    """
    Send a POST /bridge request to initiate a Stargate bridge and parse tx_hash from the response.

    Args:
        chain_id: Destination chain ID. This is the endpoint ID from here: https://docs.stargate.finance/resources/contracts/mainnet-contracts
        amount: Amount to bridge in token units (e.g., 0.0002 for 0.0002 ETH).
        attestation_token: Attestation token for TLS handshake, or None.

    Returns:
        Transaction hash as str, or None if not found or request fails.
    """
    payload_dict = {
        "chain_id": chain_id,
        "amount_wei": int(amount * 10**18),  # Convert to wei
    }
    payload = json.dumps(payload_dict).encode("utf-8")
    response, body = await send_request(
        method="POST",
        path="/bridge",
        local_attestation_token=attestation_token,
        body=payload,
    )
    tx_hash = parse_from_response(response, body, "tx_hash")
    return tx_hash


async def sparkdex_swap(
    token_in_addr: str,
    token_out_addr: str,
    amount: float,
    amount_out_min: float,
    attestation_token: bytes | None,
) -> str | None:
    """
    Send a POST /swap request to perform a SparkDEX swap and parse tx_hash from the response.

    Args:
        token_in_addr: Address of the input token (e.g., WFLR address).
        token_out_addr: Address of the output token (e.g., WETH address).
        amount: Amount to swap in token units (e.g., 1.0 for 1 WFLR).
        amount_out_min: Minimum amount to receive in output token units (e.g., 0 for no minimum).
        attestation_token: Attestation token for TLS handshake, or None.

    Returns:
        Transaction hash as str, or None if not found or request fails.
    """
    payload_dict = {
        "token_in_addr": token_in_addr,
        "token_out_addr": token_out_addr,
        "amount_in_WEI": int(amount * 10**18),  # Convert to wei
        "amount_out_min_WEI": int(amount_out_min * 10**18),  # Convert to wei
    }
    payload = json.dumps(payload_dict).encode("utf-8")
    response, body = await send_request(
        method="POST",
        path="/swap",
        local_attestation_token=attestation_token,
        body=payload,
    )
    tx_hash = parse_from_response(response, body, "tx_hash")
    return tx_hash


async def wrap_flr(amount: float, attestation_token: bytes | None) -> str | None:
    """
    Send a POST /wrap request to wrap FLR to WFLR and parse tx_hash from the response.

    Args:
        amount: Amount of FLR to wrap in FLR units (e.g., 1.0 for 1 FLR).
        attestation_token: Attestation token for TLS handshake, or None.

    Returns:
        Transaction hash as str, or None if not found or request fails.
    """
    payload_dict = {
        "amount_WEI": int(amount * 10**18)  # Convert to wei
    }
    payload = json.dumps(payload_dict).encode("utf-8")
    response, body = await send_request(
        method="POST",
        path="/wrap",
        local_attestation_token=attestation_token,
        body=payload,
    )
    tx_hash = parse_from_response(response, body, "tx_hash")
    return tx_hash


async def unwrap_wflr(amount: float, attestation_token: bytes | None) -> str | None:
    """
    Send a POST /unwrap request to unwrap WFLR to FLR and parse tx_hash from the response.

    Args:
        amount: Amount of WFLR to unwrap in WFLR units (e.g., 1.0 for 1 WFLR).
        attestation_token: Attestation token for TLS handshake, or None.

    Returns:
        Transaction hash as str, or None if not found or request fails.
    """
    payload_dict = {
        "amount_WEI": int(amount * 10**18)  # Convert to wei
    }
    payload = json.dumps(payload_dict).encode("utf-8")
    response, body = await send_request(
        method="POST",
        path="/unwrap",
        local_attestation_token=attestation_token,
        body=payload,
    )
    tx_hash = parse_from_response(response, body, "tx_hash")
    return tx_hash


async def stake(amount: float, attestation_token: bytes | None) -> str | None:
    """
    Send a POST /stake request to stake tokens and parse tx_hash from the response.

    Args:
        amount: Amount to stake in token units (e.g., 1.0 for 1 token).
        attestation_token: Attestation token for TLS handshake, or None.

    Returns:
        Transaction hash as str, or None if not found or request fails.
    """
    payload_dict = {
        "amount_WEI": int(amount * 10**18)  # Convert to wei
    }
    payload = json.dumps(payload_dict).encode("utf-8")
    response, body = await send_request(
        method="POST",
        path="/stake",
        local_attestation_token=attestation_token,
        body=payload,
    )
    tx_hash = parse_from_response(response, body, "tx_hash")
    return tx_hash


async def unstake(amount: float, attestation_token: bytes | None) -> str | None:
    """
    Send a POST /unstake request to unstake tokens and parse tx_hash from the response.

    Args:
        amount: Amount to unstake in token units (e.g., 1.0 for 1 token).
        attestation_token: Attestation token for TLS handshake, or None.

    Returns:
        Transaction hash as str, or None if not found or request fails.
    """
    payload_dict = {
        "amount_WEI": int(amount * 10**18)  # Convert to wei
    }
    payload = json.dumps(payload_dict).encode("utf-8")
    response, body = await send_request(
        method="POST",
        path="/unstake",
        local_attestation_token=attestation_token,
        body=payload,
    )
    tx_hash = parse_from_response(response, body, "tx_hash")
    return tx_hash


async def kinetic_supply(
    token_symbol: str, amount: float, attestation_token: bytes | None
) -> str | None:
    """
    Send a POST /kinetic_supply request to supply tokens and parse tx_hash from the response.

    Args:
        token_symbol: Symbol of the token to supply (e.g., 'sflr').
        amount: Amount to supply in token units (e.g., 1.0 for 1 token).
        attestation_token: Attestation token for TLS handshake, or None.

    Returns:
        Transaction hash as str, or None if not found or request fails.
    """
    payload_dict = {
        "token_symbol": token_symbol,
        "amount_WEI": int(amount * 10**18),  # Convert to wei
    }
    payload = json.dumps(payload_dict).encode("utf-8")
    response, body = await send_request(
        method="POST",
        path="/kinetic_supply",
        local_attestation_token=attestation_token,
        body=payload,
    )
    tx_hash = parse_from_response(response, body, "tx_hash")
    return tx_hash


async def kinetic_withdraw(
    token_symbol: str, amount: float, attestation_token: bytes | None
) -> str | None:
    """
    Send a POST /kinetic_withdraw request to withdraw tokens and parse tx_hash from the response.

    Args:
        token_symbol: Symbol of the token to withdraw (e.g., 'sflr').
        amount: Amount to withdraw in token units (e.g., 1.0 for 1 token).
        attestation_token: Attestation token for TLS handshake, or None.

    Returns:
        Transaction hash as str, or None if not found or request fails.
    """
    payload_dict = {
        "token_symbol": token_symbol,
        "amount_WEI": int(amount * 10**18),  # Convert to wei
    }
    payload = json.dumps(payload_dict).encode("utf-8")
    response, body = await send_request(
        method="POST",
        path="/kinetic_withdraw",
        local_attestation_token=attestation_token,
        body=payload,
    )
    tx_hash = parse_from_response(response, body, "tx_hash")
    return tx_hash


async def kinetic_enable_collateral(
    token_symbol: str, attestation_token: bytes | None
) -> str | None:
    """
    Send a POST /kinetic_enable_collateral request to enable collateral and parse tx_hash from the response.

    Args:
        token_symbol: Symbol of the token to enable as collateral (e.g., 'sflr').
        attestation_token: Attestation token for TLS handshake, or None.

    Returns:
        Transaction hash as str, or None if not found or request fails.
    """
    payload_dict = {"token_symbol": token_symbol}
    payload = json.dumps(payload_dict).encode("utf-8")
    response, body = await send_request(
        method="POST",
        path="/kinetic_enable_collateral",
        local_attestation_token=attestation_token,
        body=payload,
    )
    tx_hash = parse_from_response(response, body, "tx_hash")
    return tx_hash


async def kinetic_disable_collateral(
    token_symbol: str, attestation_token: bytes | None
) -> str | None:
    """
    Send a POST /kinetic_disable_collateral request to disable collateral and parse tx_hash from the response.

    Args:
        token_symbol: Symbol of the token to disable as collateral (e.g., 'sflr').
        attestation_token: Attestation token for TLS handshake, or None.

    Returns:
        Transaction hash as str, or None if not found or request fails.
    """
    payload_dict = {"token_symbol": token_symbol}
    payload = json.dumps(payload_dict).encode("utf-8")
    response, body = await send_request(
        method="POST",
        path="/kinetic_disable_collateral",
        local_attestation_token=attestation_token,
        body=payload,
    )
    tx_hash = parse_from_response(response, body, "tx_hash")
    return tx_hash


async def cyclo_lock(
    token_symbol: str, amount: float, attestation_token: bytes | None
) -> tuple[str | None, int | None]:
    """
    Send a POST /cyclo_lock request and parse deposit_id and tx_hash from the response.

    Args:
        token_symbol: Symbol of the token to lock (e.g., 'sflr').
        amount: Amount to lock in token units (e.g., 1.0 for 1 sFLR).
        attestation_token: Attestation token for TLS handshake, or None.

    Returns:
        Tuple of (tx_hash, deposit_id), where each is str/int or None if not found or request fails.
    """
    payload_dict = {"token_symbol": token_symbol, "amount_WEI": int(amount * 10**18)}
    payload = json.dumps(payload_dict).encode("utf-8")
    response, body = await send_request(
        method="POST",
        path="/cyclo_lock",
        local_attestation_token=attestation_token,
        body=payload,
    )
    tx_hash = parse_from_response(response, body, "tx_hash")
    deposit_id = parse_from_response(response, body, "deposit_id")
    return tx_hash, deposit_id


async def cyclo_unlock(
    token_symbol: str,
    deposit_id: int,
    unlock_proportion: float,
    attestation_token: bytes | None,
) -> str | None:
    """
    Send a POST /cyclo_unlock request and parse tx_hash from the response.

    Args:
        token_symbol: Symbol of the token to unlock (e.g., 'sflr').
        deposit_id: Deposit ID from a previous lock operation.
        unlock_proportion: Proportion of the deposit to unlock (e.g., 1.0 for full unlock).
        attestation_token: Attestation token for TLS handshake, or None.

    Returns:
        Transaction hash as str, or None if not found or request fails.
    """
    payload_dict = {
        "token_symbol": token_symbol,
        "deposit_id": deposit_id,
        "unlock_proportion": unlock_proportion,
    }
    payload = json.dumps(payload_dict).encode("utf-8")
    response, body = await send_request(
        method="POST",
        path="/cyclo_unlock",
        local_attestation_token=attestation_token,
        body=payload,
    )
    tx_hash = parse_from_response(response, body, "tx_hash")
    return tx_hash


async def openocean_swap(
    token_in_str: str,
    token_out_str: str,
    amount: float,
    speed: str,
    attestation_token: bytes | None,
) -> str | None:
    """
    Send a POST /openocean_swap request to perform a token swap and parse tx_hash from the response.

    Args:
        token_in_str: Symbol of the input token (e.g., 'wflr').
        token_out_str: Symbol of the output token (e.g., 'weth').
        amount: Amount to swap in token units (e.g., 1.0 for 1 WFLR).
        speed: Swap speed preference (e.g., 'fast', 'normal', 'safe').
        attestation_token: Attestation token for TLS handshake, or None.

    Returns:
        Transaction hash as str, or None if not found or request fails.
    """
    payload_dict = {
        "token_in_str": token_in_str,
        "token_out_str": token_out_str,
        "amount": amount,
        "speed": speed,
    }
    payload = json.dumps(payload_dict).encode("utf-8")
    response, body = await send_request(
        method="POST",
        path="/openocean_swap",
        local_attestation_token=attestation_token,
        body=payload,
    )
    tx_hash = parse_from_response(response, body, "tx_hash")
    return tx_hash


async def main() -> None:
    attestation_token = None
    try:
        with open("sim_token.txt", "rb") as f:
            attestation_token = f.read()
            logger.debug(
                f"Local attestation token size: {len(attestation_token)} bytes"
            )
    except FileNotFoundError:
        logger.debug("No client attestation token provided")

    #
    # Wrap FLR to WFLR
    wrap_tx_hash = await wrap_flr(
        amount=20.0,  # 1 FLR
        attestation_token=attestation_token,
    )
    if wrap_tx_hash:
        logger.debug(
            f"Wrap Transaction hash: https://flarescan.com/tx/0x{wrap_tx_hash}"
        )

    #
    # SparkDEX swap
    # swap_tx_hash = await sparkdex_swap(
    #    token_in_addr=token_address["wflr"],
    #    token_out_addr=token_address["weth"],
    #    amount=10.0,  # 1 WFLR
    #    amount_out_min=0.0,  # No minimum
    #    attestation_token=attestation_token
    # )
    # if swap_tx_hash:
    #     logger.debug(f"Swap Transaction hash: https://flarescan.com/tx/0x{swap_tx_hash}")

    #
    # Stargate bridge
    # chain_id is the endpoint ID from here: https://docs.stargate.finance/resources/contracts/mainnet-contracts
    # bridge_tx_hash = await stargate_bridge(
    #    chain_id=30184, # Base chain
    #    amount=0.00001,  # 0.0001 ETH
    #    attestation_token=attestation_token
    # )
    # if bridge_tx_hash:
    #    logger.debug(f"Bridge Transaction hash: https://flarescan.com/tx/0x{bridge_tx_hash}")

    #
    # Unwrap WFLR to FLR
    # unwrap_tx_hash = await unwrap_wflr(
    #   amount=20,
    #   attestation_token=attestation_token
    # )
    # if unwrap_tx_hash:
    #   logger.debug(f"Unwrap Transaction hash: https://flarescan.com/tx/0x{unwrap_tx_hash}")

    #
    # Stake tokens
    # stake_tx_hash = await stake(
    #    amount=19.0,  # 1 token
    #    attestation_token=attestation_token
    # )
    # if stake_tx_hash:
    #    logger.debug(f"Stake Transaction hash: https://flarescan.com/tx/0x{stake_tx_hash}")

    #
    # Unstake tokens
    # unstake_tx_hash = await unstake(
    #    amount=7.4724,
    #    attestation_token=attestation_token
    # )
    # if unstake_tx_hash:
    #    logger.debug(f"Unstake Transaction hash: https://flarescan.com/tx/0x{unstake_tx_hash}")

    #
    # Supply tokens to Kinetic
    # supply_tx_hash = await kinetic_supply(
    #    token_symbol="sflr",
    #    amount=1.0,  # 1 sFLR
    #    attestation_token=attestation_token
    # )
    # if supply_tx_hash:
    #    logger.debug(f"Kinetic Supply Transaction hash: https://flarescan.com/tx/0x{supply_tx_hash}")

    # time.sleep(10)

    #
    # Withdraw tokens from Kinetic
    # withdraw_tx_hash = await kinetic_withdraw(
    #    token_symbol="sflr",
    #    amount=1.0,  # 1 sFLR
    #    attestation_token=attestation_token
    # )
    # if withdraw_tx_hash:
    #    logger.debug(f"Kinetic Withdraw Transaction hash: https://flarescan.com/tx/0x{withdraw_tx_hash}")

    #
    # Enable collateral in Kinetic
    # enable_tx_hash = await kinetic_enable_collateral(
    #    token_symbol="sflr",
    #    attestation_token=attestation_token
    # )
    # if enable_tx_hash:
    #    logger.debug(f"Kinetic Enable Collateral Transaction hash: https://flarescan.com/tx/0x{enable_tx_hash}")

    #
    # Disable collateral in Kinetic
    # disable_tx_hash = await kinetic_disable_collateral(
    #    token_symbol="sflr",
    #    attestation_token=attestation_token
    # )
    # if disable_tx_hash:
    #    logger.debug(f"Kinetic Disable Collateral Transaction hash: https://flarescan.com/tx/0x{disable_tx_hash}")

    #
    # Cyclo lock and unlock
    # lock_tx_hash, deposit_id = await cyclo_lock(
    #    token_symbol="sflr",
    #    amount=1.0,  # 1 sFLR
    #    attestation_token=attestation_token
    # )
    # if deposit_id is not None:
    #    logger.debug(f"Lock Deposit ID: {deposit_id}")
    #    logger.debug(f"Lock Transaction hash: {lock_tx_hash}")
    #    # Unlock tokens
    #    unlock_tx_hash = await cyclo_unlock(
    #        token_symbol="sflr",
    #        deposit_id=deposit_id,
    #        unlock_proportion=1.0,  # Full unlock
    #        attestation_token=attestation_token
    #    )
    #    if unlock_tx_hash:
    #        logger.debug(f"Unlock Transaction hash: https://flarescan.com/tx/0x{unlock_tx_hash}")

    #
    # Swap with Openocean
    # oswap_tx_hash = await openocean_swap(
    #     token_in_str="WFLR",
    #     token_out_str="USDT",
    #     amount=int(19.0 * 10**18),
    #     speed="standard",
    #     attestation_token=attestation_token,
    # )
    # if oswap_tx_hash:
    #     logger.debug(
    #         f"Unlock Transaction hash: https://flarescan.com/tx/0x{oswap_tx_hash}"
    #     )


if __name__ == "__main__":
    asyncio.run(main())
    # loop = asyncio.get_event_loop()
    # try:
    #    asyncio.run(main())
    # finally:
    #    loop.run_until_complete(loop.shutdown_asyncgens())
    #    loop.close()
