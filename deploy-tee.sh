#!/bin/bash

# ==============================================================================
# TEE BUILD & DEPLOY SCRIPT
# 1. Builds the image using Docker
# 2. Pushes the built image to Artifacts Registry
# 3. Sets up a new GCP Confidential Space instance from the image
# ==============================================================================

set -e # Exit immediately if any command fails

# --- 1. Helper Functions ---
log_info() { echo -e "\033[1;34m[INFO]\033[0m $1"; }
log_warn() { echo -e "\033[1;33m[WARN]\033[0m $1"; }
log_succ() { echo -e "\033[1;32m[SUCCESS]\033[0m $1"; }
log_err()  { echo -e "\033[1;31m[ERROR]\033[0m $1"; }

usage() {
    echo "Usage: $0 [options]"
    echo "Options:"
    echo "  --agent <name>    Python agent to ingest (default: ingest_pdf.py)"
    echo "  --extras <name>   Suffix for image tag (default: pdf)"
    echo "  --skip-build      Skip Docker build/push, only deploy infrastructure"
    echo "  --skip-deploy     Skip infrastructure deploy, only build Docker"
    echo "  --force-yes       Skip all confirmation prompts"
    echo "  --help            Show this message"
    exit 1
}

# --- 2. Defaults & Argument Parsing ---
AGENT="ingest_pdf.py"
EXTRAS="pdf"
DO_BUILD=true
DO_DEPLOY=true
FORCE_YES=false

while [[ "$#" -gt 0 ]]; do
    case $1 in
        --agent) AGENT="$2"; shift ;;
        --extras) EXTRAS="$2"; shift ;;
        --skip-build) DO_BUILD=false ;;
        --skip-deploy) DO_DEPLOY=false ;;
        --force-yes) FORCE_YES=true ;;
        --help) usage ;;
        *) echo "Unknown parameter: $1"; usage ;;
    esac
    shift
done

# --- 3. Load Environment ---
if [ -f .env ]; then
    log_info "Sourcing .env file..."
    set -a; source .env; set +a
else
    log_err ".env file not found! Exiting."
    exit 1
fi

# Ensure mandatory variable exists initially
: "${GCP__TEE_IMAGE_REFERENCE:?Please set GCP__TEE_IMAGE_REFERENCE in .env}"

# --- 4. Dynamic Image Tag Calculation ---
# Get the repository base
# e.g., us-central1.../flare-ai-kit/fai-agent-pdf:latest -> us-central1.../flare-ai-kit
REPO_BASE=$(echo "$GCP__TEE_IMAGE_REFERENCE" | sed 's|\(.*\)/.*|\1|')

# Construct the specific target image
TARGET_IMAGE="${REPO_BASE}/fai-agent-${EXTRAS}:latest"

log_info "Configuration:"
echo "   Agent: $AGENT"
echo "   Extras: $EXTRAS"
echo "   Target Image: $TARGET_IMAGE"

# Overwrite the environment variable in memory so the Deploy step uses the correct image
GCP__TEE_IMAGE_REFERENCE="$TARGET_IMAGE"


# ==============================================================================
# PHASE 1: DOCKER BUILD & PUSH
# ==============================================================================
if [ "$DO_BUILD" = true ]; then
    log_info "Starting Build Phase..."

    # Extract keys for ALLOWED_ENVS
    KEYS=$(grep -E '^[A-Z]' .env | cut -d= -f1 | paste -sd, -)
    
    echo "   Building Docker image..."
    docker build -t "$TARGET_IMAGE" \
        --platform linux/amd64 \
        --build-arg AGENT="$AGENT" \
        --build-arg EXTRAS="$EXTRAS" \
        --build-arg ALLOWED_ENVS="LOG_LEVEL,${KEYS}" .
    
    echo "   Pushing to Artifact Registry..."
    docker push "$TARGET_IMAGE"
    log_succ "Build and Push Complete."
else
    log_info "Skipping Build Phase."
fi


# ==============================================================================
# PHASE 2: INFRASTRUCTURE DEPLOYMENT
# ==============================================================================
if [ "$DO_DEPLOY" = true ]; then
    log_info "Starting Deployment Phase..."

    # Validate Deployment Variables
    : "${GCP__INSTANCE_NAME:?Set GCP__INSTANCE_NAME}"
    : "${GCP__PROJECT:?Set GCP__PROJECT}"
    : "${GCP__ZONE:?Set GCP__ZONE}"
    : "${GCP__MACHINE_TYPE:?Set GCP__MACHINE_TYPE}"
    : "${GCP__SERVICE_ACCOUNT:?Set GCP__SERVICE_ACCOUNT}"
    : "${GCP__CONFIDENTIAL_IMAGE:?Set GCP__CONFIDENTIAL_IMAGE}"
    : "${GCP__CONFIDENTIAL_COMPUTE_TYPE:?Set GCP__CONFIDENTIAL_COMPUTE_TYPE}"

    # Check for Existing Instance
    if gcloud compute instances describe "$GCP__INSTANCE_NAME" \
        --project="$GCP__PROJECT" --zone="$GCP__ZONE" --format="json" >/dev/null 2>&1; then
        
        log_warn "Instance '$GCP__INSTANCE_NAME' already exists."
        
        if [ "$FORCE_YES" = true ]; then
            REPLY="y"
        else
            read -p "   Do you want to delete and redeploy? (y/N) " -n 1 -r
            echo
        fi

        if [[ $REPLY =~ ^[Yy]$ ]]; then
            log_info "Deleting instance..."
            gcloud compute instances delete "$GCP__INSTANCE_NAME" \
                --project="$GCP__PROJECT" --zone="$GCP__ZONE" --quiet
        else
            log_err "Deployment cancelled by user."
            exit 1
        fi
    fi

    # Prepare TEE Metadata Variables
    PREFIX_PATTERN="^(AGENT__|ECOSYSTEM__|VECTOR_DB__|GRAPH_DB__|SOCIAL__|TEE__|INGESTION__|LOG_LEVEL|APP_ENV)"
    VAR_NAMES=$(printenv | grep -E "$PREFIX_PATTERN" | cut -d'=' -f1)
    METADATA_VARS=""
    
    if [ -n "$VAR_NAMES" ]; then
        for VAR_NAME in $VAR_NAMES; do
            VAR_VALUE="${!VAR_NAME}"
            # Pass both standard and Flare-specific env prefixes
            METADATA_VARS="${METADATA_VARS},tee-env-${VAR_NAME}=${VAR_VALUE},stee-env-${VAR_NAME}=${VAR_VALUE}"
        done
    fi

    # Construct GCloud Command
    COMMAND=(
      gcloud compute instances create "$GCP__INSTANCE_NAME"
      --project="$GCP__PROJECT"
      --zone="$GCP__ZONE"
      --machine-type="$GCP__MACHINE_TYPE"
      --network-interface=network-tier=PREMIUM,nic-type=GVNIC,stack-type=IPV4_ONLY,subnet=default
      --metadata="tee-image-reference=$GCP__TEE_IMAGE_REFERENCE,stee-image-reference=$GCP__TEE_IMAGE_REFERENCE,stee-container-log-redirect=$GCP__TEE_CONTAINER_LOG_REDIRECT,tee-container-log-redirect=$GCP__TEE_CONTAINER_LOG_REDIRECT${METADATA_VARS}"
      --maintenance-policy=TERMINATE
      --provisioning-model=STANDARD
      --service-account="$GCP__SERVICE_ACCOUNT"
      --scopes="$GCP__SCOPES"
      --tags="$GCP__TAGS"
      --create-disk=auto-delete=yes,boot=yes,device-name="$GCP__INSTANCE_NAME",image=projects/confidential-space-images/global/images/"$GCP__CONFIDENTIAL_IMAGE",mode=rw,size=20,type=pd-balanced
      --shielded-secure-boot
      --shielded-vtpm
      --shielded-integrity-monitoring
      --reservation-affinity=any
      --confidential-compute-type="$GCP__CONFIDENTIAL_COMPUTE_TYPE"
    )

    log_info "Deploying instance using image: $GCP__TEE_IMAGE_REFERENCE"
    
    if [ "$FORCE_YES" != true ]; then
        read -p "   Ready to deploy. Continue? (y/N) " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            log_err "Cancelled."
            exit 1
        fi
    fi

    "${COMMAND[@]}"
    log_succ "Instance '$GCP__INSTANCE_NAME' deployed successfully."
else
    log_info "Skipping Deployment Phase."
fi