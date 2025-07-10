import uvicorn
import asyncio
from pydantic import BaseModel
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from typing import Dict, Optional, Callable, Any

from . import schemas


class A2AService:
    """Main logic for A2A operations"""

    def __init__(self, agent_card: schemas.AgentCard):
        self.agent_card = agent_card
        self.tasks_storage: Dict[str, schemas.Task] = {}
        self.messages_storage: Dict[str, schemas.Message] = {}

        self._handlers: dict[type, Callable[..., Any]] = {}

    def add_handler(self, request_type: type, handler: Callable[..., Any]):
        self._handlers[request_type] = handler

    def get_handler(self, request_type: type) -> Optional[Callable[..., Any]]:
        return self._handlers.get(request_type)


class A2ARequestHandler:
    """Handler for processing A2A RPC requests via registered service handlers"""

    def __init__(self, service: A2AService):
        self.service = service

    async def handle_rpc(
        self, request_data: BaseModel):
        """Main RPC handler that routes to appropriate service method"""
        try:
            rpc_request = schemas.A2ARequest.validate_python(request_data)
            handler = self.service.get_handler(type(rpc_request))

            if handler is None:
                return schemas.JSONRPCResponse(
                    id=rpc_request.id, error=schemas.MethodNotFoundError()
                )

            result = handler(rpc_request)  # could be sync or async

            if asyncio.iscoroutine(result):
                result = await result

            return result

        except Exception as e:
            print(f"Error processing request: {e}")
            return schemas.JSONRPCResponse(
                id=getattr(request_data, "id", None),
                error=schemas.InternalError(data=str(e)),
            )


def create_app(
    service: A2AService, agent_card: schemas.AgentCard | None = None
) -> FastAPI:
    """Factory function to create the FastAPI app with routes"""
    app = FastAPI()
    handler = A2ARequestHandler(service)

    @app.get("/", response_class=HTMLResponse)
    def read_root():  # type: ignore
        agent_name = agent_card.name if agent_card else "A2A agent"
        return f'<p style="font-size:40px">{agent_name}</p>'

    @app.get("/.well-known/agent.json")
    def agent_card_route(request: Request):  # type: ignore
        return service.agent_card

    @app.post("/")
    async def handle_rpc(request_data: schemas.SendMessageRequest):  # type: ignore
        return await handler.handle_rpc(request_data)

    return app


class A2AServer:
    """A2A server implementation exposing a run method to run it as a web API"""

    def __init__(
        self,
        agent_card: schemas.AgentCard,
        *,
        host: str = "127.0.0.1",
        port: int = 4500,
        service: Optional[A2AService] = None,
    ):
        self.host = host
        self.port = port

        self.service = service or A2AService(agent_card)
        self.app = create_app(self.service, agent_card)

    def run(self):
        """Run the server"""
        uvicorn.run(self.app, host=self.host, port=self.port)
