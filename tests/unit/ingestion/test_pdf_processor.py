from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from pydantic import BaseModel

from flare_ai_kit.common import PdfPostingError
from flare_ai_kit.ingestion.pdf_processor import (
    PDFProcessor,
    _create_dynamic_model,
)


@pytest.fixture
def sample_template():
    return SimpleNamespace(
        template_name="Invoice",
        fields=[
            SimpleNamespace(
                field_name="name",
                data_type="string",
                x0=0,
                y0=0,
                x1=10,
                y1=10,
            )
        ],
    )


@pytest.fixture
def pdf_settings(sample_template):
    return SimpleNamespace(templates=[sample_template], use_ocr=False)


def test_create_dynamic_model_builds_correct_fields():
    template = SimpleNamespace(
        template_name="Invoice",
        fields=[
            SimpleNamespace(field_name="name", data_type="string"),
            SimpleNamespace(field_name="amount", data_type="float"),
        ],
    )
    model_cls = _create_dynamic_model(template)
    obj = model_cls(name="Alice", amount=12.5)

    assert isinstance(obj, BaseModel)
    assert obj.name == "Alice"
    assert isinstance(obj.amount, float)


def _make_fake_doc(mock_page):
    """Helper to simulate a fitz Document."""
    fake_doc = MagicMock()
    fake_doc.__getitem__.side_effect = lambda idx: mock_page if idx == 0 else None
    fake_doc.close.return_value = None
    return fake_doc


@patch("flare_ai_kit.ingestion.pdf_processor.fitz.open")
def test_process_pdf_success(mock_open, pdf_settings):
    mock_page = MagicMock()
    mock_page.get_text.return_value = "Alice"
    mock_open.return_value = _make_fake_doc(mock_page)

    processor = PDFProcessor(pdf_settings, contract_poster=MagicMock())
    result = processor.process_pdf("dummy.pdf", "Invoice")

    assert result["name"] == "Alice"
    mock_open.assert_called_once_with("dummy.pdf")


def test_process_pdf_template_not_found():
    settings = SimpleNamespace(templates=[], use_ocr=False)
    processor = PDFProcessor(settings, MagicMock())
    with pytest.raises(ValueError, match="Template 'Missing' not found"):
        processor.process_pdf("dummy.pdf", "Missing")


@patch("flare_ai_kit.ingestion.pdf_processor.fitz.open")
def test_process_pdf_validation_error(mock_open, pdf_settings):
    bad_template = SimpleNamespace(
        template_name="Invoice",
        fields=[
            SimpleNamespace(
                field_name="amount",
                data_type="float",
                x0=0,
                y0=0,
                x1=10,
                y1=10,
            )
        ],
    )
    settings = SimpleNamespace(templates=[bad_template], use_ocr=False)

    mock_page = MagicMock()
    mock_page.get_text.return_value = "not_a_float"
    mock_open.return_value = _make_fake_doc(mock_page)

    processor = PDFProcessor(settings, MagicMock())
    with pytest.raises(ValueError, match="Extracted data is invalid"):
        processor.process_pdf("dummy.pdf", "Invoice")


@pytest.mark.asyncio
async def test_ingest_and_post_success(pdf_settings):
    processor = PDFProcessor(pdf_settings, contract_poster=AsyncMock())
    processor.process_pdf = MagicMock(return_value={"name": "Alice"})
    processor.contract_poster.post_data.return_value = "0xABC"

    tx_hash = await processor.ingest_and_post("file.pdf", "Invoice")

    assert tx_hash == "0xABC"
    processor.process_pdf.assert_called_once_with("file.pdf", "Invoice")
    processor.contract_poster.post_data.assert_called_once_with({"name": "Alice"})


@pytest.mark.asyncio
async def test_ingest_and_post_failure(pdf_settings):
    processor = PDFProcessor(pdf_settings, contract_poster=AsyncMock())
    processor.process_pdf = MagicMock(return_value={"name": "Alice"})
    processor.contract_poster.post_data.return_value = None

    with pytest.raises(PdfPostingError):
        await processor.ingest_and_post("file.pdf", "Invoice")
