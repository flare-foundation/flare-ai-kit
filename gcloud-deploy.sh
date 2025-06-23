#!/bin/bash

# Exit immediately if a command exits with a non-zero status.
set -e

# --- Source Environment Variables ---
# Check if a .env file exists and source it if it does.
if [ -f .env ]; then
  echo "--> Sourcing variables from .env file..."
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

echo "--> Creating instance '$GCP__INSTANCE_NAME' in project '$GCP__PROJECT' with the following settings:"
echo "    Zone: $GCP__ZONE"
echo "    Machine Type: $GCP__MACHINE_TYPE"
echo "    Service Account: $GCP__SERVICE_ACCOUNT"
echo "    Image: $GCP__IMAGE"
echo "    TEE Image Reference: $GCP__TEE_IMAGE_REFERENCE"
echo "    Confidential Compute Type: $GCP__CONFIDENTIAL_COMPUTE_TYPE"

# --- Command ---
gcloud compute instances create "$GCP__INSTANCE_NAME" \
  --project="$GCP__PROJECT" \
  --zone="$GCP__ZONE" \
  --machine-type="$GCP__MACHINE_TYPE" \
  --network-interface=network-tier=PREMIUM,nic-type=GVNIC,stack-type=IPV4_ONLY,subnet=default \
  --metadata=tee-image-reference="$GCP__TEE_IMAGE_REFERENCE" \
  --maintenance-policy=TERMINATE \
  --provisioning-model=STANDARD \
  --service-account="$GCP__SERVICE_ACCOUNT" \
  --scopes=https://www.googleapis.com/auth/cloud-platform \
  --tags=flare-ai,http-server,https-server \
  --create-disk=auto-delete=yes,\
boot=yes,\
device-name="$GCP__INSTANCE_NAME",\
image=projects/confidential-space-images/global/images/"$GCP__IMAGE",\
mode=rw,\
size=11,\
type=pd-balanced \
  --shielded-secure-boot \
  --shielded-vtpm \
  --shielded-integrity-monitoring \
  --reservation-affinity=any \
  --confidential-compute-type="$GCP__CONFIDENTIAL_COMPUTE_TYPE"

echo "--> ✨ Instance '$GCP__INSTANCE_NAME' created successfully."
