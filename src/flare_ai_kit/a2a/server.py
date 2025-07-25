"""Module for A2AServer, A2AService, and A2ARouteHandler."""

import inspect
import json
from collections.abc import Callable
from typing import Any

import uvicorn
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, ValidationError

from flare_ai_kit.a2a.schemas import (
    A2ARequest,
    AgentCard,
    InternalError,
    JSONRPCResponse,
    Message,
    MethodNotFoundError,
    SendMessageRequest,
    Task,
)


class A2AService:
    """
    Main logic for A2A operations.

    This class handles core agent-to-agent interactions.
    """

    def __init__(self, agent_card: AgentCard) -> None:
        """Initialize the A2A Server's service."""
        self.agent_card = agent_card
        self.tasks_storage: dict[str, Task] = {}
        self.messages_storage: dict[str, Message] = {}

        self._handlers: dict[type, Callable[..., Any]] = {}

    def add_handler(self, request_type: type, handler: Callable[..., Any]) -> None:
        """Adds a handler for an A2A request type."""
        self._handlers[request_type] = handler

    def get_handler(self, request_type: type) -> Callable[..., Any] | None:
        """Returns a handler by request type."""
        return self._handlers.get(request_type)


class A2ARequestHandler:
    """Handler for processing A2A RPC requests via registered service handlers."""

    def __init__(self, service: A2AService) -> None:
        """Init method for the A2A request handler."""
        self.service = service

    async def handle_rpc(self, request_data: BaseModel) -> JSONRPCResponse | Any:
        """Main RPC handler that routes to appropriate service method."""
        try:
            rpc_request = A2ARequest.validate_python(request_data)
            handler = self.service.get_handler(type(rpc_request))

            if handler is None:
                return JSONRPCResponse(error=MethodNotFoundError())

            result = handler(rpc_request)  # could be sync or async

            if inspect.isawaitable(result):
                return await result

        except (json.JSONDecodeError, ValidationError) as e:
            return JSONRPCResponse(
                id=getattr(request_data, "id", None),
                error=InternalError(data=str(e)),
            )
        else:
            return result


def create_app(service: A2AService, agent_card: AgentCard | None = None) -> FastAPI:
    """Factory function to create the FastAPI app with routes."""
    app = FastAPI()
    handler = A2ARequestHandler(service)

    @app.get("/", response_class=HTMLResponse)
    def read_root() -> HTMLResponse:  # type: ignore[valid-type]
        agent_name = agent_card.name if agent_card else "A2A agent"
        return HTMLResponse(f'<p style="font-size:40px">{agent_name}</p>')

    @app.get("/.well-known/agent.json")
    def agent_card_route() -> AgentCard:  # type: ignore[valid-type]
        return service.agent_card

    @app.post("/")
    async def handle_rpc(  # type: ignore[valid-type]
        request_data: SendMessageRequest,
    ) -> JSONRPCResponse | Any:
        return await handler.handle_rpc(request_data)

    return app


class A2AServer:
    """A2A server implementation exposing a run method to run it as a web API."""

    def __init__(
        self,
        agent_card: AgentCard,
        *,
        host: str = "127.0.0.1",
        port: int = 4500,
        service: A2AService | None = None,
    ) -> None:
        """Init method for the A2A server."""
        self.host = host
        self.port = port

        self.service = service or A2AService(agent_card)
        self.app = create_app(self.service, agent_card)

    def run(self) -> None:
        """Run the FastAPI server."""
        uvicorn.run(self.app, host=self.host, port=self.port)
