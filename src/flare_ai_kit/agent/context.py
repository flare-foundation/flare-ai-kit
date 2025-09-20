"""Module provides a single, shared instance of the Flare AI Kit SDK for agent."""

from flare_ai_kit.main import FlareAIKit

# This single `kit` instance will be imported and used by all agent tools.
# It will be initialized once when the module is first imported.
kit = FlareAIKit(config=None)
