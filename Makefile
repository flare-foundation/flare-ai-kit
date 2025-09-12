# Flare AI Kit - Parametric Docker Scripts Makefile
# 
# This Makefile provides convenient targets for building and running
# different scripts with their required dependencies using Docker.
#
# Usage:
#   make build-<script>  # Build image for specific script
#   make run-<script>    # Build and run script
#   make help           # Show available targets

.PHONY: help build-all clean list-scripts

# Default target
help:
	@echo "Flare AI Kit - Docker Scripts"
	@echo "============================="
	@echo ""
	@echo "Available targets:"
	@echo "  build-<script>    Build Docker image for specific script"
	@echo "  run-<script>      Build and run script in container"
	@echo "  build-all         Build all script images"
	@echo "  list-scripts      List available scripts"
	@echo "  clean            Remove all script images"
	@echo "  help             Show this help message"
	@echo ""
	@echo "Available scripts:"
	@echo "  ftso-price        Fetch FTSO price data (extras: ftso)"
	@echo "  da-layer          Data Availability Layer demo (extras: da)"
	@echo "  fassets-basic     FAssets operations (extras: fassets)"
	@echo "  pdf-ingestion     PDF processing and ingestion (extras: pdf)"
	@echo "  rag-vector-demo   RAG with vector embeddings (extras: rag)"
	@echo "  a2a-collaboration Agent-to-Agent collaboration (extras: a2a)"
	@echo "  wallet-integration Turnkey wallet integration (extras: wallet)"
	@echo ""
	@echo "Examples:"
	@echo "  make run-pdf-ingestion"
	@echo "  make build-rag-vector-demo"
	@echo "  make run-ftso-price ENV_FILE=.env.production"

# Variables
DOCKER_REGISTRY ?= 
IMAGE_PREFIX ?= fai-script
ENV_FILE ?= .env

# Script definitions with their required extras
SCRIPTS := \
	ftso-price:ftso:ftso_price \
	da-layer:da:da_layer \
	fassets-basic:fassets:fassets_basic \
	pdf-ingestion:pdf:pdf_ingestion \
	rag-vector-demo:rag:rag_vector_demo \
	a2a-collaboration:a2a:a2a_collaboration \
	wallet-integration:wallet:wallet_integration

# Extract script names for pattern rules
SCRIPT_NAMES := $(foreach script,$(SCRIPTS),$(word 1,$(subst :, ,$(script))))

# List available scripts
list-scripts:
	@echo "Available scripts:"
	@$(foreach script,$(SCRIPTS), \
		echo "  $(word 1,$(subst :, ,$(script))) (extras: $(word 2,$(subst :, ,$(script))))";)

# Build all script images
build-all: $(addprefix build-,$(SCRIPT_NAMES))

# Clean all script images
clean:
	@echo "Removing all script images..."
	@docker images --format "table {{.Repository}}:{{.Tag}}" | grep "^$(IMAGE_PREFIX)-" | xargs -r docker rmi -f
	@echo "Cleanup complete"

# Generic build rule for scripts
define BUILD_SCRIPT_RULE
build-$(1): 
	@echo "Building $(IMAGE_PREFIX)-$(1) with extras: $(2)"
	docker build \
		--build-arg EXTRAS="$(2)" \
		--build-arg SCRIPT="$(3)" \
		-t $(DOCKER_REGISTRY)$(IMAGE_PREFIX)-$(1) \
		.
	@echo "✅ Built $(IMAGE_PREFIX)-$(1)"
endef

# Generic run rule for scripts  
define RUN_SCRIPT_RULE
run-$(1): build-$(1)
	@echo "Running $(1) script..."
	@if [ -f "$(ENV_FILE)" ]; then \
		echo "Using environment file: $(ENV_FILE)"; \
		docker run --rm -it \
			--env-file $(ENV_FILE) \
			-v "$$(pwd)/data:/app/scripts/data" \
			-v "$$(pwd)/demo_data:/app/demo_data" \
			$(DOCKER_REGISTRY)$(IMAGE_PREFIX)-$(1); \
	else \
		echo "Warning: $(ENV_FILE) not found, running without env file"; \
		docker run --rm -it \
			-v "$$(pwd)/data:/app/scripts/data" \
			-v "$$(pwd)/demo_data:/app/demo_data" \
			$(DOCKER_REGISTRY)$(IMAGE_PREFIX)-$(1); \
	fi
endef

# Generate rules for each script
$(foreach script,$(SCRIPTS), \
	$(eval $(call BUILD_SCRIPT_RULE,$(word 1,$(subst :, ,$(script))),$(word 2,$(subst :, ,$(script))),$(word 3,$(subst :, ,$(script))))))

$(foreach script,$(SCRIPTS), \
	$(eval $(call RUN_SCRIPT_RULE,$(word 1,$(subst :, ,$(script))))))

# Special targets with common variations
.PHONY: run-pdf run-rag run-a2a run-ftso

# Aliases for common scripts
run-pdf: run-pdf-ingestion
run-rag: run-rag-vector-demo  
run-a2a: run-a2a-collaboration
run-ftso: run-ftso-price

# Development targets
.PHONY: dev-build dev-run

# Build development image with all extras
dev-build:
	@echo "Building development image with all extras..."
	docker build \
		--build-arg EXTRAS="pdf,rag,a2a,social,tee,wallet" \
		--build-arg SCRIPT="ftso_price" \
		-t $(IMAGE_PREFIX)-dev \
		.

# Run development container with shell access
dev-run: dev-build
	@echo "Starting development container..."
	docker run --rm -it \
		--env-file $(ENV_FILE) \
		-v "$$(pwd)/data:/app/scripts/data" \
		-v "$$(pwd)/scripts:/app/scripts" \
		-v "$$(pwd)/src:/app/src" \
		--entrypoint /bin/bash \
		$(IMAGE_PREFIX)-dev

# Docker compose targets (if docker-compose.yml exists)
.PHONY: compose-up compose-down

compose-up:
	@if [ -f "docker-compose.yml" ]; then \
		docker-compose up -d; \
	else \
		echo "docker-compose.yml not found"; \
	fi

compose-down:
	@if [ -f "docker-compose.yml" ]; then \
		docker-compose down; \
	else \
		echo "docker-compose.yml not found"; \
	fi
