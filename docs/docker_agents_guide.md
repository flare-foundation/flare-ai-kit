# Docker Agents Guide

This guide explains how to use the parametric Dockerfile to run agents from the `agents/` directory with specific dependency groups.

## Overview

The Dockerfile at the repository root is designed to be parametric, allowing you to:
- Install only the dependencies needed for specific functionality (via `EXTRAS`)
- Run any agent from the `agents/` directory (via `AGENT`)
- Keep images minimal and reproducible using `uv.lock`

## Build Arguments

### `EXTRAS`
Specifies which optional dependency groups to install. Available options:
- `pdf` - PDF processing (pillow, pymupdf, pytesseract)
- `rag` - Vector RAG (qdrant-client, dulwich)
- `a2a` - Agent-to-Agent communication (fastapi)
- `ftso` - FTSO price oracle functionality
- `da` - Data Availability layer functionality
- `fassets` - FAssets protocol functionality
- `social` - Social media integrations (telegram, twitter, etc.)
- `tee` - Trusted Execution Environment (cryptography, jwt)
- `wallet` - Wallet functionality (eth-account, cryptography)
- `ingestion` - General ingestion capabilities

### `AGENT`
Specifies which agents to run from the `agents/` directory. Default: `ingest_pdf.py`

## Basic Usage

### PDF Ingestion Agent

```bash
# Build the image for PDF processing
docker build -t fai-agent-pdf \
  --build-arg EXTRAS=pdf \
  --build-arg AGENT=ingest_pdf.py .

# Run the agent
docker run --rm -it \
  -v "$PWD/agents/data:/app/agents/data" \
  fai-agent-pdf
```

### With Environment Variables

```bash
# Run with environment variables for API keys and configuration
docker run --rm -it \
  -e AGENT__GEMINI_API_KEY="your_gemini_api_key" \
  -e ECOSYSTEM__WEB3_PROVIDER_URL="https://flare-api.flare.network/ext/C/rpc" \
  -e LOG_LEVEL="INFO" \
  -v "$PWD/agents/data:/app/agents/data" \
  fai-agent-pdf
```

### Using Environment File

```bash
# Create a .env file with your configuration
cat > .env.docker << EOF
AGENT__GEMINI_API_KEY=your_gemini_api_key
ECOSYSTEM__WEB3_PROVIDER_URL=https://flare-api.flare.network/ext/C/rpc
LOG_LEVEL=INFO
EOF

# Run with environment file
docker run --rm -it \
  --env-file .env.docker \
  -v "$PWD/agents/data:/app/agents/data" \
  fai-agent-pdf
```

## Advanced Usage

### Multiple Extras

```bash
# Build with multiple dependency groups
docker build -t fai-agent-multi \
  --build-arg EXTRAS="pdf,rag,a2a" \
  --build-arg AGENT=ingest_pdf.py .
```

### Custom agent

```bash
# Build for a custom agent (once you create more agents)
docker build -t fai-agent-custom \
  --build-arg EXTRAS=rag \
  --build-arg AGENT=my_custom_agent.py .
```

### Development Mode with Volume Mounts

```bash
# Mount the entire agents directory for development
docker run --rm -it \
  -v "$PWD/agents:/app/agents" \
  -v "$PWD/src:/app/src" \
  --env-file .env.docker \
  fai-agent-pdf
```

## Data Mounting

### PDF Data Directory

The PDF ingestion agent expects data in `/app/agents/data/`. Mount your local data:

```bash
# Mount local data directory
docker run --rm -it \
  -v "$PWD/my-pdfs:/app/agents/data" \
  fai-agent-pdf
```

### Persistent Output

```bash
# Mount output directory for persistent results
docker run --rm -it \
  -v "$PWD/agents/data:/app/agents/data" \
  -v "$PWD/output:/app/output" \
  fai-agent-pdf
```

## Environment Variables

### Required for PDF Processing
- `AGENT__GEMINI_API_KEY` - Google Gemini API key for AI processing

### Optional Configuration
- `LOG_LEVEL` - Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
- `ECOSYSTEM__WEB3_PROVIDER_URL` - Web3 provider URL for blockchain interactions
- `INGESTION__CHUNK_SIZE` - Text chunk size for processing (default: 5000)

### For Other Functionality
- `VECTOR_DB__QDRANT_URL` - Qdrant vector database URL (for RAG)
- `SOCIAL__TELEGRAM_API_TOKEN` - Telegram bot token (for social features)
- `TEE__SIMULATE_ATTESTATION_TOKEN` - Simulate TEE attestation (for testing)

## Native Package Dependencies

The Dockerfile includes native packages required for PDF processing:

### Included Packages
- `tesseract-ocr` - OCR engine for text extraction from images
- `tesseract-ocr-eng` - English language pack for Tesseract
- `poppler-utils` - PDF utilities for document processing

### Adding More Languages

To support additional languages for OCR, extend the Dockerfile:

```dockerfile
# Add more Tesseract language packs
RUN apt-get update && apt-get install -y --no-install-recommends \
    tesseract-ocr-fra \
    tesseract-ocr-deu \
    tesseract-ocr-spa \
    && rm -rf /var/lib/apt/lists/*
```

## Troubleshooting

### Script Not Found Error
```
Error: Script /app/agents/my_agent.py not found
```
Ensure your agent exists in the `agents/` directory and the filename matches the `AGENT` build arg.

### Missing Dependencies
```
ModuleNotFoundError: No module named 'qdrant_client'
```
Make sure you included the correct `EXTRAS` when building the image.

### Permission Issues
```
PermissionError: [Errno 13] Permission denied
```
Check that mounted volumes have correct permissions. The container runs as user `app` (non-root).

### OCR Issues
```
TesseractNotFoundError: tesseract is not installed
```
This shouldn't happen with the provided Dockerfile, but if it does, ensure Tesseract is properly installed in the image.

## Best Practices

1. **Use specific EXTRAS**: Only install the dependencies you need
2. **Environment files**: Use `.env` files for configuration instead of command-line args
3. **Volume mounts**: Mount only necessary directories to keep containers lightweight
4. **Non-root user**: The container runs as non-root user `app` for security
5. **Caching**: The Dockerfile is optimized for Docker layer caching

## Examples Repository

See the `agents/` directory for example agents:
- `ingest_pdf.py` - PDF ingestion and processing
- More agents will be added as the project grows

Each agent should be self-contained and follow the same pattern for consistency.