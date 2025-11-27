#!/usr/bin/env bash
# ADR-0045: Deploy production schema to local ClickHouse
# Usage: ./deploy-schema.sh
# Exit codes: 0=success, 1=script not found, 2=deployment failed

set -euo pipefail

# Semantic constants (ADR-0045)
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
DEPLOY_SCRIPT="${REPO_ROOT}/scripts/deploy-clickhouse-schema.py"
MISE_UV_SHIM="${HOME}/.local/share/mise/shims/uv"

# Verify deploy script exists (no duplication - use existing)
if [[ ! -f "${DEPLOY_SCRIPT}" ]]; then
    echo "ERROR: Deploy script not found: ${DEPLOY_SCRIPT}" >&2
    exit 1
fi

# Set local mode environment
export GCCH_MODE=local
export CLICKHOUSE_HOST=localhost
export CLICKHOUSE_HTTP_PORT=8123

echo "Deploying schema to local ClickHouse..."
echo "Mode: ${GCCH_MODE}"
echo "Host: ${CLICKHOUSE_HOST}:${CLICKHOUSE_HTTP_PORT}"

# Run deployment script
if [[ -x "${MISE_UV_SHIM}" ]]; then
    "${MISE_UV_SHIM}" run python "${DEPLOY_SCRIPT}"
else
    python "${DEPLOY_SCRIPT}"
fi

echo "Schema deployment completed"
