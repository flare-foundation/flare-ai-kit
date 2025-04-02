"""Common utils for Flare AI Kit."""

import importlib.resources
import json
from functools import cache

from flare_ai_kit.common.exceptions import AbiError


# Use cache to avoid reloading/reparsing the same ABI repeatedly
@cache
def load_abi(abi_name: str) -> list[str]:
    """
    Loads and parses a contract ABI JSON file from package resources.

    The result is cached to improve performance on subsequent calls with the
    same abi_name.

    Args:
        abi_name: The base name of the ABI file (without .json extension)
                  located in the 'flare_ai_kit/abis' resources directory.

    Returns:
        The parsed ABI structure, typically a list of dictionaries.

    Raises:
        AbiError: If the ABI file is not found, cannot be parsed, is not in the
                  expected list format, or other loading errors occur.

    """
    resource_path = f"{abi_name}.json"
    package_name = "flare_ai_kit.abis"

    try:
        ref = importlib.resources.files(package_name).joinpath(resource_path)
        with ref.open("r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError as e:
        msg = (
            f"ABI resource '{resource_path}' not found within the "
            f"'{package_name}' package resources."
        )
        raise AbiError(msg) from e
    except json.JSONDecodeError as e:
        msg = f"Error decoding ABI JSON file '{resource_path}''"
        raise AbiError(msg) from e
    except (OSError, Exception) as e:
        # Catch other potential errors like permission issues
        msg = f"An unexpected error occurred while loading ABI '{resource_path}'"
        raise AbiError(msg) from e
