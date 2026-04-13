#!/usr/bin/env bash
# deploy.sh — One-command deploy to Google Cloud Run
# Usage: SOVEREIGN_GEMINI_API_KEY=<key> ./deploy.sh

set -euo pipefail

PROJECT_ID="${SOVEREIGN_GCP_PROJECT:-your-project-id}"
SERVICE_NAME="axiom-generator"
REGION="us-central1"
IMAGE="${REGION}-docker.pkg.dev/${PROJECT_ID}/axiom/${SERVICE_NAME}:latest"

echo "▶  Building and pushing image: ${IMAGE}"
gcloud builds submit --tag "${IMAGE}"

echo "▶  Deploying to Cloud Run (${SERVICE_NAME} @ ${REGION})"
gcloud run deploy "${SERVICE_NAME}" \
    --image "${IMAGE}" \
    --platform managed \
    --region "${REGION}" \
    --allow-unauthenticated \
    --memory 1Gi \
    --cpu 1 \
    --timeout 300 \
    --set-env-vars "SOVEREIGN_GEMINI_API_KEY=${SOVEREIGN_GEMINI_API_KEY}"

SERVICE_URL=$(gcloud run services describe "${SERVICE_NAME}" \
    --platform managed --region "${REGION}" \
    --format 'value(status.url)')

echo "✅  Deployed at: ${SERVICE_URL}"
