
# backend/main.py
"""
AI Agent API Main Application Module

This module initializes and configures the FastAPI application for the AI Agent API.
It sets up CORS middleware, integrates various providers (AI, blockchain, attestation),
and configures the chat routing system.

Dependencies:
    - FastAPI for the web framework
    - Structlog for structured logging
    - CORS middleware for cross-origin resource sharing
    - Custom providers for AI, blockchain, and attestation services
"""
print("Hello TORKEL")
import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from flare_ai_kit.tee import create_ssl_context
import uvicorn
from uvicorn.config import Config
from uvicorn.server import Server
import asyncio

from .chat import ChatRouter
from flare_ai_kit.tee.attestation import VtpmAttestation

from settings import settings

logger = structlog.get_logger(__name__)


def create_app() -> FastAPI:
    """
    Create and configure the FastAPI application instance.

    This function:
    1. Creates a new FastAPI instance
    2. Configures CORS middleware with settings from the configuration
    3. Initializes required service providers:
       - GeminiProvider for AI capabilities
       - FlareProvider for blockchain interactions
       - Vtpm for attestation services
       - PromptService for managing chat prompts
    4. Sets up routing for chat endpoints

    Returns:
        FastAPI: Configured FastAPI application instance

    Configuration:
        The following settings are used from settings module:
        - api_version: API version string
        - cors_origins: List of allowed CORS origins
        - gemini_api_key: API key for Gemini AI service
        - gemini_model: Model identifier for Gemini AI
        - web3_provider_url: URL for Web3 provider
        - simulate_attestation: Boolean flag for attestation simulation
    """
    app = FastAPI(
        title="AI Agent API", version=settings.api_version, redirect_slashes=False
    )

    # Configure CORS middleware with settings from configuration
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Initialize router with service providers
    chat = ChatRouter(
        #ai=GeminiProvider(api_key=settings.gemini_api_key, model=settings.gemini_model),
        #blockchain=FlareProvider(web3_provider_url=settings.web3_provider_url),
        attestation=VtpmAttestation(simulate=settings.simulate_attestation)
        #prompts=PromptService(),
    )

    # Register chat routes with API
    app.include_router(chat.router, prefix="/api/routes/chat", tags=["chat"])
    return app


app = create_app()


async def start() -> None:
    """
    Start the FastAPI application server using uvicorn with RA-TLS and an in-memory certificate.

    This function:
    1. Initializes the attestation provider.
    2. Creates an in-memory SSLContext with a self-signed certificate and attestation token.
    3. Runs uvicorn with the custom SSL context.
    """
    # Initialize attestation
    attestation = VtpmAttestation(simulate=settings.simulate_attestation)
    
    # Generate attestation token
    token = attestation.get_token([])  # Adjust if specific input is needed

    # Create SSL context with attestation token
    ssl_context = create_ssl_context(token, common_name="localhost", days_valid=365)

    # Configure uvicorn with SSL context
    config = Config(
        app=app,
        host="0.0.0.0",
        port=8080,
        ssl_certfile=None,
        ssl_keyfile=None,
        loop="asyncio",
    )

    # Create and run uvicorn server with custom SSL context
    server = Server(config)
    server.config.ssl = ssl_context

    await server.serve()

if __name__ == "__main__":
    asyncio.run(start())

