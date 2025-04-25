"""
Prompt Service Module for Flare AI Kit

This module provides a service layer for managing and formatting AI prompts.
It acts as a wrapper around the PromptLibrary, adding error handling and
logging capabilities. The service is responsible for retrieving prompts,
formatting them with provided parameters, and returning the formatted prompts
along with their associated metadata.

Example:
    ```python
    service = PromptService()
    prompt, mime_type, schema = service.get_formatted_prompt(
        "token_send", amount="100", address="0x123..."
    )
    ```
"""

from typing import Any

import structlog

from flare_ai_kit.prompts.library import PromptLibrary

logger = structlog.get_logger(__name__)


class PromptService:
    """
    Service class for managing AI prompt operations.

    This service provides a high-level interface for working with prompts,
    including formatting, error handling, and logging. It wraps the PromptLibrary
    class to provide additional functionality and safety checks.

    The service maintains its own structured logger instance for detailed
    operational logging and debugging.

    Attributes:
        library (PromptLibrary): Instance of the prompt library containing all
            prompt templates
        logger (BoundLogger): Structured logger bound with service context

    Example:
        ```python
        service = PromptService()
        try:
            prompt, mime_type, schema = service.get_formatted_prompt(
                "token_send", to_address="0x123...", amount=100
            )
        except Exception as e:
            print(f"Failed to format prompt: {e}")
        ```
    """

    def __init__(self) -> None:
        """
        Initialize a new PromptService instance.

        Creates a new PromptLibrary instance and initializes a bound logger
        with the service context.
        """
        self.library = PromptLibrary()
        self.logger = logger.bind(service="prompt")

    def get_formatted_prompt(
        self, prompt_name: str, **kwargs: Any
    ) -> tuple[str, str | None, type | None]:
        """
        Get a formatted prompt with its schema and mime type.

        Retrieves a prompt template by name, formats it with the provided
        parameters, and returns the formatted prompt along with its
        associated metadata.

        Args:
            prompt_name (str): Name of the prompt template to retrieve
            **kwargs (Any): Variable keyword arguments used to format
                the prompt template

        Returns:
            tuple[str, str | None, type | None]: A tuple containing:
                - formatted_prompt (str): The formatted prompt string
                - response_mime_type (str | None): MIME type for the expected response
                - response_schema (type | None): Type/schema for the expected response

        Raises:
            KeyError: If the requested prompt_name doesn't exist in the library
            ValueError: If required format parameters are missing
            Exception: For other formatting or processing errors

        Example:
            ```python
            service = PromptService()
            try:
                prompt, mime_type, schema = service.get_formatted_prompt(
                    "token_swap", from_token="ETH", to_token="USDC", amount=1.5
                )
            except KeyError:
                print("Prompt template not found")
            except ValueError:
                print("Missing required parameters")
            ```

        Logs:
            - Exceptions during prompt formatting with prompt name and error details
        """
        try:
            prompt = self.library.get_prompt(prompt_name)
            formatted = prompt.format(**kwargs)
        except Exception as e:
            self.logger.exception(
                "prompt_formatting_failed", prompt_name=prompt_name, error=str(e)
            )
            raise
        else:
            return (formatted, prompt.response_mime_type, prompt.response_schema)