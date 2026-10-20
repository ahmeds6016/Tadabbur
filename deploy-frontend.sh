#!/bin/bash
# Claude-owned execution. Review the privacy draft with Ahmed before deployment.
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SERVICE_NAME="tafsir-frontend"
SOURCE_DIR="frontend"
MEMORY="1Gi"
CPU="1"
TIMEOUT="60"
DEPLOY_ARGS=()
source "${SCRIPT_DIR}/scripts/deploy-common.sh" "$@"
