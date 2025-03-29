"""Common utils for Flare AI Kit."""

import importlib.resources
import json

from flare_ai_kit.common.exceptions import AbiError


def load_abi(abi_name: str) -> list[str]:
    """Loads a contract ABI JSON file from the package resources."""
    try:
        ref = importlib.resources.files("flare_ai_kit.abis").joinpath(
            f"{abi_name}.json"
        )
        with ref.open("r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError as e:
        msg = f"ABI file '{abi_name}.json' not found in package resources."
        raise AbiError(msg) from e
    except json.JSONDecodeError as e:
        msg = f"Error decoding ABI JSON file '{abi_name}.json'"
        raise AbiError(msg) from e
    except Exception as e:
        # Catch other potential errors like permission issues
        msg = f"Failed to load ABI '{abi_name}.json'"
        raise AbiError(msg) from e
