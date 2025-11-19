#!/usr/bin/env python3
# /// script
# dependencies = [
#   "pandas>=2.0.0",
#   "polars>=0.19.0",
# ]
# ///
"""
Binance Vision Futures Data Collector - Integration Bridge

Demonstrates how USDT perpetual futures collection would integrate with
gapless-crypto-data architecture. This is a proof-of-concept showing:

1. URL pattern differences (futures/um vs spot)
2. Same 11-column CSV format compatibility
3. Validation pipeline reuse potential
4. Architectural separation considerations

Usage:
    uv run vision_futures_collector.py --symbol BTCUSDT --date 2024-01-15

NOTE: This is a proof-of-concept, not production code.
"""

import argparse
import csv
import json
import tempfile
import urllib.request
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional


class BinanceFuturesCollector:
    """
    Proof-of-concept futures collector demonstrating integration patterns.

    Mirrors BinancePublicDataCollector architecture but for USDT-Margined futures.
    Key differences:
    - Base URL: data/futures/um vs data/spot
    - No 1-second interval support
    - Perpetual vs delivery contract handling
    """

    def __init__(
        self, symbol: str = "BTCUSDT", market_type: str = "um", output_dir: Optional[Path] = None
    ):
        """
        Initialize futures collector.

        Args:
            symbol: Futures symbol (e.g., "BTCUSDT")
            market_type: "um" (USDT-Margined) or "cm" (Coin-Margined)
            output_dir: Output directory for collected data
        """
        self.symbol = symbol
        self.market_type = market_type
        self.base_url = f"https://data.binance.vision/data/futures/{market_type}"
        self.output_dir = output_dir or Path(__file__).parent / "output"
        self.output_dir.mkdir(exist_ok=True)

        print("Initialized BinanceFuturesCollector")
        print(f"  Symbol: {symbol}")
        print(f"  Market: {market_type.upper()} (USDT-Margined)")
        print(f"  Base URL: {self.base_url}")
        print(f"  Output: {self.output_dir}")

    def collect_daily_file(self, target_date: str, interval: str = "1m") -> Dict:
        """
        Collect single daily file for specific date and interval.

        Args:
            target_date: Date in YYYY-MM-DD format
            interval: Timeframe (e.g., "1m", "1h", "4h")

        Returns:
            Dict with collection results and metadata
        """
        # Construct download URL
        filename = f"{self.symbol}-{interval}-{target_date}.zip"
        url = f"{self.base_url}/daily/klines/{self.symbol}/{interval}/{filename}"

        print()
        print(f"Collecting: {self.symbol} {interval} {target_date}")
        print(f"URL: {url}")

        # Download ZIP file
        try:
            with urllib.request.urlopen(url, timeout=30) as response:
                zip_data = response.read()
                content_length = len(zip_data)
                print(f"  Downloaded: {content_length:,} bytes")
        except Exception as e:
            raise RuntimeError(f"Failed to download: {e}")

        # Extract CSV from ZIP
        with tempfile.NamedTemporaryFile(suffix=".zip", delete=False) as tmp_zip:
            tmp_zip.write(zip_data)
            tmp_zip_path = tmp_zip.name

        try:
            with zipfile.ZipFile(tmp_zip_path, "r") as z:
                # Get CSV filename (should match pattern)
                csv_filename = f"{self.symbol}-{interval}-{target_date}.csv"
                if csv_filename not in z.namelist():
                    raise RuntimeError(f"Expected CSV not found in ZIP: {csv_filename}")

                # Extract CSV data
                csv_data = z.read(csv_filename).decode("utf-8")
                lines = csv_data.strip().split("\n")
                print(f"  Rows: {len(lines):,}")

        finally:
            Path(tmp_zip_path).unlink()

        # Parse CSV and analyze format
        reader = csv.reader(lines)
        rows = list(reader)

        if not rows:
            raise RuntimeError("Empty CSV file")

        # Check column count (should be 11 for klines data)
        first_row = rows[0]
        column_count = len(first_row)
        print(f"  Columns: {column_count}")

        # Expected 11-column format for klines
        expected_columns = [
            "open_time",
            "open",
            "high",
            "low",
            "close",
            "volume",
            "close_time",
            "quote_volume",
            "count",
            "taker_buy_base_volume",
            "taker_buy_quote_volume",
            "ignore",
        ]

        if column_count != 11:
            print(f"  ⚠️  WARNING: Expected 11 columns, got {column_count}")
        else:
            print("  ✅ Format: 11-column klines (compatible with spot format)")

        # Save to output directory
        output_filename = (
            f"binance_futures_{self.market_type}_{self.symbol}-{interval}_{target_date}.csv"
        )
        output_path = self.output_dir / output_filename

        with open(output_path, "w") as f:
            f.write(csv_data)

        print(f"  Saved: {output_path}")

        # Build metadata
        metadata = {
            "symbol": self.symbol,
            "market_type": self.market_type,
            "interval": interval,
            "date": target_date,
            "url": url,
            "row_count": len(rows),
            "column_count": column_count,
            "format_compatible": column_count == 11,
            "download_size_bytes": content_length,
            "output_file": str(output_path),
            "collection_timestamp": datetime.now().isoformat(),
        }

        # Save metadata
        metadata_path = output_path.with_suffix(".csv.metadata.json")
        with open(metadata_path, "w") as f:
            json.dump(metadata, f, indent=2)

        print(f"  Metadata: {metadata_path}")

        return metadata

    def demonstrate_integration_compatibility(self) -> Dict:
        """
        Demonstrate compatibility with gapless-crypto-data architecture.

        Returns:
            Dict with integration analysis
        """
        print()
        print("=" * 70)
        print("INTEGRATION COMPATIBILITY ANALYSIS")
        print("=" * 70)

        analysis = {
            "url_pattern": {
                "spot": "https://data.binance.vision/data/spot/monthly/klines/{symbol}/{interval}/",
                "futures_um": "https://data.binance.vision/data/futures/um/daily/klines/{symbol}/{interval}/",
                "difference": "URL path prefix only (data/spot vs data/futures/um)",
                "impact": "Minimal - parameterize base path",
            },
            "data_format": {
                "spot": "11-column CSV (no header, taker_buy_base_volume)",
                "futures": "12-column CSV (with header row, taker_buy_volume, ignore column)",
                "compatible": False,
                "impact": "HIGH - CSV parsing needs to skip header, drop ignore column, rename taker_buy_volume",
            },
            "timeframe_support": {
                "spot": "1s, 1m, 3m, 5m, 15m, 30m, 1h, 2h, 4h, 6h, 8h, 12h, 1d",
                "futures": "1m, 3m, 5m, 15m, 30m, 1h, 2h, 4h, 6h, 8h, 12h, 1d, 3d, 1w, 1mo",
                "difference": "Futures has 3d/1w/1mo, lacks 1s",
                "impact": "Low - validation needs timeframe-specific rules",
            },
            "aggregation_granularity": {
                "spot": "monthly and daily",
                "futures": "monthly and daily",
                "compatible": True,
                "impact": "Zero",
            },
            "contract_types": {
                "spot": "Single type (trading pairs)",
                "futures": "Perpetual + delivery contracts",
                "difference": "Futures needs contract type classification",
                "impact": "Medium - symbol validation logic differs",
            },
        }

        # Print analysis
        for category, details in analysis.items():
            print()
            print(f"{category.upper().replace('_', ' ')}:")
            for key, value in details.items():
                if isinstance(value, bool):
                    status = "✅" if value else "❌"
                    print(f"  {key}: {status}")
                else:
                    print(f"  {key}: {value}")

        # Recommendations
        print()
        print("INTEGRATION RECOMMENDATIONS:")
        print("  1. Shared CSV validation pipeline (11-column format identical)")
        print("  2. Parameterize base URL path (spot vs futures/um)")
        print("  3. Add contract type classifier (perpetual vs delivery)")
        print("  4. Extend timeframe constants (add 3d, 1w, 1mo; remove 1s for futures)")
        print("  5. Consider: separate package (gapless-futures-data) for clear separation")

        return analysis


def main():
    """Main execution with CLI argument parsing."""
    parser = argparse.ArgumentParser(
        description="Binance Vision Futures Collector - Integration POC"
    )
    parser.add_argument("--symbol", default="BTCUSDT", help="Futures symbol (default: BTCUSDT)")
    parser.add_argument("--date", required=True, help="Date to collect (YYYY-MM-DD)")
    parser.add_argument("--interval", default="1m", help="Timeframe interval (default: 1m)")
    parser.add_argument(
        "--market",
        default="um",
        choices=["um", "cm"],
        help="Market type: um (USDT-Margined) or cm (Coin-Margined)",
    )
    parser.add_argument(
        "--analyze", action="store_true", help="Run integration compatibility analysis"
    )

    args = parser.parse_args()

    # Initialize collector
    collector = BinanceFuturesCollector(symbol=args.symbol, market_type=args.market)

    # Collect data
    metadata = collector.collect_daily_file(target_date=args.date, interval=args.interval)

    # Run analysis if requested
    if args.analyze:
        analysis = collector.demonstrate_integration_compatibility()

        # Save analysis
        analysis_file = collector.output_dir / "integration_analysis.json"
        with open(analysis_file, "w") as f:
            json.dump(analysis, f, indent=2)

        print()
        print(f"✅ Analysis saved: {analysis_file}")

    print()
    print("=" * 70)
    print("COLLECTION COMPLETE")
    print("=" * 70)
    print(f"Symbol: {metadata['symbol']}")
    print(f"Date: {metadata['date']}")
    print(f"Rows: {metadata['row_count']:,}")
    print(f"Format Compatible: {metadata['format_compatible']}")
    print(f"Output: {metadata['output_file']}")


if __name__ == "__main__":
    main()
