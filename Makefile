# Flare AI Kit - Docker Agents Makefile
# Provides convenient targets for building and running Docker agents

.PHONY: help build-pdf run-pdf build-rag run-rag build-a2a run-a2a build-multi run-multi clean-images list-images

# Default target
help: ## Show this help message
	@echo "Flare AI Kit - Docker Agents"
	@echo "============================="
	@echo ""
	@echo "Available targets:"
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "  %-20s %s\n", $$1, $$2}' $(MAKEFILE_LIST)
	@echo ""
	@echo "Environment variables:"
	@echo "  DATA_DIR     - Local directory to mount as /app/agents/data (default: ./agents/data)"
	@echo "  ENV_FILE     - Environment file to use (default: .env)"
	@echo "  DOCKER_OPTS  - Additional docker run options"
	@echo ""
	@echo "Examples:"
	@echo "  make run-pdf DATA_DIR=./my-pdfs"
	@echo "  make run-pdf ENV_FILE=.env.production"
	@echo "  make run-pdf DOCKER_OPTS='--rm -it'"

# Configuration
DATA_DIR ?= ./agents/data
ENV_FILE ?= .env
DOCKER_OPTS ?= --rm -it

# PDF Processing
build-pdf: ## Build Docker image for PDF processing
	@echo "Building PDF processing image..."
	docker build \
		--build-arg EXTRAS=pdf \
		--build-arg AGENT=ingest_pdf.py \
		--tag fai-agent-pdf \
		.
	@echo "✅ PDF image built: fai-agent-pdf"

run-pdf: build-pdf ## Build and run PDF processing agent
	@echo "Running PDF processing agent..."
	@if [ ! -f "$(ENV_FILE)" ]; then \
		echo "⚠️  Environment file $(ENV_FILE) not found. Creating example..."; \
		echo "AGENT__GEMINI_API_KEY=your_gemini_api_key_here" > $(ENV_FILE).example; \
		echo "LOG_LEVEL=INFO" >> $(ENV_FILE).example; \
		echo "Please copy $(ENV_FILE).example to $(ENV_FILE) and configure your API keys"; \
		exit 1; \
	fi
	@mkdir -p $(DATA_DIR)
	docker run $(DOCKER_OPTS) \
		--env-file $(ENV_FILE) \
		-v "$(shell pwd)/$(DATA_DIR):/app/agents/data" \
		fai-agent-pdf

# RAG Processing
build-rag: ## Build Docker image for RAG processing
	@echo "Building RAG processing image..."
	docker build \
		--build-arg EXTRAS=rag \
		--build-arg AGENT=ingest_pdf.py \
		--tag fai-agent-rag \
		.
	@echo "✅ RAG image built: fai-agent-rag"

run-rag: build-rag ## Build and run RAG processing agent
	@echo "Running RAG processing agent..."
	@if [ ! -f "$(ENV_FILE)" ]; then \
		echo "⚠️  Environment file $(ENV_FILE) not found"; \
		exit 1; \
	fi
	@mkdir -p $(DATA_DIR)
	docker run $(DOCKER_OPTS) \
		--env-file $(ENV_FILE) \
		-v "$(shell pwd)/$(DATA_DIR):/app/agents/data" \
		fai-agent-rag

# A2A Processing
build-a2a: ## Build Docker image for A2A processing
	@echo "Building A2A processing image..."
	docker build \
		--build-arg EXTRAS=a2a \
		--build-arg AGENT=ingest_pdf.py \
		--tag fai-agent-a2a \
		.
	@echo "✅ A2A image built: fai-agent-a2a"

run-a2a: build-a2a ## Build and run A2A processing agent
	@echo "Running A2A processing agent..."
	@if [ ! -f "$(ENV_FILE)" ]; then \
		echo "⚠️  Environment file $(ENV_FILE) not found"; \
		exit 1; \
	fi
	@mkdir -p $(DATA_DIR)
	docker run $(DOCKER_OPTS) \
		--env-file $(ENV_FILE) \
		-v "$(shell pwd)/$(DATA_DIR):/app/agents/data" \
		fai-agent-a2a

# Multi-functionality build
build-multi: ## Build Docker image with multiple extras (pdf,rag,a2a)
	@echo "Building multi-functionality image..."
	docker build \
		--build-arg EXTRAS=pdf,rag,a2a \
		--build-arg AGENT=ingest_pdf.py \
		--tag fai-agent-multi \
		.
	@echo "✅ Multi image built: fai-agent-multi"

run-multi: build-multi ## Build and run multi-functionality agent
	@echo "Running multi-functionality agent..."
	@if [ ! -f "$(ENV_FILE)" ]; then \
		echo "⚠️  Environment file $(ENV_FILE) not found"; \
		exit 1; \
	fi
	@mkdir -p $(DATA_DIR)
	docker run $(DOCKER_OPTS) \
		--env-file $(ENV_FILE) \
		-v "$(shell pwd)/$(DATA_DIR):/app/agents/data" \
		fai-agent-multi

# Custom builds
build-custom: ## Build custom image (use EXTRAS and AGENT env vars)
	@if [ -z "$(EXTRAS)" ]; then \
		echo "❌ EXTRAS environment variable is required"; \
		echo "Usage: make build-custom EXTRAS=pdf,rag AGENT=my_agent.py"; \
		exit 1; \
	fi
	@if [ -z "$(AGENT)" ]; then \
		echo "❌ AGENT environment variable is required"; \
		echo "Usage: make build-custom EXTRAS=pdf,rag AGENT=my_agent.py"; \
		exit 1; \
	fi
	@echo "Building custom image with EXTRAS=$(EXTRAS) AGENT=$(AGENT)..."
	docker build \
		--build-arg EXTRAS=$(EXTRAS) \
		--build-arg AGENT=$(AGENT) \
		--tag fai-agent-custom \
		.
	@echo "✅ Custom image built: fai-agent-custom"

run-custom: build-custom ## Build and run custom agent (use EXTRAS and AGENT env vars)
	@echo "Running custom agent..."
	@if [ ! -f "$(ENV_FILE)" ]; then \
		echo "⚠️  Environment file $(ENV_FILE) not found"; \
		exit 1; \
	fi
	@mkdir -p $(DATA_DIR)
	docker run $(DOCKER_OPTS) \
		--env-file $(ENV_FILE) \
		-v "$(shell pwd)/$(DATA_DIR):/app/agents/data" \
		fai-agent-custom

# Development helpers
dev-shell: build-pdf ## Start interactive shell in PDF container for development
	@echo "Starting development shell..."
	@mkdir -p $(DATA_DIR)
	docker run $(DOCKER_OPTS) \
		--env-file $(ENV_FILE) \
		-v "$(shell pwd)/agents:/app/agents" \
		-v "$(shell pwd)/src:/app/src" \
		-v "$(shell pwd)/$(DATA_DIR):/app/agents/data" \
		--entrypoint /bin/bash \
		fai-agent-pdf

# Utility targets
list-images: ## List all fai-agent Docker images
	@echo "Flare AI Kit agent images:"
	@docker images --filter "reference=fai-agent-*" --format "table {{.Repository}}\t{{.Tag}}\t{{.Size}}\t{{.CreatedAt}}"

clean-images: ## Remove all fai-agent Docker images
	@echo "Removing all fai-agent images..."
	@docker images --filter "reference=fai-agent-*" -q | xargs -r docker rmi -f
	@echo "✅ Cleaned up fai-agent images"

# Test targets
test-build: ## Test building all main image variants
	@echo "Testing all main builds..."
	@make build-pdf
	@make build-rag  
	@make build-a2a
	@make build-multi
	@echo "✅ All builds completed successfully"

# Environment setup
setup-env: ## Create example environment file
	@if [ -f "$(ENV_FILE)" ]; then \
		echo "⚠️  $(ENV_FILE) already exists"; \
	else \
		echo "Creating example environment file: $(ENV_FILE)"; \
		echo "# Flare AI Kit Configuration" > $(ENV_FILE); \
		echo "LOG_LEVEL=INFO" >> $(ENV_FILE); \
		echo "" >> $(ENV_FILE); \
		echo "# AI Agent Configuration" >> $(ENV_FILE); \
		echo "AGENT__GEMINI_API_KEY=your_gemini_api_key_here" >> $(ENV_FILE); \
		echo "AGENT__GEMINI_MODEL=gemini-2.0-flash" >> $(ENV_FILE); \
		echo "" >> $(ENV_FILE); \
		echo "# Blockchain Configuration" >> $(ENV_FILE); \
		echo "ECOSYSTEM__WEB3_PROVIDER_URL=https://flare-api.flare.network/ext/C/rpc" >> $(ENV_FILE); \
		echo "" >> $(ENV_FILE); \
		echo "# Processing Configuration" >> $(ENV_FILE); \
		echo "INGESTION__CHUNK_SIZE=5000" >> $(ENV_FILE); \
		echo "" >> $(ENV_FILE); \
		echo "# Testing Configuration" >> $(ENV_FILE); \
		echo "TEE__SIMULATE_ATTESTATION_TOKEN=true" >> $(ENV_FILE); \
		echo "✅ Created $(ENV_FILE) - please configure your API keys"; \
	fi

# Quick start
quick-start: setup-env run-pdf ## Quick start: setup environment and run PDF agent