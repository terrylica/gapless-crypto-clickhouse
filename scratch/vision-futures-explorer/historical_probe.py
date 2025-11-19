#!/usr/bin/env python3
# /// script
# dependencies = [
#   "urllib3>=2.0.0",
# ]
# ///
"""
Binance Vision Historical Availability Probe

Determines which USDT perpetual futures symbols had data available on specific
historical dates by probing Binance Vision S3 for file existence.

Usage:
    # Check single symbol on specific date
    uv run historical_probe.py --symbol BTCUSDT --date 2024-01-15

    # Check all symbols on specific date
    uv run historical_probe.py --date 2024-01-15 --all

    # Check symbol across date range
    uv run historical_probe.py --symbol BTCUSDT --start 2024-01-01 --end 2024-01-31
"""

import argparse
import json
import urllib.request
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Dict, List


def check_symbol_availability(
    symbol: str, target_date: date, market_type: str = "um", interval: str = "1m"
) -> Dict:
    """
    Check if a specific symbol had data available on a given date.

    Args:
        symbol: Futures symbol (e.g., "BTCUSDT")
        target_date: Date to check
        market_type: "um" (USDT-Margined) or "cm" (Coin-Margined)
        interval: Timeframe interval (e.g., "1m", "1h")

    Returns:
        Dict with availability status, URL, and response details
    """
    # Construct expected file URL
    date_str = target_date.strftime("%Y-%m-%d")
    filename = f"{symbol}-{interval}-{date_str}.zip"
    url = f"https://data.binance.vision/data/futures/{market_type}/daily/klines/{symbol}/{interval}/{filename}"

    # Try HEAD request to check file existence without downloading
    request = urllib.request.Request(url, method="HEAD")

    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            return {
                "symbol": symbol,
                "date": date_str,
                "available": True,
                "url": url,
                "status_code": response.status,
                "content_length": response.headers.get("Content-Length"),
                "last_modified": response.headers.get("Last-Modified"),
            }
    except urllib.error.HTTPError as e:
        return {
            "symbol": symbol,
            "date": date_str,
            "available": False,
            "url": url,
            "status_code": e.code,
            "error": str(e),
        }
    except Exception as e:
        return {
            "symbol": symbol,
            "date": date_str,
            "available": False,
            "url": url,
            "status_code": None,
            "error": str(e),
        }


def get_available_symbols_for_date(
    target_date: date,
    symbols: List[str],
    market_type: str = "um",
    interval: str = "1m",
    verbose: bool = True,
) -> Dict:
    """
    Check which symbols from a list had data on a specific date.

    Args:
        target_date: Date to check
        symbols: List of symbols to check
        market_type: "um" or "cm"
        interval: Timeframe interval
        verbose: Print progress

    Returns:
        Dict with available/unavailable symbol lists and metadata
    """
    available = []
    unavailable = []
    errors = []

    if verbose:
        print(f"Checking {len(symbols)} symbols for {target_date.isoformat()}...")
        print()

    for i, symbol in enumerate(symbols, 1):
        if verbose and i % 50 == 0:
            print(f"  Progress: {i}/{len(symbols)} symbols checked...")

        result = check_symbol_availability(symbol, target_date, market_type, interval)

        if result["available"]:
            available.append(result)
        elif result["status_code"] == 404:
            unavailable.append(result)
        else:
            errors.append(result)

    if verbose:
        print()
        print("✅ Availability check complete!")
        print(f"   Available: {len(available)} symbols")
        print(f"   Not available: {len(unavailable)} symbols")
        print(f"   Errors: {len(errors)} symbols")

    return {
        "date": target_date.isoformat(),
        "total_symbols_checked": len(symbols),
        "available_count": len(available),
        "unavailable_count": len(unavailable),
        "error_count": len(errors),
        "available_symbols": [r["symbol"] for r in available],
        "unavailable_symbols": [r["symbol"] for r in unavailable],
        "error_symbols": [r["symbol"] for r in errors],
        "details": {"available": available, "unavailable": unavailable, "errors": errors},
    }


def generate_historical_snapshot(
    symbol: str, start_date: date, end_date: date, market_type: str = "um", interval: str = "1m"
) -> Dict:
    """
    Generate availability snapshot for a symbol across date range.

    Args:
        symbol: Futures symbol to check
        start_date: Start of date range
        end_date: End of date range
        market_type: "um" or "cm"
        interval: Timeframe interval

    Returns:
        Dict with availability timeline and gap analysis
    """
    print(f"Generating historical snapshot: {symbol}")
    print(f"Date range: {start_date.isoformat()} to {end_date.isoformat()}")
    print()

    timeline = []
    gaps = []
    current = start_date

    total_days = (end_date - start_date).days + 1
    day_count = 0

    while current <= end_date:
        day_count += 1
        if day_count % 10 == 0:
            print(f"  Progress: {day_count}/{total_days} days checked...")

        result = check_symbol_availability(symbol, current, market_type, interval)
        timeline.append(result)

        if not result["available"]:
            gaps.append(current.isoformat())

        current += timedelta(days=1)

    print()
    available_count = sum(1 for r in timeline if r["available"])
    gap_count = len(gaps)

    print("✅ Snapshot complete!")
    print(f"   Total days: {total_days}")
    print(f"   Available: {available_count} days ({available_count / total_days * 100:.1f}%)")
    print(f"   Gaps: {gap_count} days ({gap_count / total_days * 100:.1f}%)")

    return {
        "symbol": symbol,
        "start_date": start_date.isoformat(),
        "end_date": end_date.isoformat(),
        "total_days": total_days,
        "available_count": available_count,
        "gap_count": gap_count,
        "availability_percentage": round(available_count / total_days * 100, 2),
        "gaps": gaps,
        "timeline": timeline,
    }


def load_discovered_symbols() -> List[str]:
    """Load perpetual symbols from futures_discovery.py output."""
    json_file = Path(__file__).parent / "discovered_futures_symbols.json"

    if not json_file.exists():
        raise FileNotFoundError(
            f"Symbol discovery file not found: {json_file}\n"
            "Run `uv run futures_discovery.py` first to discover symbols."
        )

    with open(json_file) as f:
        data = json.load(f)

    return data["perpetual_contracts"]


def main():
    """Main execution with CLI argument parsing."""
    parser = argparse.ArgumentParser(
        description="Check historical availability of USDT futures symbols"
    )
    parser.add_argument("--symbol", help="Futures symbol to check (e.g., BTCUSDT)")
    parser.add_argument("--date", help="Single date to check (YYYY-MM-DD)")
    parser.add_argument("--start", help="Start date for range check (YYYY-MM-DD)")
    parser.add_argument("--end", help="End date for range check (YYYY-MM-DD)")
    parser.add_argument("--all", action="store_true", help="Check all discovered symbols")
    parser.add_argument("--interval", default="1m", help="Timeframe interval (default: 1m)")

    args = parser.parse_args()

    # Validate arguments
    if not args.date and not (args.start and args.end):
        parser.error("Either --date or both --start and --end must be specified")

    # Parse dates
    if args.date:
        target_date = datetime.strptime(args.date, "%Y-%m-%d").date()
    else:
        start_date = datetime.strptime(args.start, "%Y-%m-%d").date()
        end_date = datetime.strptime(args.end, "%Y-%m-%d").date()

    # Single date check
    if args.date:
        if args.all:
            # Check all symbols on specific date
            symbols = load_discovered_symbols()
            result = get_available_symbols_for_date(target_date, symbols, interval=args.interval)

            # Save to JSON
            output_file = Path(__file__).parent / f"availability_{args.date}.json"
            with open(output_file, "w") as f:
                json.dump(result, f, indent=2)

            print()
            print(f"✅ Results saved to: {output_file}")

        elif args.symbol:
            # Check single symbol on single date
            result = check_symbol_availability(args.symbol, target_date, interval=args.interval)

            print(json.dumps(result, indent=2))

        else:
            parser.error("Either --symbol or --all must be specified with --date")

    # Date range check
    else:
        if not args.symbol:
            parser.error("--symbol is required for date range checks")

        result = generate_historical_snapshot(
            args.symbol, start_date, end_date, interval=args.interval
        )

        # Save to JSON
        output_file = Path(__file__).parent / f"snapshot_{args.symbol}_{args.start}_{args.end}.json"
        with open(output_file, "w") as f:
            json.dump(result, f, indent=2)

        print()
        print(f"✅ Results saved to: {output_file}")


if __name__ == "__main__":
    main()
