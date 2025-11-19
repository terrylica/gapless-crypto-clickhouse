#!/usr/bin/env python3
"""Test importing the built package and verify version."""

import importlib.metadata
import sys

# Test import
try:
    import gapless_crypto_clickhouse

    print("✅ Package import successful")
except ImportError as e:
    print(f"❌ Package import failed: {e}")
    sys.exit(1)

# Check __version__
try:
    version = gapless_crypto_clickhouse.__version__
    print(f"✅ __version__: {version}")
except AttributeError:
    print("⚠️ __version__ attribute not found")

# Check metadata version
try:
    metadata_version = importlib.metadata.version("gapless-crypto-clickhouse")
    print(f"✅ Metadata version: {metadata_version}")
except importlib.metadata.PackageNotFoundError:
    print("⚠️ Package metadata not found")

# Test key modules
modules_to_test = [
    "gapless_crypto_clickhouse.api",
    "gapless_crypto_clickhouse.__probe__",
    "gapless_crypto_clickhouse.exceptions",
    "gapless_crypto_clickhouse.clickhouse_query",
    "gapless_crypto_clickhouse.collectors.clickhouse_bulk_loader",
    "gapless_crypto_clickhouse.clickhouse.connection",
]

for module in modules_to_test:
    try:
        importlib.import_module(module)
        print(f"✅ {module}")
    except ImportError as e:
        print(f"❌ {module}: {e}")

# Test probe discovery
try:
    from gapless_crypto_clickhouse.__probe__ import discover

    result = discover()
    print(f"✅ Probe discovery: {len(result)} capabilities")
except Exception as e:
    print(f"⚠️ Probe discovery failed: {e}")

# Test API functions
try:
    from gapless_crypto_clickhouse.api import collect_data  # noqa: F401

    print("✅ API function 'collect_data' available")
except ImportError as e:
    print(f"❌ API import failed: {e}")

print("\n✅ Import validation complete")
