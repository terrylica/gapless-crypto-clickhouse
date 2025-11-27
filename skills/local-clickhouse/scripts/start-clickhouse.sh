#!/usr/bin/env bash
# ADR-0045: Start mise-installed ClickHouse server
# Usage: ./start-clickhouse.sh
# Exit codes: 0=success/already running, 1=not installed, 2=failed to start

set -euo pipefail

# Semantic constants (ADR-0045)
MISE_CLICKHOUSE_SHIM="${HOME}/.local/share/mise/shims/clickhouse"
PORT_LOCAL_HTTP=8123
STARTUP_TIMEOUT_SEC=10

# Check mise ClickHouse installation
if [[ ! -x "${MISE_CLICKHOUSE_SHIM}" ]]; then
    echo "ERROR: mise ClickHouse not found at ${MISE_CLICKHOUSE_SHIM}" >&2
    echo "Install: mise install clickhouse" >&2
    exit 1
fi

# Check if already running
if nc -z localhost "${PORT_LOCAL_HTTP}" 2>/dev/null; then
    echo "ClickHouse already running on port ${PORT_LOCAL_HTTP}"
    "${MISE_CLICKHOUSE_SHIM}" client --query "SELECT version()" 2>/dev/null || true
    exit 0
fi

# Start server in daemon mode
echo "Starting ClickHouse server..."
"${MISE_CLICKHOUSE_SHIM}" server --daemon

# Wait for server to be ready
for i in $(seq 1 "${STARTUP_TIMEOUT_SEC}"); do
    if nc -z localhost "${PORT_LOCAL_HTTP}" 2>/dev/null; then
        echo "ClickHouse server started successfully"
        "${MISE_CLICKHOUSE_SHIM}" client --query "SELECT version()"
        exit 0
    fi
    echo "Waiting for server... (${i}/${STARTUP_TIMEOUT_SEC})"
    sleep 1
done

echo "ERROR: ClickHouse server failed to start within ${STARTUP_TIMEOUT_SEC}s" >&2
exit 2
