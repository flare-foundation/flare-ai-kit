#!/bin/bash

# Exit immediately on non-zero status.
set -e

# --- Argument Parsing ---
PRINT_COMMAND=false
if [[ "$1" == "-v" || "$1" == "--verbose" ]]; then
  PRINT_COMMAND=true
fi

# --- Source Environment Variables ---
if [ -f .env ]; then
  echo "--> Sourcing variables from .env..."
  set -a # Automatically export all variables defined in the sourced file
  source .env
  set +a # Stop automatically exporting
else
  echo "--> INFO: .env file not found. Relying on variables already in the environment."
fi

# --- Variables ---
: "${GCP__INSTANCE_NAME:?Please set GCP__INSTANCE_NAME}"
: "${GCP__PROJECT:?Please set GCP__PROJECT}"
: "${GCP__ZONE:?Please set GCP__ZONE}"
: "${GCP__MACHINE_TYPE:?Please set GCP__MACHINE_TYPE}"
: "${GCP__TEE_IMAGE_REFERENCE:?Please set GCP__TEE_IMAGE_REFERENCE}"
: "${GCP__SERVICE_ACCOUNT:?Please set GCP__SERVICE_ACCOUNT}"
: "${GCP__IMAGE:?Please set GCP__IMAGE}"
: "${GCP__CONFIDENTIAL_COMPUTE_TYPE:?Please set GCP__CONFIDENTIAL_COMPUTE_TYPE}"
: "${GCP__SCOPES:?Please set GCP__SCOPES}"
: "${GCP__TAGS:?Please set GCP__TAGS}"
: "${GCP__TEE_CONTAINER_LOG_REDIRECT:?Please set GCP__TEE_CONTAINER_LOG_REDIRECT}"

echo "--> Creating instance '$GCP__INSTANCE_NAME' in project '$GCP__PROJECT' with the following settings:"
echo "      - Zone: $GCP__ZONE"
echo "      - Machine Type: $GCP__MACHINE_TYPE"
echo "      - Service Account: $GCP__SERVICE_ACCOUNT"
echo "      - Image: $GCP__IMAGE"
echo "      - TEE Image Reference: $GCP__TEE_IMAGE_REFERENCE"
echo "      - Confidential Compute Type: $GCP__CONFIDENTIAL_COMPUTE_TYPE"
echo "      - Scopes: $GCP__SCOPES"
echo "      - Tags: $GCP__TAGS"
echo "      - TEE Log Redirect: $GCP__TEE_CONTAINER_LOG_REDIRECT"

# --- Build TEE Environment Metadata ---
echo "--> Preparing TEE environment metadata from .env variables..."
PREFIX_PATTERN="^(AGENT__|ECOSYSTEM__|VECTOR_DB__|GRAPH_DB__|SOCIAL__|TEE__|INGESTION__)"
VAR_NAMES=$(printenv | grep -E "$PREFIX_PATTERN" | cut -d'=' -f1)
METADATA_VARS=""
if [ -n "$VAR_NAMES" ]; then
    echo "    Found the following variables for TEE:"
    for VAR_NAME in $VAR_NAMES; do
        # Indirect expansion: Get the VALUE of the variable whose NAME is in VAR_NAME.
        VAR_VALUE="${!VAR_NAME}"
        METADATA_VARS="${METADATA_VARS},tee-env-${VAR_NAME}=${VAR_VALUE}"

        # Display the variable being passed, but hide secrets.
        if [[ "$VAR_NAME" == *SECRET* || "$VAR_NAME" == *KEY* || "$VAR_NAME" == *TOKEN* ]]; then
            echo "      - ${VAR_NAME}=******"
        else
            echo "      - ${VAR_NAME}=${VAR_VALUE}"
        fi
    done
fi

# --- Build Command Array ---
COMMAND=(
  gcloud compute instances create "$GCP__INSTANCE_NAME"
  --project="$GCP__PROJECT"
  --zone="$GCP__ZONE"
  --machine-type="$GCP__MACHINE_TYPE"
  --network-interface=network-tier=PREMIUM,nic-type=GVNIC,stack-type=IPV4_ONLY,subnet=default
  --metadata="tee-image-reference=$GCP__TEE_IMAGE_REFERENCE,tee-container-log-redirect=$GCP__TEE_CONTAINER_LOG_REDIRECT${METADATA_VARS}"
  --maintenance-policy=TERMINATE
  --provisioning-model=STANDARD
  --service-account="$GCP__SERVICE_ACCOUNT"
  --scopes="$GCP__SCOPES"
  --tags="$GCP__TAGS"
  --create-disk=auto-delete=yes,boot=yes,device-name="$GCP__INSTANCE_NAME",image=projects/confidential-space-images/global/images/"$GCP__IMAGE",mode=rw,size=11,type=pd-balanced
  --shielded-secure-boot
  --shielded-vtpm
  --shielded-integrity-monitoring
  --reservation-affinity=any
  --confidential-compute-type="$GCP__CONFIDENTIAL_COMPUTE_TYPE"
)

# --- Confirmation ---

# Print the command in a readable multi-line format.
if [ "$PRINT_COMMAND" = true ]; then
  echo
  echo "The following command will be executed:"
  echo "----------------------------------------"
  printf "%s" "${COMMAND[0]}"
  for (( i=1; i<${#COMMAND[@]}; i++ )); do
      PART="${COMMAND[$i]}"
      if [[ "$PART" == --* ]]; then
          printf ' \\\n'
          printf '  %s' "$PART"
      else
          printf ' %s' "$PART"
      fi
  done
  printf '\n'
  echo "----------------------------------------"
fi

read -p "Do you want to continue? (y/N) " -n 1 -r
echo

if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Deployment cancelled by user."
    exit 1
fi

# --- Execute Command ---
echo "--> Proceeding with deployment..."
"${COMMAND[@]}"

echo "--> ✨ Instance '$GCP__INSTANCE_NAME' created successfully."