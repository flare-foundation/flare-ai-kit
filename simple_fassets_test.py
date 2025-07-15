#!/usr/bin/env python
"""Simple test script to verify FAssets implementation is valid Python."""

import ast
import importlib
import json
import logging
import sys
from pathlib import Path
from typing import TYPE_CHECKING, Any, TypeVar

if TYPE_CHECKING:
    from collections.abc import Callable

from flare_ai_kit.ecosystem.protocols.fassets import FAssets

logger = logging.getLogger(__name__)

T = TypeVar("T")


def test_syntax() -> bool:
    """Test if fassets.py has valid Python syntax."""
    file_path = (
        Path(__file__).parent
        / "src"
        / "flare_ai_kit"
        / "ecosystem"
        / "protocols"
        / "fassets.py"
    )

    if not file_path.exists():
        return False

    try:
        content = file_path.read_text(encoding="utf-8")
        ast.parse(content)
    except SyntaxError:
        logger.exception("Syntax error in fassets.py")
        return False
    return True


def test_imports() -> bool:
    """Test if required imports work correctly."""
    try:
        # Add the src directory to the path
        sys.path.insert(0, str(Path(__file__).parent / "src"))

        # Try to import the main classes
        importlib.import_module("flare_ai_kit.common.schemas")
        importlib.import_module("flare_ai_kit.ecosystem.protocols.fassets")
    except ImportError:
        logger.exception("Import error")
        return False
    return True


def test_structure() -> bool:
    """Test if FAssets class has required structure."""
    try:
        sys.path.insert(0, str(Path(__file__).parent / "src"))

        # Check required methods
        required_methods = [
            "create",
            "get_supported_fassets",
            "get_fasset_info",
            "get_all_agents",
            "get_agent_info",
            "reserve_collateral",
            "execute_minting",
            "redeem_from_agent",
            "get_fasset_balance",
            "swap_fasset_for_native",
            "swap_native_for_fasset",
            "swap_fasset_for_fasset",
        ]

        return all(hasattr(FAssets, method) for method in required_methods)
    except (ImportError, AttributeError):
        logger.exception("Structure test failed")
        return False


def test_abi_files() -> bool:
    """Test if all required ABI files exist and have correct structure."""
    base_path = Path(__file__).parent / "src" / "flare_ai_kit" / "abis"

    required_abis = {
        "FlareContractRegistry.json": ["getContractAddressByName"],
        "AssetManager.json": [
            "getSettings",
            "getAgents",
            "getAgentInfo",
            "reserveCollateral",
            "executeMinting",
            "redeem",
        ],
        "ERC20.json": ["balanceOf", "approve", "allowance"],
        "SparkDEXRouter.json": ["swapExactTokensForETH"],
    }

    for abi_file, required_functions in required_abis.items():
        try:
            file_path = base_path / abi_file
            if not file_path.exists():
                logger.error("ABI file not found: %s", abi_file)
                return False

            content = file_path.read_text(encoding="utf-8")
            abi_data: list[dict[str, Any]] = json.loads(content)

            # Check each required function exists in the ABI
            for func_name in required_functions:
                found = False
                for entry in abi_data:
                    entry_type = entry.get("type", "")
                    entry_name = entry.get("name", "")
                    if entry_type == "function" and entry_name == func_name:
                        found = True
                        break
                if not found:
                    logger.error(
                        "Missing required function in %s: %s", abi_file, func_name
                    )
                    return False
        except (json.JSONDecodeError, FileNotFoundError):
            logger.exception("Error processing %s", abi_file)
            return False
    return True


def test_file_syntax() -> bool:
    """Test individual file imports to verify syntax."""
    test_files = {
        "fassets": "src/flare_ai_kit/ecosystem/protocols/fassets.py",
        "schemas": "src/flare_ai_kit/common/schemas.py",
        "main": "src/flare_ai_kit/main.py",
    }

    for name, file_path in test_files.items():
        try:
            with Path(file_path).open(encoding="utf-8") as f:
                content = f.read()
            compile(content, file_path, "exec")
        except (FileNotFoundError, SyntaxError):
            logger.exception("Error in %s", name)
            return False
    return True


def test_file_imports() -> bool:
    """Test if files can be imported without errors."""
    try:
        # Reset path
        sys.path.insert(0, str(Path(__file__).parent / "src"))

        # Test direct imports
        importlib.import_module("flare_ai_kit.common.schemas")
        importlib.import_module("flare_ai_kit.ecosystem.protocols.fassets")
    except ImportError:
        logger.exception("Import test failed")
        return False
    return True


def test_data_models() -> bool:
    """Test if data models are properly defined."""
    try:
        file_path = (
            Path(__file__).parent / "src" / "flare_ai_kit" / "common" / "schemas.py"
        )
        content = file_path.read_text(encoding="utf-8")

        # Check for required models
        models_to_check = [
            ("FAssetType", "class FAssetType"),
            ("FAssetInfo", "class FAssetInfo"),
            ("AgentInfo", "class AgentInfo"),
            ("CollateralReservationData", "class CollateralReservationData"),
            ("RedemptionRequestData", "class RedemptionRequestData"),
        ]

        return all(pattern in content for _, pattern in models_to_check)
    except FileNotFoundError:
        logger.exception("Data models test failed")
        return False


def test_fassets_structure() -> bool:
    """Test FAssets class internal structure."""
    try:
        file_path = (
            Path(__file__).parent
            / "src"
            / "flare_ai_kit"
            / "ecosystem"
            / "protocols"
            / "fassets.py"
        )
        content = file_path.read_text(encoding="utf-8")

        # Check for required structure
        structure_checks = [
            ("FAssets class definition", "class FAssets(Flare):"),
            ("create classmethod", "async def create(cls,"),
            (
                "_initialize_sparkdex_router method",
                "async def _initialize_sparkdex_router(self):",
            ),
            (
                "_initialize_supported_fassets method",
                "async def _initialize_supported_fassets(self):",
            ),
            (
                "get_supported_fassets method",
                "async def get_supported_fassets(self) -> dict[str, FAssetInfo]:",
            ),
            (
                "get_fasset_info method",
                "async def get_fasset_info(self, fasset_type: FAssetType) "
                "-> FAssetInfo:",
            ),
            (
                "get_all_agents method",
                "async def get_all_agents(self, fasset_type: FAssetType) -> list:",
            ),
            ("get_agent_info method", "async def get_agent_info("),
            ("get_available_lots method", "async def get_available_lots("),
            ("reserve_collateral method", "async def reserve_collateral("),
            (
                "get_asset_manager_settings method",
                "async def get_asset_manager_settings(",
            ),
            ("redeem_from_agent method", "async def redeem_from_agent("),
            ("get_redemption_request method", "async def get_redemption_request("),
            (
                "get_collateral_reservation_data method",
                "async def get_collateral_reservation_data(",
            ),
            ("get_fasset_balance method", "async def get_fasset_balance("),
            ("get_fasset_allowance method", "async def get_fasset_allowance("),
            ("approve_fasset method", "async def approve_fasset("),
            ("swap_fasset_for_native method", "async def swap_fasset_for_native("),
            ("swap_native_for_fasset method", "async def swap_native_for_fasset("),
            ("swap_fasset_for_fasset method", "async def swap_fasset_for_fasset("),
            ("execute_minting method", "async def execute_minting("),
        ]

        return all(pattern in content for _, pattern in structure_checks)
    except FileNotFoundError:
        logger.exception("FAssets structure test failed")
        return False


def test_integration_setup() -> bool:
    """Test if FAssets is properly integrated into FlareAIKit."""
    try:
        file_path = Path(__file__).parent / "src" / "flare_ai_kit" / "main.py"
        content = file_path.read_text(encoding="utf-8")

        integration_checks = [
            ("FlareAIKit class import", "from flare_ai_kit.main import FlareAIKit"),
            (
                "FAssets property in FlareAIKit",
                "self.fassets = FAssets(self.settings.ecosystem)",
            ),
        ]

        return all(pattern in content for _, pattern in integration_checks)
    except FileNotFoundError:
        logger.exception("Integration test failed")
        return False


def main() -> int:
    """Run all tests and report results."""
    logging.basicConfig(level=logging.INFO)
    logger.info("Testing FAssets Implementation...")

    tests: list[tuple[str, Callable[[], bool]]] = [
        ("Syntax", test_syntax),
        ("Imports", test_imports),
        ("Structure", test_structure),
        ("ABI Files", test_abi_files),
        ("File Syntax", test_file_syntax),
        ("File Imports", test_file_imports),
        ("Data Models", test_data_models),
        ("FAssets Structure", test_fassets_structure),
        ("Integration", test_integration_setup),
    ]

    failed = False
    for name, test_func in tests:
        result = test_func()
        logger.info("%s Test: %s", name, "PASS" if result else "FAIL")
        if not result:
            failed = True

    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
