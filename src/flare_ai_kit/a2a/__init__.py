"""Module providing components for interacting with A2A agents within flare"""

from .server import A2AServer
from .client import A2AClient
from . import schemas

__all__ = [
    "A2AServer",
    "A2AClient",
    "schemas"
]
