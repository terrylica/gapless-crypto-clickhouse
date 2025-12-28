"""CLI for gapless-crypto-clickhouse setup and diagnostics.

ADR: 2025-12-21-sdk-first-run-experience

Commands:
    gcch init     - Deploy schema to ClickHouse
    gcch status   - Check ClickHouse connectivity and data counts
    gcch check    - Validate complete setup (connectivity + schema + data)
"""

import sys

import click

from . import probe
from .clickhouse import ClickHouseConfig, ClickHouseConnection


@click.group()
@click.version_option()
def main() -> None:
    """Gapless Crypto ClickHouse - Setup and diagnostics CLI."""
    pass


@main.command()
def init() -> None:
    """Deploy schema to ClickHouse.

    Creates the ohlcv table if it doesn't exist.
    Uses bundled schema.sql with production-ready settings.
    """
    try:
        config = ClickHouseConfig.from_env()
        click.echo(f"Connecting to ClickHouse at {config.host}:{config.http_port}...")

        # Create connection without context manager to avoid auto-create loop
        conn = ClickHouseConnection(config)
        if not conn.health_check():
            click.echo("ClickHouse health check failed", err=True)
            sys.exit(1)

        if conn._table_exists("ohlcv"):
            click.echo("Table 'ohlcv' already exists")
        else:
            conn.ensure_schema()
            click.echo("Schema deployed successfully")

        conn.client.close()

    except Exception as e:
        click.echo(f"Failed: {e}", err=True)
        sys.exit(1)


@main.command()
def status() -> None:
    """Check ClickHouse connectivity and data counts."""
    # Check local ClickHouse installation
    local_status = probe.check_local_clickhouse()
    mode = probe.get_current_mode()

    click.echo(f"Mode: {mode}")
    click.echo(f"Local ClickHouse installed: {local_status['installed']}")
    click.echo(f"Local ClickHouse running: {local_status['running']}")

    if local_status.get("version"):
        click.echo(f"Local ClickHouse version: {local_status['version']}")

    # Try to connect and get data counts
    try:
        config = ClickHouseConfig.from_env()
        click.echo(f"\nConnecting to {config.host}:{config.http_port}...")

        conn = ClickHouseConnection(config)
        if not conn.health_check():
            click.echo("ClickHouse health check failed", err=True)
            return

        if conn._table_exists("ohlcv"):
            result = conn.execute("SELECT COUNT(*) FROM ohlcv")
            row_count = result[0][0] if result else 0
            click.echo("Connected successfully")
            click.echo(f"ohlcv table: {row_count:,} rows")
        else:
            click.echo("Connected successfully")
            click.echo("ohlcv table: not found (run 'gcch init' to create)")

        conn.client.close()

    except Exception as e:
        click.echo(f"Connection failed: {e}", err=True)


@main.command()
def check() -> None:
    """Validate complete setup (connectivity, schema, data).

    Returns exit code 0 if all checks pass, 1 otherwise.
    """
    issues: list[str] = []

    # 1. Check mode detection
    mode = probe.get_current_mode()
    click.echo(f"[1/4] Mode detection: {mode}")

    # 2. Check ClickHouse connectivity
    click.echo("[2/4] Checking ClickHouse connectivity...")
    config = None
    conn = None
    try:
        config = ClickHouseConfig.from_env()
        conn = ClickHouseConnection(config)
        if conn.health_check():
            click.echo("      ClickHouse reachable")
        else:
            issues.append("ClickHouse health check failed")
            click.echo("      ClickHouse health check failed")
    except Exception as e:
        issues.append(f"Connection failed: {e}")
        click.echo(f"      Connection failed: {e}")

    # 3. Check schema exists
    click.echo("[3/4] Checking schema...")
    if conn:
        try:
            if conn._table_exists("ohlcv"):
                click.echo("      ohlcv table exists")
            else:
                issues.append("ohlcv table not found")
                click.echo("      ohlcv table not found")
                click.echo("      Fix: Run 'gcch init' to create schema")
        except Exception as e:
            issues.append(f"Schema check failed: {e}")
            click.echo(f"      Schema check failed: {e}")
    else:
        click.echo("      Skipped (no connection)")

    # 4. Check data availability
    click.echo("[4/4] Checking data...")
    if conn and conn._table_exists("ohlcv"):
        try:
            result = conn.execute("SELECT COUNT(*) FROM ohlcv")
            row_count = result[0][0] if result else 0
            if row_count > 0:
                click.echo(f"      {row_count:,} rows in ohlcv")
            else:
                click.echo("      No data yet (will auto-ingest on first query)")
        except Exception as e:
            click.echo(f"      Could not check data: {e}")
    else:
        click.echo("      Skipped (no table)")

    # Cleanup
    if conn:
        conn.client.close()

    # Summary
    click.echo("")
    if issues:
        click.echo(f"{len(issues)} issue(s) found:")
        for issue in issues:
            click.echo(f"   - {issue}")
        sys.exit(1)
    else:
        click.echo("All checks passed - SDK ready to use")
        sys.exit(0)


if __name__ == "__main__":
    main()
