"""Comprehensive tests for __probe__.py AI agent introspection module.

Targets 80%+ coverage for AI coding agent discovery and integration.
Tests all public APIs and internal discovery functions.
"""

from gapless_crypto_clickhouse import __probe__


class TestProbeAPIDiscovery:
    """Test API discovery functions."""

    def test_discover_api_structure(self):
        """Test discover_api returns expected structure."""
        api_map = __probe__.discover_api()

        # Verify top-level structure
        assert "metadata" in api_map
        assert "functions" in api_map
        assert "classes" in api_map
        assert "cli" in api_map
        assert "endpoints" in api_map

        # Verify metadata
        assert api_map["metadata"]["package"] == "gapless-crypto-data"
        assert "version" in api_map["metadata"]
        assert api_map["metadata"]["probe_version"] == "1.0.0"
        assert api_map["metadata"]["type"] == "cryptocurrency-data-collection"
        assert api_map["metadata"]["compatibility"] == "uv-native"

    def test_discover_api_functions(self):
        """Test function discovery includes key API functions."""
        api_map = __probe__.discover_api()
        functions = api_map["functions"]

        # Verify key functions are discovered
        assert "fetch_data" in functions
        assert "download" in functions
        assert "get_supported_symbols" in functions
        assert "get_supported_timeframes" in functions
        assert "fill_gaps" in functions

        # Verify function metadata structure
        for func_name, func_info in functions.items():
            assert "parameters" in func_info
            assert "docstring" in func_info
            assert "module" in func_info
            assert isinstance(func_info["parameters"], list)

    def test_discover_api_classes(self):
        """Test class discovery includes core classes."""
        api_map = __probe__.discover_api()
        classes = api_map["classes"]

        # Verify core classes are discovered
        assert "BinancePublicDataCollector" in classes
        assert "UniversalGapFiller" in classes

        # Verify class metadata
        assert (
            classes["BinancePublicDataCollector"]["purpose"] == "high-performance-data-collection"
        )
        assert classes["UniversalGapFiller"]["purpose"] == "gap-detection-and-filling"
        assert "methods" in classes["BinancePublicDataCollector"]
        assert isinstance(classes["BinancePublicDataCollector"]["methods"], list)

    def test_discover_api_cli(self):
        """Test CLI discovery returns usage patterns."""
        api_map = __probe__.discover_api()
        cli = api_map["cli"]

        assert cli["entry_point"] == "gapless-crypto-data"
        assert cli["uv_usage"] == "uv run gapless-crypto-data"
        assert "common_patterns" in cli
        assert isinstance(cli["common_patterns"], list)
        assert len(cli["common_patterns"]) > 0

    def test_discover_api_endpoints(self):
        """Test endpoint discovery returns probe endpoints."""
        api_map = __probe__.discover_api()
        endpoints = api_map["endpoints"]

        assert "__probe__.discover_api" in endpoints
        assert "__probe__.get_capabilities" in endpoints
        assert "__probe__.get_task_graph" in endpoints
        assert "__probe__.generate_uv_cli_tasks" in endpoints
        assert "__probe__.get_probe_info" in endpoints

    def test_discover_api_caching(self):
        """Test that discover_api results are cached."""
        result1 = __probe__.discover_api()
        result2 = __probe__.discover_api()
        # Should be the same object due to caching
        assert result1 is result2


class TestProbeCapabilities:
    """Test capabilities reporting."""

    def test_get_capabilities_structure(self):
        """Test get_capabilities returns expected structure."""
        caps = __probe__.get_capabilities()

        assert "data_collection" in caps
        assert "processing" in caps
        assert "integration" in caps
        assert "ai_agent_features" in caps

    def test_get_capabilities_data_collection(self):
        """Test data collection capabilities."""
        caps = __probe__.get_capabilities()
        data_caps = caps["data_collection"]

        assert data_caps["source"] == "binance-public-repository"
        assert data_caps["performance_multiplier"] == "22x"
        assert "USDT-spot-pairs" in data_caps["supported_markets"]
        assert "1h" in data_caps["timeframes"]
        assert "1d" in data_caps["timeframes"]
        assert data_caps["data_format"] == "11-column-microstructure"
        assert data_caps["gap_guarantee"] == "zero-gaps"

    def test_get_capabilities_processing(self):
        """Test processing capabilities."""
        caps = __probe__.get_capabilities()
        proc_caps = caps["processing"]

        assert proc_caps["memory_streaming"] is True
        assert proc_caps["atomic_operations"] is True
        assert proc_caps["resume_capability"] is True
        assert proc_caps["parallel_symbols"] is True

    def test_get_capabilities_integration(self):
        """Test integration capabilities."""
        caps = __probe__.get_capabilities()
        int_caps = caps["integration"]

        assert int_caps["pandas_compatible"] is True
        assert int_caps["polars_native"] is True
        assert int_caps["pyarrow_backend"] is True
        assert int_caps["ccxt_compatible"] is True

    def test_get_capabilities_ai_features(self):
        """Test AI agent specific features."""
        caps = __probe__.get_capabilities()
        ai_caps = caps["ai_agent_features"]

        assert ai_caps["stateless_probing"] is True
        assert ai_caps["task_graph_generation"] is True
        assert ai_caps["uv_cli_spawning"] is True
        assert ai_caps["deterministic_output"] is True
        assert ai_caps["no_file_operations"] is True

    def test_get_capabilities_caching(self):
        """Test that capabilities are cached."""
        result1 = __probe__.get_capabilities()
        result2 = __probe__.get_capabilities()
        assert result1 is result2


class TestProbeTaskGraph:
    """Test task graph generation for phased AI agent spawning."""

    def test_get_task_graph_structure(self):
        """Test task graph returns expected structure."""
        graph = __probe__.get_task_graph()

        assert "nodes" in graph
        assert "execution_plan" in graph
        assert "parallel_safe" in graph

    def test_get_task_graph_nodes(self):
        """Test task graph contains expected nodes."""
        graph = __probe__.get_task_graph()
        nodes = graph["nodes"]

        # Verify phase 0 nodes (parallel discovery)
        assert "discover" in nodes
        assert "capabilities" in nodes

        # Verify phase 1 nodes (validation)
        assert "validate_symbols" in nodes
        assert "validate_timeframes" in nodes

        # Verify phase 2 nodes (integration test)
        assert "test_collection" in nodes

    def test_get_task_graph_node_structure(self):
        """Test each node has required fields."""
        graph = __probe__.get_task_graph()

        for node_id, node in graph["nodes"].items():
            assert "type" in node
            assert "command" in node
            assert "dependencies" in node
            assert "outputs" in node
            assert "phase" in node
            assert isinstance(node["dependencies"], list)
            assert isinstance(node["outputs"], list)

    def test_get_task_graph_execution_plan(self):
        """Test execution plan contains all phases."""
        graph = __probe__.get_task_graph()
        plan = graph["execution_plan"]

        assert "phase_0" in plan
        assert "phase_1" in plan
        assert "phase_2" in plan

        # Verify phase 0 contains parallel discovery
        assert "discover" in plan["phase_0"]
        assert "capabilities" in plan["phase_0"]

    def test_get_task_graph_parallel_safe(self):
        """Test parallel safety flags."""
        graph = __probe__.get_task_graph()
        parallel_safe = graph["parallel_safe"]

        assert parallel_safe["phase_0"] is True  # Discovery is parallel-safe
        assert parallel_safe["phase_1"] is True  # Validation is parallel-safe
        assert parallel_safe["phase_2"] is False  # Integration test is sequential

    def test_get_task_graph_caching(self):
        """Test that task graph is cached."""
        result1 = __probe__.get_task_graph()
        result2 = __probe__.get_task_graph()
        assert result1 is result2


class TestProbeUVCLIGeneration:
    """Test UV CLI command generation for AI agent spawning."""

    def test_generate_uv_cli_tasks_structure(self):
        """Test CLI task generation returns expected structure."""
        tasks = __probe__.generate_uv_cli_tasks()

        assert "phase_0_parallel" in tasks
        assert "phase_1_parallel" in tasks
        assert "phase_2_sequential" in tasks
        assert "usage" in tasks

    def test_generate_uv_cli_tasks_phase_0(self):
        """Test phase 0 commands."""
        tasks = __probe__.generate_uv_cli_tasks()
        phase_0 = tasks["phase_0_parallel"]

        assert isinstance(phase_0, list)
        assert len(phase_0) == 2  # discover + capabilities
        for cmd in phase_0:
            assert cmd.startswith("uv run --active")
            assert "gapless_crypto_clickhouse" in cmd

    def test_generate_uv_cli_tasks_phase_1(self):
        """Test phase 1 commands."""
        tasks = __probe__.generate_uv_cli_tasks()
        phase_1 = tasks["phase_1_parallel"]

        assert isinstance(phase_1, list)
        assert len(phase_1) == 2  # validate_symbols + validate_timeframes

    def test_generate_uv_cli_tasks_phase_2(self):
        """Test phase 2 commands."""
        tasks = __probe__.generate_uv_cli_tasks()
        phase_2 = tasks["phase_2_sequential"]

        assert isinstance(phase_2, list)
        assert len(phase_2) == 1  # test_collection

    def test_generate_uv_cli_tasks_with_custom_graph(self):
        """Test CLI generation with custom task graph."""
        custom_graph = {
            "nodes": {
                "test_node": {
                    "type": "test",
                    "command": "python -c 'print(1)'",
                    "dependencies": [],
                    "outputs": ["test_output"],
                    "phase": 0,
                }
            },
            "execution_plan": {
                "phase_0": ["test_node"],
                "phase_1": [],
                "phase_2": [],
            },
            "parallel_safe": {"phase_0": True, "phase_1": True, "phase_2": False},
        }

        tasks = __probe__.generate_uv_cli_tasks(custom_graph)
        assert len(tasks["phase_0_parallel"]) == 1
        assert "uv run --active python -c 'print(1)'" in tasks["phase_0_parallel"]


class TestProbeInfo:
    """Test probe system metadata and health."""

    def test_get_probe_info_structure(self):
        """Test probe info returns expected structure."""
        info = __probe__.get_probe_info()

        assert "probe_system" in info
        assert "health" in info

    def test_get_probe_info_system(self):
        """Test probe system metadata."""
        info = __probe__.get_probe_info()
        system = info["probe_system"]

        assert system["version"] == "1.0.0"
        assert "claude-code" in system["compatible_agents"]
        assert system["output_format"] == "deterministic-json"
        assert system["caching"] == "memory-based"
        assert system["stateless"] is True

    def test_get_probe_info_health(self):
        """Test health checks."""
        info = __probe__.get_probe_info()
        health = info["health"]

        assert "imports_ok" in health
        assert "api_accessible" in health
        assert "cache_status" in health

        # Imports should be OK in test environment
        assert health["imports_ok"] is True
        assert health["api_accessible"] is True
        assert isinstance(health["cache_status"], int)


class TestProbeDirectAccess:
    """Test direct function access (module-level exports)."""

    def test_direct_discover_api(self):
        """Test direct access to discover_api."""
        result = __probe__.discover_api()
        assert "metadata" in result

    def test_direct_get_capabilities(self):
        """Test direct access to get_capabilities."""
        result = __probe__.get_capabilities()
        assert "data_collection" in result

    def test_direct_get_task_graph(self):
        """Test direct access to get_task_graph."""
        result = __probe__.get_task_graph()
        assert "nodes" in result

    def test_direct_generate_uv_cli_tasks(self):
        """Test direct access to generate_uv_cli_tasks."""
        result = __probe__.generate_uv_cli_tasks()
        assert "phase_0_parallel" in result

    def test_direct_get_probe_info(self):
        """Test direct access to get_probe_info."""
        result = __probe__.get_probe_info()
        assert "probe_system" in result

    def test_probe_instance_access(self):
        """Test access via probe instance."""
        result = __probe__.probe.discover_api()
        assert "metadata" in result


class TestProbeAPIClass:
    """Test ProbeAPI class instantiation and methods."""

    def test_probe_api_instantiation(self):
        """Test ProbeAPI can be instantiated."""
        from gapless_crypto_clickhouse.__probe__ import ProbeAPI

        probe = ProbeAPI()
        assert hasattr(probe, "discover_api")
        assert hasattr(probe, "get_capabilities")
        assert hasattr(probe, "get_task_graph")

    def test_probe_api_independent_caching(self):
        """Test each ProbeAPI instance has independent cache."""
        from gapless_crypto_clickhouse.__probe__ import ProbeAPI

        probe1 = ProbeAPI()
        probe2 = ProbeAPI()

        result1 = probe1.discover_api()
        result2 = probe2.discover_api()

        # Should have same content but different cache instances
        assert result1 == result2
        assert probe1._cache is not probe2._cache
