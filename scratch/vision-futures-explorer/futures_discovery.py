#!/usr/bin/env python3
# /// script
# dependencies = [
#   "urllib3>=2.0.0",
# ]
# ///
"""
Binance Vision Futures Symbol Discovery

Enumerates all USDT perpetual futures symbols from Binance Vision S3 bucket.
Uses S3 bucket listing API to discover all available symbols without requiring
API keys or rate limiting concerns.

Usage:
    uv run futures_discovery.py

Output:
    JSON file with all discovered perpetual futures symbols
"""

import json
import urllib.request
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple
from xml.etree import ElementTree


def discover_all_futures_symbols(
    market_type: str = "um", granularity: str = "daily"
) -> Tuple[List[str], Dict]:
    """
    Discover all USDT futures symbols from Binance Vision S3 bucket.

    Args:
        market_type: "um" (USDT-Margined) or "cm" (Coin-Margined)
        granularity: "daily" or "monthly"

    Returns:
        Tuple of (symbols_list, metadata_dict)
        - symbols_list: All symbols found
        - metadata_dict: Discovery statistics and timing
    """
    base_url = "https://s3-ap-northeast-1.amazonaws.com/data.binance.vision"
    prefix = f"data/futures/{market_type}/{granularity}/klines/"

    all_symbols = []
    request_count = 0
    marker = None
    start_time = datetime.now()

    # S3 XML namespace
    ns = {"s3": "http://s3.amazonaws.com/doc/2006-03-01/"}

    print(f"Discovering {market_type.upper()} futures symbols from Binance Vision...")
    print(f"Prefix: {prefix}")
    print()

    while True:
        # Build request URL with optional marker for pagination
        params = {"prefix": prefix, "delimiter": "/"}
        if marker:
            params["marker"] = marker

        # Construct query string
        query_string = "&".join(f"{k}={v}" for k, v in params.items())
        url = f"{base_url}?{query_string}"

        request_count += 1
        print(f"Request {request_count}: Fetching symbols...")

        # Fetch S3 listing
        try:
            with urllib.request.urlopen(url, timeout=30) as response:
                xml_data = response.read()
        except Exception as e:
            raise RuntimeError(f"Failed to fetch S3 listing: {e}")

        # Parse XML response
        root = ElementTree.fromstring(xml_data)

        # Extract symbol directories from CommonPrefixes
        batch_symbols = []
        for prefix_elem in root.findall(".//s3:CommonPrefixes/s3:Prefix", ns):
            # Example: "data/futures/um/daily/klines/BTCUSDT/"
            path = prefix_elem.text
            symbol = path.rstrip("/").split("/")[-1]
            batch_symbols.append(symbol)

        all_symbols.extend(batch_symbols)
        print(f"  Found {len(batch_symbols)} symbols (total: {len(all_symbols)})")

        # Check if more results exist (pagination)
        is_truncated_elem = root.find(".//s3:IsTruncated", ns)
        is_truncated = is_truncated_elem is not None and is_truncated_elem.text == "true"

        if not is_truncated:
            break

        # Get next marker for pagination
        next_marker_elem = root.find(".//s3:NextMarker", ns)
        if next_marker_elem is not None:
            marker = next_marker_elem.text
        else:
            # Sometimes NextMarker is not provided, use last symbol as marker
            if batch_symbols:
                marker = f"{prefix}{batch_symbols[-1]}/"
            else:
                break

    duration = (datetime.now() - start_time).total_seconds()

    # Build metadata
    metadata = {
        "discovery_timestamp": datetime.now().isoformat(),
        "market_type": market_type,
        "granularity": granularity,
        "total_symbols": len(all_symbols),
        "request_count": request_count,
        "duration_seconds": round(duration, 2),
        "s3_prefix": prefix,
    }

    print()
    print("✅ Discovery complete!")
    print(f"   Total symbols: {len(all_symbols)}")
    print(f"   Requests made: {request_count}")
    print(f"   Duration: {duration:.2f}s")

    return all_symbols, metadata


def classify_symbol(symbol: str) -> Dict:
    """
    Classify futures symbol as perpetual or delivery contract.

    Args:
        symbol: Futures symbol (e.g., "BTCUSDT" or "BTCUSDT_231229")

    Returns:
        Classification dict with type, base_symbol, expiry_date (if applicable)
    """
    if "_" in symbol:
        # Delivery contract: BTCUSDT_231229
        parts = symbol.rsplit("_", 1)
        base_symbol = parts[0]
        date_str = parts[1]

        try:
            # Parse expiry date (YYMMDD format)
            expiry_date = datetime.strptime(date_str, "%y%m%d").date()
            is_expired = expiry_date < datetime.now().date()

            return {
                "symbol": symbol,
                "type": "delivery",
                "base_symbol": base_symbol,
                "expiry_date": expiry_date.isoformat(),
                "is_expired": is_expired,
            }
        except ValueError:
            # Invalid date format, treat as perpetual with special suffix
            return {
                "symbol": symbol,
                "type": "perpetual_variant",
                "base_symbol": base_symbol,
                "expiry_date": None,
                "is_expired": False,
            }
    else:
        # Perpetual contract: BTCUSDT
        return {
            "symbol": symbol,
            "type": "perpetual",
            "base_symbol": symbol,
            "expiry_date": None,
            "is_expired": False,
        }


def filter_perpetual_contracts(symbols: List[str]) -> List[str]:
    """
    Filter list to include only perpetual contracts (exclude delivery contracts).

    Args:
        symbols: List of all futures symbols

    Returns:
        Filtered list containing only perpetual contracts
    """
    perpetual = []

    for symbol in symbols:
        classification = classify_symbol(symbol)
        if classification["type"] == "perpetual":
            perpetual.append(symbol)

    return perpetual


def main():
    """Main execution: discover symbols, classify, and save to JSON."""

    # Discover all USDT-Margined futures symbols
    all_symbols, metadata = discover_all_futures_symbols(market_type="um", granularity="daily")

    # Classify each symbol
    print()
    print("Classifying symbols...")
    classified = [classify_symbol(s) for s in all_symbols]

    # Separate perpetual vs delivery
    perpetual = [c for c in classified if c["type"] == "perpetual"]
    delivery = [c for c in classified if c["type"] == "delivery"]

    print(f"  Perpetual contracts: {len(perpetual)}")
    print(f"  Delivery contracts: {len(delivery)}")

    # Build output structure
    output = {
        "metadata": metadata,
        "summary": {
            "total_symbols": len(all_symbols),
            "perpetual_count": len(perpetual),
            "delivery_count": len(delivery),
        },
        "perpetual_contracts": sorted([s["symbol"] for s in perpetual]),
        "delivery_contracts": sorted([s["symbol"] for s in delivery]),
        "classified_symbols": sorted(classified, key=lambda x: x["symbol"]),
    }

    # Save to JSON file
    output_file = Path(__file__).parent / "discovered_futures_symbols.json"
    with open(output_file, "w") as f:
        json.dump(output, f, indent=2)

    print()
    print(f"✅ Results saved to: {output_file}")
    print()
    print("Sample perpetual contracts:")
    for symbol in sorted([s["symbol"] for s in perpetual])[:10]:
        print(f"  - {symbol}")

    if len(perpetual) > 10:
        print(f"  ... and {len(perpetual) - 10} more")


if __name__ == "__main__":
    main()
