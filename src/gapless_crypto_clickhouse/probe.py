"""
Probe module for AI agent discoverability.

Provides introspection capabilities for AI coding agents to discover:
- Available query methods and their signatures
- Supported symbols, timeframes, instrument types
- Performance characteristics (Arrow optimization)
- Auto-ingestion capabilities
- Deployment modes (Cloud vs Local) - ADR-0044

Usage (for AI agents):
    from gapless_crypto_clickhouse import probe

    # Get all capabilities as JSON
    caps = probe.get_capabilities()
    print(caps["query_methods"]["query_ohlcv"])

    # Get supported symbols
    symbols = probe.get_supported_symbols()

    # Get performance info
    perf = probe.get_performance_info()

    # Get deployment modes (ADR-0044)
    modes = probe.get_deployment_modes()
    current = probe.get_current_mode()
    status = probe.check_local_clickhouse()
"""

import json
import os
import shutil
import subprocess
from typing import Any, Dict

from . import __version__
from .api import get_supported_symbols, get_supported_timeframes

# Import semantic constants from centralized module (ADR-0046)
from .constants import (
    ENV_CLICKHOUSE_HOST,
    ENV_GCCH_MODE,
    LOCAL_HOSTS,
    MODE_AUTO,
    MODE_CLOUD,
    MODE_LOCAL,
    PORT_CLOUD_HTTP,
    PORT_LOCAL_HTTP,
)


def get_capabilities() -> Dict[str, Any]:
    """
    Get all package capabilities for AI agent discovery.

    Returns:
        Dictionary with package capabilities:
        - query_methods: Available query methods with signatures
        - data_sources: Supported data sources
        - symbols: Available trading pairs
        - timeframes: Supported timeframes
        - instrument_types: Available instrument types
        - performance: Performance characteristics
        - features: Feature flags

    Example:
        caps = probe.get_capabilities()
        print(json.dumps(caps, indent=2))
    """
    return {
        "package": {
            "name": "gapless-crypto-clickhouse",
            "version": __version__,
            "description": "ClickHouse-based cryptocurrency data with zero-gap guarantee and Arrow optimization",
        },
        "query_methods": {
            "query_ohlcv": {
                "signature": "query_ohlcv(symbol, timeframe, start_date, end_date, instrument_type='spot', auto_ingest=True, fill_gaps=True, clickhouse_config=None) -> pd.DataFrame",
                "description": "Query OHLCV data with lazy auto-ingestion (Arrow-optimized)",
                "performance": {
                    "first_query_with_auto_ingest": "30-60s (download + ingest + query)",
                    "cached_query": "0.1-2s (3x faster with Arrow)",
                    "memory_reduction": "75% vs clickhouse-driver",
                },
                "parameters": {
                    "symbol": {
                        "type": "str | List[str]",
                        "description": "Trading pair symbol(s), e.g. 'BTCUSDT' or ['BTCUSDT', 'ETHUSDT']",
                        "required": True,
                    },
                    "timeframe": {
                        "type": "str",
                        "description": "Timeframe string, e.g. '1h', '4h', '1d'",
                        "required": True,
                        "valid_values": get_supported_timeframes(),
                    },
                    "start_date": {
                        "type": "str",
                        "description": "Start date in 'YYYY-MM-DD' or 'YYYY-MM-DD HH:MM:SS' format",
                        "required": True,
                    },
                    "end_date": {
                        "type": "str",
                        "description": "End date in 'YYYY-MM-DD' or 'YYYY-MM-DD HH:MM:SS' format",
                        "required": True,
                    },
                    "instrument_type": {
                        "type": "Literal['spot', 'futures-um']",
                        "description": "Instrument type (default: 'spot')",
                        "required": False,
                        "default": "spot",
                    },
                    "auto_ingest": {
                        "type": "bool",
                        "description": "Automatically download and ingest missing data (default: True)",
                        "required": False,
                        "default": True,
                    },
                    "fill_gaps": {
                        "type": "bool",
                        "description": "Detect and fill gaps using REST API (default: True)",
                        "required": False,
                        "default": True,
                    },
                },
                "examples": [
                    {
                        "description": "Basic query with auto-ingestion",
                        "code": 'df = query_ohlcv("BTCUSDT", "1h", "2024-01-01", "2024-01-31")',
                    },
                    {
                        "description": "Multi-symbol query",
                        "code": 'df = query_ohlcv(["BTCUSDT", "ETHUSDT"], "1h", "2024-01-01", "2024-01-31")',
                    },
                    {
                        "description": "Futures data",
                        "code": 'df = query_ohlcv("BTCUSDT", "1h", "2024-01-01", "2024-01-31", instrument_type="futures-um")',
                    },
                ],
            },
            "fetch_data": {
                "signature": "fetch_data(symbol, timeframe, start=None, end=None, limit=None, instrument_type='spot') -> pd.DataFrame",
                "description": "Fetch data from file-based workflow (CSV/Parquet, no database)",
                "note": "Use query_ohlcv() for database-based workflows with auto-ingestion",
            },
        },
        "data_sources": {
            "binance_public_data": {
                "url": "https://data.binance.vision/data/",
                "description": "Binance Public Data Repository (CloudFront CDN)",
                "performance": "22x faster than REST API",
                "markets": ["spot", "futures-um"],
            },
            "binance_rest_api": {
                "url": "https://api.binance.com/api/v3/klines",
                "description": "Binance REST API (for gap filling only)",
                "rate_limit": "2400 requests/minute",
            },
        },
        "symbols": {
            "count": len(get_supported_symbols()),
            "description": "715 validated perpetual symbols (spot + futures aligned)",
            "examples": ["BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT", "XRPUSDT"],
            "source": "binance-futures-availability package (95%+ SLA)",
        },
        "timeframes": {
            "supported": get_supported_timeframes(),
            "description": "16 timeframes (13 standard: 1s-1d + 3 exotic: 3d, 1w, 1mo)",
            "ultra_high_frequency": ["1s", "1m", "3m", "5m"],
            "intraday": ["15m", "30m", "1h", "2h", "4h"],
            "daily": ["6h", "8h", "12h", "1d"],
            "exotic": ["3d", "1w", "1mo"],
        },
        "instrument_types": {
            "spot": {
                "description": "USDT-quoted spot pairs",
                "data_format": "11-column microstructure format",
            },
            "futures-um": {
                "description": "USDT-margined perpetual futures",
                "data_format": "11-column microstructure format + funding_rate",
            },
        },
        "performance": {
            "arrow_optimization": {
                "query_speedup": "3x faster DataFrame creation",
                "memory_reduction": "75% less memory (zero-copy)",
                "driver": "clickhouse-connect with Apache Arrow",
            },
            "ingestion": {
                "bulk_loader": ">100K rows/sec",
                "download": "22x faster than REST API (CloudFront CDN)",
            },
        },
        "features": {
            "zero_gap_guarantee": {
                "description": "Deterministic versioning + ReplacingMergeTree deduplication",
                "query_keyword": "FINAL",
            },
            "auto_ingestion": {
                "description": "Lazy on-demand download and ingest when data missing",
                "enabled_by_default": True,
            },
            "gap_detection": {
                "description": "SQL-based gap detection for all 16 timeframes",
                "method": "Window functions with expected interval analysis",
            },
            "gap_filling": {
                "description": "REST API-based gap filling (v6.0.0 TODO)",
                "status": "not_implemented",
            },
        },
    }


def get_performance_info() -> Dict[str, Any]:
    """
    Get performance characteristics.

    Returns:
        Dictionary with performance metrics

    Example:
        perf = probe.get_performance_info()
        print(f"Query speedup: {perf['arrow']['query_speedup']}")
    """
    return {
        "arrow": {
            "query_speedup": "3x faster",
            "memory_reduction": "75%",
            "driver": "clickhouse-connect",
        },
        "ingestion": {
            "bulk_loader": ">100K rows/sec",
            "download": "22x faster than REST API",
        },
        "query": {
            "cached": "0.1-2s",
            "first_time_with_auto_ingest": "30-60s",
        },
    }


def print_capabilities() -> None:
    """
    Print all capabilities as formatted JSON.

    Example:
        from gapless_crypto_clickhouse import probe
        probe.print_capabilities()
    """
    caps = get_capabilities()
    print(json.dumps(caps, indent=2))


# ============================================================================
# Deployment Mode Functions (ADR-0044)
# ============================================================================


def get_deployment_modes() -> Dict[str, Any]:
    """
    Get available deployment modes for AI agent discovery.

    Returns:
        Dictionary with available modes and their characteristics.

    Example:
        modes = probe.get_deployment_modes()
        print(modes["local"]["description"])
    """
    return {
        "available_modes": [MODE_LOCAL, MODE_CLOUD],
        "default_mode": MODE_AUTO,
        MODE_CLOUD: {
            "description": "ClickHouse Cloud on AWS (production, multi-user)",
            "port": PORT_CLOUD_HTTP,
            "secure": True,
            "requires_credentials": True,
            "best_for": [
                "Multi-user access",
                "Production workloads",
                "Managed infrastructure",
            ],
        },
        MODE_LOCAL: {
            "description": "Local ClickHouse installation (development, backtesting)",
            "port": PORT_LOCAL_HTTP,
            "secure": False,
            "requires_credentials": False,
            "best_for": [
                "Backtesting (50-100x faster)",
                "Development",
                "Offline work",
                "Trying the package",
            ],
        },
        "mode_selection": {
            "env_var": ENV_GCCH_MODE,
            "values": {
                MODE_LOCAL: "Force local mode",
                MODE_CLOUD: "Force cloud mode (requires CLICKHOUSE_HOST)",
                MODE_AUTO: "Auto-detect based on CLICKHOUSE_HOST",
            },
        },
    }


def get_current_mode() -> str:
    """
    Detect current deployment mode from environment.

    Returns:
        "local" or "cloud" based on environment configuration.

    Example:
        current = probe.get_current_mode()
        print(f"Running in {current} mode")
    """
    mode = os.environ.get(ENV_GCCH_MODE, MODE_AUTO).lower()

    if mode == MODE_LOCAL:
        return MODE_LOCAL
    elif mode == MODE_CLOUD:
        return MODE_CLOUD
    else:  # auto
        host = os.environ.get(ENV_CLICKHOUSE_HOST, "")
        if host in LOCAL_HOSTS:
            return MODE_LOCAL
        return MODE_CLOUD


def get_local_installation_guide() -> Dict[str, Any]:
    """
    Get platform-specific installation guide for local ClickHouse.

    Returns:
        Dictionary with installation instructions per platform.

    Example:
        guide = probe.get_local_installation_guide()
        print(guide["macos"]["commands"])
    """
    import platform

    current_platform = platform.system().lower()

    return {
        "current_platform": current_platform,
        "macos": {
            "method": "Homebrew",
            "commands": [
                "brew install clickhouse",
                "clickhouse server --daemon",
            ],
            "verify": "clickhouse client --query 'SELECT 1'",
            "stop": "pkill -f clickhouse-server",
        },
        "linux": {
            "method": "Official installer",
            "commands": [
                "curl https://clickhouse.com/ | sh",
                "./clickhouse server --daemon",
            ],
            "verify": "./clickhouse client --query 'SELECT 1'",
            "alternative": {
                "method": "apt (Ubuntu/Debian)",
                "commands": [
                    "sudo apt-get install -y apt-transport-https ca-certificates",
                    "curl -fsSL https://packages.clickhouse.com/deb/lts/clickhouse.gpg | sudo gpg --dearmor -o /usr/share/keyrings/clickhouse-keyring.gpg",
                    'echo "deb [signed-by=/usr/share/keyrings/clickhouse-keyring.gpg] https://packages.clickhouse.com/deb stable main" | sudo tee /etc/apt/sources.list.d/clickhouse.list',
                    "sudo apt-get update",
                    "sudo apt-get install -y clickhouse-server clickhouse-client",
                    "sudo service clickhouse-server start",
                ],
            },
        },
        "configuration": {
            "env_vars": {
                ENV_GCCH_MODE: MODE_LOCAL,
                ENV_CLICKHOUSE_HOST: "localhost",
                "CLICKHOUSE_HTTP_PORT": str(PORT_LOCAL_HTTP),
            },
            "example": f'export {ENV_GCCH_MODE}={MODE_LOCAL}',
        },
    }


def check_local_clickhouse() -> Dict[str, Any]:
    """
    Check if local ClickHouse is installed and running.

    Returns:
        Dictionary with installation and running status.

    Example:
        status = probe.check_local_clickhouse()
        if status["running"]:
            print(f"ClickHouse running, version: {status['version']}")
    """
    result: Dict[str, Any] = {
        "installed": False,
        "running": False,
        "binary_path": None,
        "version": None,
        "error": None,
    }

    # Check if clickhouse binary is available
    binary_path = shutil.which("clickhouse")
    if binary_path:
        result["installed"] = True
        result["binary_path"] = binary_path

        # Try to get version
        try:
            version_output = subprocess.run(
                ["clickhouse", "client", "--version"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if version_output.returncode == 0:
                result["version"] = version_output.stdout.strip()
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pass

    # Check if server is running by attempting connection
    try:
        import socket

        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(2)
        connect_result = sock.connect_ex(("localhost", PORT_LOCAL_HTTP))
        sock.close()
        if connect_result == 0:
            result["running"] = True
    except Exception as e:
        result["error"] = str(e)

    return result


if __name__ == "__main__":
    # Allow running as script for quick inspection
    print_capabilities()
