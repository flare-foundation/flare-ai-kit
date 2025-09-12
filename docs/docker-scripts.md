# Docker Scripts Guide

This guide explains how to use the parametric Dockerfile system to run Flare AI Kit scripts in isolated, reproducible containers.

## Overview

The Flare AI Kit provides a single, parametric Dockerfile that can build optimized images for different scripts. Each image contains only the dependencies needed for that specific script, keeping images lean and fast to build.

## Quick Start

### Using Make (Recommended)

```bash
# Run PDF ingestion script
make run-pdf-ingestion

# Run RAG vector demo
make run-rag-vector-demo

# Run FTSO price fetching
make run-ftso-price

# List all available scripts
make list-scripts

# Get help
make help
```

### Using Docker Directly

```bash
# Build image for PDF processing
docker build -t fai-script-pdf \
  --build-arg EXTRAS=pdf \
  --build-arg SCRIPT=pdf_ingestion .

# Run the PDF script
docker run --rm -it \
  --env-file .env \
  -v "$PWD/data:/app/scripts/data" \
  fai-script-pdf
```

## Available Scripts

| Script | Extras | Description |
|--------|--------|-------------|
| `ftso_price` | `ftso` | Fetch cryptocurrency prices from FTSO |
| `da_layer` | `da` | Data Availability Layer operations |
| `fassets_basic` | `fassets` | FAssets minting and redemption |
| `pdf_ingestion` | `pdf` | PDF processing and on-chain posting |
| `rag_vector_demo` | `rag` | RAG with vector embeddings |
| `a2a_collaboration` | `a2a` | Agent-to-Agent collaboration |
| `wallet_integration` | `wallet` | Turnkey wallet integration |

## Build Arguments

### EXTRAS

Comma-separated list of optional dependency groups to install:

- `ftso` - FTSO price oracle functionality (core deps only)
- `da` - Data Availability Layer (core deps only)  
- `fassets` - FAssets operations (core deps only)
- `pdf` - PDF processing (pillow, pymupdf, pytesseract)
- `rag` - RAG functionality (qdrant-client, dulwich)
- `a2a` - Agent-to-Agent communication (fastapi)
- `social` - Social media integrations (telegram, twitter, etc.)
- `tee` - Trusted Execution Environment (cryptography, jwt)
- `wallet` - Wallet integrations (eth-account, cryptography)

### SCRIPT

The script name to run (without .py extension):

- `ftso_price`
- `da_layer`
- `fassets_basic`
- `pdf_ingestion`
- `rag_vector_demo`
- `a2a_collaboration`
- `wallet_integration`

## Environment Variables

### Core Configuration

```bash
# Agent settings
AGENT__GEMINI_API_KEY=your_gemini_api_key
AGENT__GEMINI_MODEL=gemini-1.5-flash

# Ecosystem settings
ECOSYSTEM__FLARE_RPC_URL=https://flare-api.flare.network/ext/C/rpc
ECOSYSTEM__COSTON2_RPC_URL=https://coston2-api.flare.network/ext/C/rpc
```

### Script-Specific Variables

#### PDF Processing
```bash
INGESTION__PDF_INGESTION__USE_OCR=false
```

#### RAG Vector Demo
```bash
VECTOR_DB__QDRANT_URL=http://localhost:6333
VECTOR_DB__COLLECTION_NAME=flare_ai_kit
VECTOR_DB__EMBEDDINGS_MODEL=text-embedding-004
```

#### Wallet Integration
```bash
WALLET__TURNKEY_API_BASE_URL=https://api.turnkey.com
WALLET__TURNKEY_API_PUBLIC_KEY=your_public_key
WALLET__TURNKEY_API_PRIVATE_KEY=your_private_key
```

## Data Mounting

### Standard Data Directory

Mount your local data directory to `/app/scripts/data`:

```bash
docker run --rm -it \
  -v "$PWD/data:/app/scripts/data" \
  fai-script-pdf
```

### Demo Data

For scripts that generate temporary data:

```bash
docker run --rm -it \
  -v "$PWD/demo_data:/app/demo_data" \
  fai-script-rag
```

### Custom Mounts

```bash
# Mount specific directories
docker run --rm -it \
  -v "$PWD/pdfs:/app/input" \
  -v "$PWD/output:/app/output" \
  fai-script-pdf
```

## Native Package Dependencies

Some scripts require native system packages:

### PDF Processing (`pdf` extras)

Automatically installs:
- `tesseract-ocr` - OCR engine
- `tesseract-ocr-eng` - English language pack
- `poppler-utils` - PDF utilities
- `libgl1-mesa-glx` - OpenGL support
- `libglib2.0-0` - GLib library

### Custom Native Packages

To add custom native packages, extend the Dockerfile:

```dockerfile
# In runtime stage, after existing RUN apt-get update
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        your-custom-package \
        another-package && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*
```

## Advanced Usage

### Multiple Extras

```bash
# Build with multiple dependency groups
docker build -t fai-script-multi \
  --build-arg EXTRAS="pdf,rag,a2a" \
  --build-arg SCRIPT=pdf_ingestion .
```

### Development Mode

```bash
# Build development image with all extras
make dev-build

# Run with shell access and volume mounts
make dev-run
```

### Custom Registry

```bash
# Build and push to custom registry
DOCKER_REGISTRY=myregistry.com/ make build-pdf-ingestion

# Push to registry
docker push myregistry.com/fai-script-pdf-ingestion
```

## Troubleshooting

### Common Issues

1. **Script not found error**
   ```
   Error: Script 'scripts/my_script.py' not found!
   ```
   - Check script name spelling
   - Ensure script exists in `scripts/` directory

2. **Missing dependencies**
   ```
   ModuleNotFoundError: No module named 'qdrant_client'
   ```
   - Add required extras: `--build-arg EXTRAS=rag`

3. **Permission denied**
   ```
   PermissionError: [Errno 13] Permission denied
   ```
   - Check volume mount permissions
   - Ensure data directory is writable

### Debug Mode

```bash
# Run with shell access for debugging
docker run --rm -it \
  --env-file .env \
  -v "$PWD/data:/app/scripts/data" \
  --entrypoint /bin/bash \
  fai-script-pdf

# Inside container, run script manually
python /app/scripts/pdf_ingestion.py
```

### Logs and Monitoring

```bash
# View container logs
docker logs <container_id>

# Run with verbose output
docker run --rm -it \
  -e LOG_LEVEL=DEBUG \
  fai-script-pdf
```

## Best Practices

1. **Use .env files** for configuration management
2. **Mount data directories** for persistent storage
3. **Use specific extras** to minimize image size
4. **Pin image versions** in production
5. **Use multi-stage builds** for optimization
6. **Clean up images** regularly with `make clean`

## Examples

See the `scripts/` directory for complete examples of each script type.
