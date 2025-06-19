"""Google Gemini LLM adapter for the Agent Framework."""

import os
from typing import Any

from google import genai  # type: ignore[import]

from .base import AgentBase, AgentInput, AgentOutput, Message


class GeminiLLMAdapter:
    """Adapter for Google Gemini LLM."""

    def __init__(self, api_key: str | None = None, model: str = "gemini-pro"):
        """Initialize the Gemini LLM adapter."""
        self.api_key = api_key or os.getenv("GOOGLE_API_KEY")
        if not self.api_key:
            raise ValueError("Google API key is required")

        self.model = model
        self.client = genai.Client(api_key=self.api_key)

    def generate_text(
        self, prompt: str, context: str | None = None, **kwargs: Any
    ) -> str:
        """Generate text using Gemini LLM."""
        full_prompt = prompt
        if context:
            full_prompt = f"Context: {context}\nPrompt: {prompt}"
        response = self.client.models.generate_content(
            model=self.model, contents=full_prompt, **kwargs
        )  # type: ignore
        return response.text if hasattr(response, "text") and response.text else ""


class GeminiAgent(AgentBase):
    """Agent implementation using Google Gemini LLM."""

    def __init__(self, api_key: str | None = None, model: str = "gemini-pro"):
        """Initialize the Gemini agent."""
        super().__init__()
        self.llm_adapter = GeminiLLMAdapter(api_key=api_key, model=model)

    def process(self, input_data: AgentInput) -> AgentOutput:
        """Process input using Gemini LLM."""
        # Add user message to conversation history
        self.conversation_history.append(
            Message(role="user", content=input_data.message)
        )

        # Generate response using Gemini
        response_text = self.llm_adapter.generate_text(
            prompt=input_data.message,
            context=input_data.context,
        )

        # Add assistant response to conversation history
        self.conversation_history.append(
            Message(role="assistant", content=response_text)
        )

        return AgentOutput(
            response=response_text,
            context=input_data.context,
        )
