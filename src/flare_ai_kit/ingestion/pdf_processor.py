"""Processes PDF files to extract data and post it to a smart contract."""

import fitz  # type: ignore # PyMuPDF
import pytesseract  # type: ignore
from PIL import Image
from typing import Dict, Any, Type
import structlog
from pydantic import BaseModel, create_model, ValidationError

from flare_ai_kit.ingestion.settings import (
    PDFTemplateSettings,
    PDFIngestionSettings,
)
from flare_ai_kit.onchain.contract_poster import ContractPoster

logger = structlog.get_logger(__name__)


# A mapping from data_type strings in the settings to actual Python types
TYPE_MAP: dict[str, type] = {"string": str, "integer": int, "float": float}


def _create_dynamic_model(template: PDFTemplateSettings) -> Type[BaseModel]:
    """Dynamically creates a Pydantic model from a PDF template."""
    # Create a dictionary of field definitions for Pydantic
    fields = {
        field.field_name: (TYPE_MAP.get(field.data_type, str), ...)
        for field in template.fields
    }
    # Use Pydantic's create_model function to build the class
    return create_model(f"{template.template_name}Model", **fields)  # type: ignore


class PDFProcessor:
    """
    A class to process PDF files, extract data based on templates,
    and post it to a smart contract.
    """

    def __init__(self, settings: PDFIngestionSettings, contract_poster: ContractPoster):
        """
        Initializes the PDFProcessor.

        Args:
            settings: The settings for PDF ingestion.
            contract_poster: An instance of the ContractPoster to handle on-chain transactions.
        """
        self.settings = settings
        self.contract_poster = contract_poster
        self.templates = {
            template.template_name: template for template in settings.templates
        }

    def _extract_text_from_area(
        self, page: fitz.Page, rect: fitz.Rect, use_ocr: bool
    ) -> str:
        """
        Extracts text from a specified area of a page.

        Args:
            page: The page to extract text from.
            rect: The rectangular area to extract text from.
            use_ocr: Whether to use OCR for text extraction.

        Returns:
            The extracted text.
        """
        if use_ocr:
            pix = page.get_pixmap(clip=rect)  # type: ignore
            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)  # type: ignore
            return str(pytesseract.image_to_string(img).strip())  # type: ignore
        else:
            return str(page.get_text("text", clip=rect).strip())  # type: ignore

    def process_pdf(self, file_path: str, template_name: str) -> Dict[str, Any]:
        """
        Processes a PDF file using a specified template.

        Args:
            file_path: The path to the PDF file.
            template_name: The name of the template to use.

        Returns:
            A dictionary of the extracted data.

        Raises:
            ValueError: If the template is not found or the PDF cannot be processed.
        """
        if template_name not in self.templates:
            raise ValueError(f"Template '{template_name}' not found.")

        template: PDFTemplateSettings = self.templates[template_name]
        extracted_data = {}

        try:
            doc = fitz.open(file_path)
            page = doc[0]  # Assuming single-page documents for now

            for field_settings in template.fields:
                rect = fitz.Rect(
                    field_settings.x0,
                    field_settings.y0,
                    field_settings.x1,
                    field_settings.y1,
                )
                text = self._extract_text_from_area(page, rect, self.settings.use_ocr)
                extracted_data[field_settings.field_name] = text

            doc.close()

            # Validate and normalize data
            DynamicPDFModel = _create_dynamic_model(template)
            pdf_data = DynamicPDFModel(**extracted_data)  # type: ignore
            return pdf_data.model_dump()

        except (IOError, fitz.FileDataError) as e:
            logger.error(
                "Failed to open or process PDF", file_path=file_path, error=str(e)
            )
            raise ValueError(f"Could not process PDF file: {file_path}") from e
        except ValidationError as e:
            logger.error(
                "Extracted data failed validation",
                extracted_data=extracted_data,
                error=str(e),
            )
            raise ValueError("Extracted data is invalid") from e

    async def ingest_and_post(self, file_path: str, template_name: str) -> str:
        """
        Ingests a PDF, extracts data, and posts it to the smart contract.

        Args:
            file_path: The path to the PDF file.
            template_name: The name of the template to use.

        Returns:
            The transaction hash of the on-chain transaction.
        """
        logger.info(
            "Starting PDF ingestion and posting",
            file_path=file_path,
            template=template_name,
        )
        try:
            extracted_data = self.process_pdf(file_path, template_name)
            tx_hash = await self.contract_poster.post_data(extracted_data)
            logger.info("Successfully ingested and posted PDF data", tx_hash=tx_hash)
            if not tx_hash:
                raise ValueError("Transaction failed to return a hash.")
            return tx_hash
        except (ValueError, Exception) as e:
            logger.exception("PDF ingestion and posting failed", error=str(e))
            raise
