"""
__probe__.py - API-only probe hooks for AI coding agents

Provides deterministic JSON output for effortless AI agent discovery:
- API map discovery
- Capabilities detection
- Task graph generation for phased spawning
- Zero-file terminal probing

Usage:
    import gapless_crypto_clickhouse
    probe = gapless_crypto_clickhouse.__probe__

    # Initial discovery
    api_map = probe.discover_api()
    capabilities = probe.get_capabilities()

    # Phased spawning
    task_graph = probe.get_task_graph()
    sub_tasks = probe.generate_uv_cli_tasks(task_graph)
"""

import inspect
from typing import Any, Dict, List, Optional

# Internal imports
from . import api
from .collectors.binance_public_data_collector import BinancePublicDataCollector
from .gap_filling.universal_gap_filler import UniversalGapFiller


class ProbeAPI:
    """API-only probe hooks for deterministic JSON output."""

    def __init__(self):
        self._cache: Dict[str, Any] = {}

    def discover_api(self) -> Dict[str, Any]:
        """
        Generate deterministic API map for AI agents.

        Returns:
            Dict containing complete API surface with metadata
        """
        if "api_map" in self._cache:
            return self._cache["api_map"]

        api_map = {
            "metadata": {
                "package": "gapless-crypto-data",
                "version": "2.15.0",
                "probe_version": "1.0.0",
                "type": "cryptocurrency-data-collection",
                "compatibility": "uv-native",
            },
            "functions": self._discover_functions(),
            "classes": self._discover_classes(),
            "cli": self._discover_cli(),
            "endpoints": self._discover_endpoints(),
        }

        self._cache["api_map"] = api_map
        return api_map

    def get_capabilities(self) -> Dict[str, Any]:
        """
        Report package capabilities for AI agents.

        Returns:
            Dict with capability matrix and operational limits
        """
        if "capabilities" in self._cache:
            return self._cache["capabilities"]

        capabilities = {
            "data_collection": {
                "source": "binance-public-repository",
                "performance_multiplier": "22x",
                "supported_markets": ["USDT-spot-pairs"],
                "timeframes": [
                    "1s",
                    "1m",
                    "3m",
                    "5m",
                    "15m",
                    "30m",
                    "1h",
                    "2h",
                    "4h",
                    "6h",
                    "8h",
                    "12h",
                    "1d",
                ],
                "data_format": "11-column-microstructure",
                "gap_guarantee": "zero-gaps",
            },
            "processing": {
                "memory_streaming": True,
                "atomic_operations": True,
                "resume_capability": True,
                "parallel_symbols": True,
            },
            "integration": {
                "pandas_compatible": True,
                "polars_native": True,
                "pyarrow_backend": True,
                "ccxt_compatible": True,
            },
            "ai_agent_features": {
                "stateless_probing": True,
                "task_graph_generation": True,
                "uv_cli_spawning": True,
                "deterministic_output": True,
                "no_file_operations": True,
            },
        }

        self._cache["capabilities"] = capabilities
        return capabilities

    def get_task_graph(self) -> Dict[str, Any]:
        """
        Generate task dependency graph for phased AI agent spawning.

        Returns:
            Dict with task nodes, dependencies, and execution metadata
        """
        if "task_graph" in self._cache:
            return self._cache["task_graph"]

        task_graph = {
            "nodes": {
                "discover": {
                    "type": "discovery",
                    "command": 'python -c "import gapless_crypto_clickhouse; print(gapless_crypto_clickhouse.__probe__.discover_api())"',
                    "dependencies": [],
                    "outputs": ["api_map"],
                    "phase": 0,
                },
                "capabilities": {
                    "type": "capability_check",
                    "command": 'python -c "import gapless_crypto_clickhouse; print(gapless_crypto_clickhouse.__probe__.get_capabilities())"',
                    "dependencies": [],
                    "outputs": ["capabilities_matrix"],
                    "phase": 0,
                },
                "validate_symbols": {
                    "type": "validation",
                    "command": 'python -c "import gapless_crypto_clickhouse; print(gapless_crypto_clickhouse.get_supported_symbols())"',
                    "dependencies": ["discover"],
                    "outputs": ["symbol_list"],
                    "phase": 1,
                },
                "validate_timeframes": {
                    "type": "validation",
                    "command": 'python -c "import gapless_crypto_clickhouse; print(gapless_crypto_clickhouse.get_supported_timeframes())"',
                    "dependencies": ["discover"],
                    "outputs": ["timeframe_list"],
                    "phase": 1,
                },
                "test_collection": {
                    "type": "integration_test",
                    "command": "python -c \"import gapless_crypto_clickhouse; df=gapless_crypto_clickhouse.fetch_data('BTCUSDT', '1h', limit=5); print(f'✓ {len(df)} rows collected')\"",
                    "dependencies": ["validate_symbols", "validate_timeframes"],
                    "outputs": ["collection_status"],
                    "phase": 2,
                },
            },
            "execution_plan": {
                "phase_0": ["discover", "capabilities"],
                "phase_1": ["validate_symbols", "validate_timeframes"],
                "phase_2": ["test_collection"],
            },
            "parallel_safe": {"phase_0": True, "phase_1": True, "phase_2": False},
        }

        self._cache["task_graph"] = task_graph
        return task_graph

    def generate_uv_cli_tasks(self, task_graph: Optional[Dict[str, Any]] = None) -> List[str]:
        """
        Generate uv CLI commands for spawning AI agent sub-tasks.

        Args:
            task_graph: Optional pre-computed task graph

        Returns:
            List of uv CLI commands ready for execution
        """
        if task_graph is None:
            task_graph = self.get_task_graph()

        # Phase 0: Parallel discovery
        phase_0_commands = []
        for node_id in task_graph["execution_plan"]["phase_0"]:
            node = task_graph["nodes"][node_id]
            uv_cmd = f"uv run --active {node['command']}"
            phase_0_commands.append(uv_cmd)

        # Phase 1: Validation (depends on Phase 0)
        phase_1_commands = []
        for node_id in task_graph["execution_plan"]["phase_1"]:
            node = task_graph["nodes"][node_id]
            uv_cmd = f"uv run --active {node['command']}"
            phase_1_commands.append(uv_cmd)

        # Phase 2: Integration test (depends on Phase 1)
        phase_2_commands = []
        for node_id in task_graph["execution_plan"]["phase_2"]:
            node = task_graph["nodes"][node_id]
            uv_cmd = f"uv run --active {node['command']}"
            phase_2_commands.append(uv_cmd)

        return {
            "phase_0_parallel": phase_0_commands,
            "phase_1_parallel": phase_1_commands,
            "phase_2_sequential": phase_2_commands,
            "usage": "Execute phases in order. Within each phase, commands can run in parallel.",
        }

    def get_probe_info(self) -> Dict[str, Any]:
        """
        Get probe system metadata and health.

        Returns:
            Dict with probe system status and capabilities
        """
        return {
            "probe_system": {
                "version": "1.0.0",
                "compatible_agents": ["claude-code", "cursor", "copilot", "codeium"],
                "output_format": "deterministic-json",
                "caching": "memory-based",
                "stateless": True,
            },
            "health": {
                "imports_ok": self._check_imports(),
                "api_accessible": self._check_api_access(),
                "cache_status": len(self._cache),
            },
        }

    def _discover_functions(self) -> Dict[str, Any]:
        """Discover public functions from api module."""
        functions = {}

        for name in dir(api):
            if not name.startswith("_"):
                obj = getattr(api, name)
                if callable(obj) and inspect.isfunction(obj):
                    sig = inspect.signature(obj)
                    functions[name] = {
                        "parameters": [p.name for p in sig.parameters.values()],
                        "docstring": (obj.__doc__ or "").strip(),
                        "module": obj.__module__,
                    }

        return functions

    def _discover_classes(self) -> Dict[str, Any]:
        """Discover public classes."""
        classes = {
            "BinancePublicDataCollector": {
                "module": "gapless_crypto_clickhouse.collectors.binance_public_data_collector",
                "purpose": "high-performance-data-collection",
                "methods": self._get_public_methods(BinancePublicDataCollector),
            },
            "UniversalGapFiller": {
                "module": "gapless_crypto_clickhouse.gap_filling.universal_gap_filler",
                "purpose": "gap-detection-and-filling",
                "methods": self._get_public_methods(UniversalGapFiller),
            },
        }

        return classes

    def _discover_cli(self) -> Dict[str, Any]:
        """Discover CLI interface."""
        return {
            "entry_point": "gapless-crypto-data",
            "uv_usage": "uv run gapless-crypto-data",
            "common_patterns": [
                "uv run gapless-crypto-data --symbol BTCUSDT --timeframes 1h,4h",
                "uv run gapless-crypto-data --fill-gaps --directory ./data",
                "uv run gapless-crypto-data --symbol BTCUSDT,ETHUSDT --timeframes 1s,1d",
            ],
        }

    def _discover_endpoints(self) -> Dict[str, Any]:
        """Discover probe endpoints."""
        return {
            "__probe__.discover_api": "Complete API surface discovery",
            "__probe__.get_capabilities": "Package capability matrix",
            "__probe__.get_task_graph": "Task dependency graph for phased execution",
            "__probe__.generate_uv_cli_tasks": "uv CLI commands for agent spawning",
            "__probe__.get_probe_info": "Probe system metadata and health",
        }

    def _get_public_methods(self, cls) -> List[str]:
        """Get public methods from a class."""
        return [
            name for name in dir(cls) if not name.startswith("_") and callable(getattr(cls, name))
        ]

    def _check_imports(self) -> bool:
        """Check if core imports are working."""
        try:
            import importlib.util

            return (
                importlib.util.find_spec("pandas") is not None
                and importlib.util.find_spec("httpx") is not None
            )
        except ImportError:
            return False

    def _check_api_access(self) -> bool:
        """Check if API functions are accessible."""
        try:
            from . import api

            return hasattr(api, "fetch_data")
        except Exception:
            return False


# Global probe instance for easy access
_probe_instance = ProbeAPI()

# Export functions for direct access
discover_api = _probe_instance.discover_api
get_capabilities = _probe_instance.get_capabilities
get_task_graph = _probe_instance.get_task_graph
generate_uv_cli_tasks = _probe_instance.generate_uv_cli_tasks
get_probe_info = _probe_instance.get_probe_info

# For backwards compatibility and explicit access
probe = _probe_instance

__all__ = [
    "discover_api",
    "get_capabilities",
    "get_task_graph",
    "generate_uv_cli_tasks",
    "get_probe_info",
    "probe",
    "ProbeAPI",
]
