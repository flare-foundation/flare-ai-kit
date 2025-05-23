"""Gemini agent implementation using Google's Generative AI."""

import os
from typing import Any

import google.genai as genai  # type: ignore[import]

from .base import AgentBase, AgentInput, AgentOutput, Message


class GeminiLLMAdapter:
    """Adapter for Google Gemini LLM using google-genai package."""

    def __init__(self, api_key: str | None = None, model: str = "gemini-pro") -> None:
        self.api_key = api_key or os.getenv("GOOGLE_GENAI_API_KEY")
        if not self.api_key:
            error_msg = "Google Gemini API key not provided."
            raise ValueError(error_msg)
        self.model = model
        self.client = genai.Client(api_key=self.api_key)

    def generate_text(
        self, prompt: str, context: Any | None = None, **kwargs: Any
    ) -> str:
        """Generate text using the Gemini model."""
        full_prompt = prompt
        if context:
            full_prompt = f"Context: {context}\nPrompt: {prompt}"
        response = self.client.models.generate_content(model=self.model, contents=full_prompt, **kwargs)
        return response.text if hasattr(response, "text") else ""


class GeminiAgent(AgentBase):
    """Agent implementation using GeminiLLMAdapter."""

    llm_adapter: GeminiLLMAdapter | None = None
    context: Any | None = None

    def initialize(self, **kwargs: Any) -> None:
        """Initialize the agent with context."""
        self.context = kwargs.get("context")

    def process_input(self, agent_input: AgentInput) -> AgentOutput:
        """Process input and return output using the Gemini adapter."""
        self.add_message(Message(role="user", content=agent_input.message))
        response_text = self.llm_adapter.generate_text(
            prompt=agent_input.message, context=self.context
        )
        self.add_message(Message(role="agent", content=response_text))
        return AgentOutput(response=response_text, context=self.context)

    def update_context(self, context: Any) -> None:
        """Update the agent's context."""
        self.context = context
