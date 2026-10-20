#!/bin/bash
# Sourced by the two deployment entrypoints. Running an entrypoint is a deploy.
set -euo pipefail
NO_TRAFFIC=0
if [[ "${1:-}" == "--no-traffic" ]]; then
  NO_TRAFFIC=1
  shift
fi
if [[ $# -ne 0 ]]; then
  echo "Usage: $0 [--no-traffic]" >&2
  exit 2
fi

PROJECT_ID="tafsir-simplified"
REGION="us-central1"
IMAGE_NAME="gcr.io/${PROJECT_ID}/${SERVICE_NAME}"
REVISION_SUFFIX="r-$(date -u +%Y%m%d%H%M%S)-${RANDOM}"
EXPECTED_REVISION="${SERVICE_NAME}-${REVISION_SUFFIX}"
IMAGE_TAG="${IMAGE_NAME}:${REVISION_SUFFIX}"
VERIFY="${SCRIPT_DIR}/scripts/verify_deployment.py"

if [[ -z "$(gcloud auth list --filter=status:ACTIVE --format='value(account)')" ]]; then
  echo "No active gcloud account. Authenticate before deploying." >&2
  exit 1
fi

if [[ "$NO_TRAFFIC" == 0 ]]; then
  # Before building: a pinned service would leave this deploy's revision at 0%.
  python3 "$VERIFY" preflight --project "$PROJECT_ID" --region "$REGION" --service "$SERVICE_NAME"
fi

echo "Building ${IMAGE_TAG}"
BUILD_ID=$(gcloud builds submit "${SCRIPT_DIR}/${SOURCE_DIR}" --project "$PROJECT_ID" --tag "$IMAGE_TAG" --suppress-logs --format='value(id)')
DIGEST=$(python3 "$VERIFY" build-digest --project "$PROJECT_ID" --build-id "$BUILD_ID" --image "$IMAGE_TAG")

TRAFFIC_ARGS=()
VERIFY_ARGS=()
if [[ "$NO_TRAFFIC" == 1 ]]; then
  TRAFFIC_ARGS=(--no-traffic --tag "$REVISION_SUFFIX")
  VERIFY_ARGS=(--no-traffic)
fi

echo "Deploying immutable image ${IMAGE_NAME}@${DIGEST} as ${EXPECTED_REVISION}"
CREATED_REVISION=$(gcloud run deploy "$SERVICE_NAME" --project "$PROJECT_ID" --region "$REGION" \
  --image "${IMAGE_NAME}@${DIGEST}" --revision-suffix "$REVISION_SUFFIX" \
  --platform managed --allow-unauthenticated --memory "$MEMORY" --cpu "$CPU" \
  --timeout "$TIMEOUT" --max-instances 10 ${DEPLOY_ARGS[@]+"${DEPLOY_ARGS[@]}"} ${TRAFFIC_ARGS[@]+"${TRAFFIC_ARGS[@]}"} \
  --format='value(status.latestCreatedRevisionName)')

if [[ "$CREATED_REVISION" != "$EXPECTED_REVISION" ]]; then
  echo "Deployment returned latestCreated=${CREATED_REVISION}; expected created revision ${EXPECTED_REVISION}. Refusing to report success using a different latest revision." >&2
  exit 1
fi

python3 "$VERIFY" verify --project "$PROJECT_ID" --region "$REGION" --service "$SERVICE_NAME" \
  --revision "$CREATED_REVISION" --digest "$DIGEST" ${VERIFY_ARGS[@]+"${VERIFY_ARGS[@]}"}

if [[ "$NO_TRAFFIC" == 1 ]]; then
  echo "NOTE: gcloud has now pinned production traffic to the previously serving revision." >&2
  echo "The next normal deploy will refuse to run until traffic is switched; see AI.md (3.6 -> 3.8 migration notes)." >&2
fi
