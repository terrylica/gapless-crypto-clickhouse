# AI Agent Probe Usage Example

This demonstrates how AI coding agents can effortlessly probe the `gapless-crypto-data` package after PyPI installation.

## Phase 0: Initial Discovery (Parallel)

```bash
# Discover complete API surface
uv run --active python -c "import gapless_crypto_data; print(gapless_crypto_data.__probe__.discover_api())"

# Get capability matrix
uv run --active python -c "import gapless_crypto_data; print(gapless_crypto_data.__probe__.get_capabilities())"
```

## Phase 1: Validation (Parallel)

```bash
# Validate supported symbols
uv run --active python -c "import gapless_crypto_data; print(gapless_crypto_data.get_supported_symbols())"

# Validate supported timeframes
uv run --active python -c "import gapless_crypto_data; print(gapless_crypto_data.get_supported_timeframes())"
```

## Phase 2: Integration Test (Sequential)

```bash
# Test data collection capability
uv run --active python -c "import gapless_crypto_data; df=gapless_crypto_data.fetch_data('BTCUSDT', '1h', limit=5); print(f'✓ {len(df)} rows collected')"
```

## Automated Task Generation

AI agents can generate the complete task graph:

```bash
uv run --active python -c "
import gapless_crypto_data
import json

# Get phased task commands
tasks = gapless_crypto_data.__probe__.generate_uv_cli_tasks()
print('=== PHASE 0 (Parallel Discovery) ===')
for cmd in tasks['phase_0_parallel']:
    print(f'  {cmd}')

print('\\n=== PHASE 1 (Parallel Validation) ===')
for cmd in tasks['phase_1_parallel']:
    print(f'  {cmd}')

print('\\n=== PHASE 2 (Sequential Integration) ===')
for cmd in tasks['phase_2_sequential']:
    print(f'  {cmd}')
"
```

## Key Benefits for AI Agents

1. **No File Operations**: Pure API-based discovery
2. **Deterministic Output**: Consistent JSON across runs
3. **Stateless Probing**: No persistent state required
4. **Phased Execution**: Optimal performance with parallel tasks
5. **uv Native**: Direct CLI command generation

## Sample Output

```json
{
  "ai_agent_features": {
    "deterministic_output": true,
    "no_file_operations": true,
    "stateless_probing": true,
    "task_graph_generation": true,
    "uv_cli_spawning": true
  },
  "data_collection": {
    "gap_guarantee": "zero-gaps",
    "performance_multiplier": "22x",
    "source": "binance-public-repository"
  }
}
```

This design makes it effortless for AI coding agents to understand, validate, and utilize the package capabilities without any setup overhead.
