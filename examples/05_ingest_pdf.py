"""
Example of using the PDF ingestion and on-chain posting feature.

This script first generates a sample PDF and gets its exact data coordinates,
then processes the file to demonstrate a successful extraction.
"""

import asyncio
from unittest.mock import AsyncMock, mock_open, patch

from data.create_sample_invoice import create_invoice_and_get_coords

from flare_ai_kit import FlareAIKit
from flare_ai_kit.config import AppSettings

MOCK_TX_HASH = "0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef"


async def main() -> None:
    """Main function to run the PDF ingestion example with a real PDF."""
    # Step 1: Generate the sample PDF and get the exact coordinates
    print("📄 Generating sample_invoice.pdf and finding coordinates...")
    coords = create_invoice_and_get_coords()
    print("-" * 30)

    print("🚀 Starting PDF ingestion example...")

    # --- Configuration with programmatically found and CASTED coordinates ---
    settings = AppSettings(
        log_level="INFO",
        ingestion={
            "pdf_ingestion": {
                "templates": [
                    {
                        "template_name": "generated_invoice",
                        "fields": [
                            {
                                "field_name": "invoice_id",
                                "x0": int(coords["invoice_id"].x0),  # type: ignore[reportArgumentType]
                                "y0": int(coords["invoice_id"].y0),  # type: ignore[reportArgumentType]
                                "x1": int(coords["invoice_id"].x1),  # type: ignore[reportArgumentType]
                                "y1": int(coords["invoice_id"].y1),  # type: ignore[reportArgumentType]
                            },
                            {
                                "field_name": "issue_date",
                                "x0": int(coords["issue_date"].x0),  # type: ignore[reportArgumentType]
                                "y0": int(coords["issue_date"].y0),  # type: ignore[reportArgumentType]
                                "x1": int(coords["issue_date"].x1),  # type: ignore[reportArgumentType]
                                "y1": int(coords["issue_date"].y1),  # type: ignore[reportArgumentType]
                            },
                            {
                                "field_name": "amount_due",
                                "x0": int(coords["amount_due"].x0),  # type: ignore[reportArgumentType]
                                "y0": int(coords["amount_due"].y0),  # type: ignore[reportArgumentType]
                                "x1": int(coords["amount_due"].x1),  # type: ignore[reportArgumentType]
                                "y1": int(coords["amount_due"].y1),  # type: ignore[reportArgumentType]
                            },
                        ],
                    }
                ],
                "use_ocr": False,
                "contract_settings": {
                    "contract_address": "0x0000000000000000000000000000000000000000",
                    "abi_name": "OnchainDataRegistry",
                    "function_name": "registerDocument",
                },
            }
        },
    )

    # mock the blockchain and ABI file-opening parts.
    with (
        patch(
            "flare_ai_kit.onchain.contract_poster.ContractPoster.post_data",
            new_callable=AsyncMock,
            return_value=MOCK_TX_HASH,
        ) as mock_post_data,
        patch("flare_ai_kit.onchain.contract_poster.open", mock_open(read_data="[]")),
    ):
        kit = FlareAIKit(config=settings)

        tx_hash = await kit.pdf_processor.ingest_and_post(
            file_path="examples/data/sample_invoice.pdf",
            template_name="generated_invoice",
        )

        print("\n✅ Workflow executed successfully!")

        extracted_data = mock_post_data.call_args[0][0]
        print(f"   📄 REAL data extracted from PDF: {extracted_data}")
        print(f"   🔗 Mocked on-chain posting returned transaction hash: {tx_hash}")


if __name__ == "__main__":
    asyncio.run(main())
