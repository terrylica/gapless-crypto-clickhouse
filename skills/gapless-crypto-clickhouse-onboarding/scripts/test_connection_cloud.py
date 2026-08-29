#!/usr/bin/env python3
"""Test ClickHouse Cloud connection (Doppler OR .env file support).

Usage (Doppler - recommended):
    doppler run --project aws-credentials --config prd -- python test_connection_cloud.py

Usage (.env file - fallback):
    python test_connection_cloud.py  # Auto-loads from .env if present

Requirements:
    - Option A: Doppler CLI with aws-credentials/prd access
    - Option B: .env file with ClickHouse Cloud credentials
    - Package: gapless-crypto-clickhouse (imports ClickHouseConnection)
"""

import os
import sys


def test_connection():
    """Test ClickHouse Cloud connection with diagnostic queries."""

    # Step 1: Try loading from .env file if present (fallback method)
    if os.path.exists(".env"):
        print("🔍 Found .env file, loading credentials...")
        try:
            from dotenv import load_dotenv

            load_dotenv(".env")
            print("✅ .env file loaded")
        except ImportError:
            print("⚠️  python-dotenv not installed, skipping .env loading")
            print("   Install with: pip install python-dotenv")

    # Step 2: Verify required environment variables
    required_vars = {
        "CLICKHOUSE_HOST": os.getenv("CLICKHOUSE_HOST"),
        "CLICKHOUSE_HTTP_PORT": os.getenv("CLICKHOUSE_HTTP_PORT", "8443"),
        "CLICKHOUSE_USER": os.getenv("CLICKHOUSE_USER", "default"),
        "CLICKHOUSE_PASSWORD": os.getenv("CLICKHOUSE_PASSWORD"),
        "CLICKHOUSE_SECURE": os.getenv("CLICKHOUSE_SECURE", "true"),
    }

    missing = [k for k, v in required_vars.items() if not v]
    if missing or not required_vars["CLICKHOUSE_PASSWORD"]:
        print("❌ Error: Missing required environment variables")
        print(f"   Missing: {', '.join(missing) if missing else 'CLICKHOUSE_PASSWORD (empty)'}")
        print("\n📝 How to fix:")
        print(
            "   Option A (Doppler): doppler run --project aws-credentials --config prd -- python test_connection_cloud.py"
        )
        print("   Option B (.env file):")
        print("     1. cp .env.cloud.example .env")
        print("     2. Edit .env with your credentials")
        print("     3. python test_connection_cloud.py")
        sys.exit(1)

    print("\n🔍 Testing ClickHouse Cloud Connection...")
    print(f"   Host: {required_vars['CLICKHOUSE_HOST']}")
    print(f"   Port: {required_vars['CLICKHOUSE_HTTP_PORT']}")
    print(f"   User: {required_vars['CLICKHOUSE_USER']}")
    print(f"   Secure: {required_vars['CLICKHOUSE_SECURE']}")

    try:
        # Use gapless-crypto-clickhouse package (has secure parameter support)
        from gapless_crypto_clickhouse.clickhouse import ClickHouseConfig, ClickHouseConnection

        # Create config from environment
        config = ClickHouseConfig.from_env()

        # Test connection
        with ClickHouseConnection(config) as conn:
            # Test 1: Version and user query
            result = conn.execute("SELECT version() as version, currentUser() as user")
            version, current_user = result[0]

            print("\n✅ Connection successful!")
            print(f"   ClickHouse version: {version}")
            print(f"   User: {current_user}")

            # Test 2: Table count query
            result = conn.execute("SELECT count() FROM system.tables")
            table_count = result[0][0]
            print(f"   Tables visible: {table_count}")

            # Test 3: Database accessibility
            try:
                result = conn.execute("SELECT count() FROM gapless_crypto.klines")
                row_count = result[0][0]
                print(f"   Data accessible: ✅ (gapless_crypto.klines, {row_count:,} rows)")
            except Exception:
                print(
                    "   Data accessible: ⚠️  (gapless_crypto.klines not yet created - expected for new service)"
                )

        print("\n🎉 All connection tests passed!")
        print("\n📋 Service Details:")
        print("   Service ID: a3163f31-21f4-4e22-844e-ef3fbc26ace2")
        print("   Region: us-west-2 (AWS)")
        print("   Console: https://clickhouse.cloud/services/a3163f31-21f4-4e22-844e-ef3fbc26ace2")

        print("\n🚀 Next Steps:")
        print("   1. Run your first query: python examples/simple_api_examples.py")
        print("   2. Read API docs: docs/guides/python-api.md")
        print("   3. Join #data-engineering Slack for support")

        return 0

    except ImportError as e:
        print(f"❌ Package import failed: {e}")
        print("\n📝 How to fix:")
        print("   Install package: pip install gapless-crypto-clickhouse")
        return 1

    except Exception as e:
        print(f"❌ Connection failed: {e}")

        # Provide troubleshooting guidance based on error type
        error_msg = str(e).lower()

        print("\n🔧 Troubleshooting:")

        if "connection refused" in error_msg or "timeout" in error_msg:
            print("  ❌ Connection Refused / Timeout")
            print("     → Check CLICKHOUSE_HOST ends with '.aws.clickhouse.cloud'")
            print("     → Verify CLICKHOUSE_HTTP_PORT=8443 (not 8123)")
            print("     → Service may be resuming from idle (15min timeout), retry in 30s")
            print(
                "     → Verify service status: https://clickhouse.cloud/services/a3163f31-21f4-4e22-844e-ef3fbc26ace2"
            )

        elif "ssl" in error_msg or "tls" in error_msg or "certificate" in error_msg:
            print("  ❌ SSL/TLS Error")
            print("     → Ensure CLICKHOUSE_SECURE=true in environment variables")
            print("     → Package v6.0.0+ required for secure parameter support")
            print("     → Upgrade if needed: pip install --upgrade gapless-crypto-clickhouse")

        elif (
            "authentication" in error_msg or "password" in error_msg or "access denied" in error_msg
        ):
            print("  ❌ Authentication Failed")
            print("     → Verify CLICKHOUSE_PASSWORD is correct")
            print(
                "     → Check Doppler: doppler secrets get CLICKHOUSE_PASSWORD --project aws-credentials --config prd"
            )
            print(
                "     → Reset password in console: https://clickhouse.cloud/ → Settings → Reset Password"
            )
            print("     → Update Doppler/1Password after password reset")

        else:
            print("  ❌ Unknown Error")
            print("     → Review error message above")
            print("     → Check environment variables: env | grep CLICKHOUSE")
            print(
                "     → See troubleshooting guide: skills/gapless-crypto-clickhouse-onboarding/references/troubleshooting.md"
            )
            print("     → Join #data-engineering Slack for support")

        return 1


if __name__ == "__main__":
    sys.exit(test_connection())
