# flare_ai_kit/adk/__init__.py

from ..tool import tool  # pyright: ignore[reportUnknownvariableType]

# This exposes `adk.tool` to users who import `adk`
__all__ = ["tool"]
