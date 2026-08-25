#!/usr/bin/env bash
# ADR-0045: Start the local ClickHouse server
# Usage: ./start-clickhouse.sh
# Exit codes: 0=success/already running, 1=not installed, 2=failed to start

set -euo pipefail

# Semantic constants (ADR-0045)
PORT_LOCAL_HTTP=8123
STARTUP_TIMEOUT_SEC=10

# Resolve the clickhouse binary, PATH first.
#
# This script previously hardcoded "${HOME}/.local/share/mise/shims/clickhouse". mise was
# retired machine-wide (proto is the only toolchain manager), so that path stopped
# existing and this script failed on every invocation -- while telling the reader to fix
# it by running `mise install clickhouse`, a command that cannot work here. ClickHouse was
# installed the whole time at /opt/homebrew/bin/clickhouse.
#
# PATH first is the tool-agnostic answer: proto shims, Homebrew and system installs all
# land there, so this needs no edit the next time the toolchain manager changes. The
# explicit fallbacks cover a non-login shell whose PATH never went through profile
# activation. The mise entry is kept ONLY so a machine that still has one keeps working;
# it is last on purpose and must not be promoted back to primary.
CLICKHOUSE_BIN=""
if command -v clickhouse >/dev/null 2>&1; then
    CLICKHOUSE_BIN="$(command -v clickhouse)"
else
    for candidate in \
        "${HOME}/.proto/shims/clickhouse" \
        "/opt/homebrew/bin/clickhouse" \
        "/usr/local/bin/clickhouse" \
        "${HOME}/.local/share/mise/shims/clickhouse"; do
        if [[ -x "${candidate}" ]]; then
            CLICKHOUSE_BIN="${candidate}"
            break
        fi
    done
fi

if [[ -z "${CLICKHOUSE_BIN}" ]]; then
    echo "ERROR: clickhouse binary not found on PATH or at any known location" >&2
    echo "Install it (e.g. 'brew install clickhouse') or put it on PATH." >&2
    exit 1
fi

# Check if already running
if nc -z localhost "${PORT_LOCAL_HTTP}" 2>/dev/null; then
    echo "ClickHouse already running on port ${PORT_LOCAL_HTTP}"
    "${CLICKHOUSE_BIN}" client --query "SELECT version()" 2>/dev/null || true
    exit 0
fi

# Start server in daemon mode
echo "Starting ClickHouse server..."
"${CLICKHOUSE_BIN}" server --daemon

# Wait for server to be ready
for i in $(seq 1 "${STARTUP_TIMEOUT_SEC}"); do
    if nc -z localhost "${PORT_LOCAL_HTTP}" 2>/dev/null; then
        echo "ClickHouse server started successfully"
        "${CLICKHOUSE_BIN}" client --query "SELECT version()"
        exit 0
    fi
    echo "Waiting for server... (${i}/${STARTUP_TIMEOUT_SEC})"
    sleep 1
done

echo "ERROR: ClickHouse server failed to start within ${STARTUP_TIMEOUT_SEC}s" >&2
exit 2
