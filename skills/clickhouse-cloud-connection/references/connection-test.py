#!/usr/bin/env python3
"""Test ClickHouse Cloud connection using Doppler credentials.

Usage:
    doppler run --project aws-credentials --config prd -- python connection-test.py

Requirements:
    - Doppler CLI configured with aws-credentials/prd access
    - clickhouse-connect library: uv pip install clickhouse-connect
"""
import os
import sys
import clickhouse_connect


def test_connection():
    """Test ClickHouse Cloud connection with diagnostic queries."""

    # Load credentials from environment (set by Doppler)
    host = os.getenv("CLICKHOUSE_HOST")
    port = int(os.getenv("CLICKHOUSE_PORT", "8443"))
    user = os.getenv("CLICKHOUSE_USER", "default")
    password = os.getenv("CLICKHOUSE_PASSWORD")

    # Validate environment
    if not all([host, password]):
        print("❌ Error: Missing required environment variables")
        print("   Required: CLICKHOUSE_HOST, CLICKHOUSE_PASSWORD")
        print("   Run with: doppler run --project aws-credentials --config prd -- python connection-test.py")
        sys.exit(1)

    print(f"Connecting to {host}:{port} as {user}...")

    try:
        # Create clickhouse-connect client
        client = clickhouse_connect.get_client(
            host=host,
            port=port,
            username=user,
            password=password,
            secure=True  # CRITICAL: Required for ClickHouse Cloud
        )

        # Test 1: Version and user query
        result = client.query("SELECT version() as version, currentUser() as user")
        version = result.result_rows[0][0]
        current_user = result.result_rows[0][1]

        print(f"✅ Connection successful!")
        print(f"   ClickHouse version: {version}")
        print(f"   User: {current_user}")

        # Test 2: Table count query
        result = client.query("SELECT count() FROM system.tables")
        table_count = result.result_rows[0][0]
        print(f"   Tables visible: {table_count}")

        # Test 3: Data accessibility (optional)
        try:
            result = client.query("SELECT count() FROM gapless_crypto.klines")
            row_count = result.result_rows[0][0]
            print(f"   Data accessible: ✅ (gapless_crypto.klines, {row_count:,} rows)")
        except Exception:
            print(f"   Data accessible: ⚠️  (gapless_crypto.klines not yet created)")

        print(f"\n✅ All connection tests passed!")
        print(f"   Service ID: a3163f31-21f4-4e22-844e-ef3fbc26ace2")
        return 0

    except Exception as e:
        print(f"❌ Connection failed: {e}")
        print(f"\nTroubleshooting:")
        print(f"  - Check Doppler credentials: doppler secrets --project aws-credentials --config prd --only-names | grep CLICKHOUSE")
        print(f"  - Verify service status: https://clickhouse.cloud/services/a3163f31-21f4-4e22-844e-ef3fbc26ace2")
        print(f"  - Check password in console: https://clickhouse.cloud/ → Settings → Reset Password")
        return 1


if __name__ == "__main__":
    sys.exit(test_connection())
