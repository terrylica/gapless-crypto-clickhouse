#!/bin/bash
# CLI Usage Examples for Gapless Crypto Data
#
# This script demonstrates various ways to use the gapless-crypto-data CLI tool
# for ultra-fast cryptocurrency data collection and gap filling.
#
# IMPORTANT: All examples use safe historical date ranges to avoid 404 errors.
# Avoid using future dates or dates before symbol listing dates.

echo "🚀 Gapless Crypto Data - CLI Usage Examples"
echo "=========================================="
echo

echo "📋 Basic Usage Examples:"
echo

echo "1. Default collection (SOLUSDT, all timeframes, full coverage):"
echo "   uv run gapless-crypto-data"
echo

echo "2. Custom symbol and timeframes:"
echo "   uv run gapless-crypto-data --symbol BTCUSDT --timeframes 1h,4h"
echo

echo "3. Multiple symbols (native multi-symbol support):"
echo "   uv run gapless-crypto-data --symbol BTCUSDT,ETHUSDT,SOLUSDT --timeframes 1h,4h"
echo

echo "4. Safe historical date range (recommended):"
echo "   uv run gapless-crypto-data --symbol ETHUSDT --timeframes 1m,5m --start 2022-01-01 --end 2022-01-31"
echo

echo "5. Multiple timeframes with safe range:"
echo "   uv run gapless-crypto-data --symbol ADAUSDT --timeframes 1m,3m,5m,15m,30m,1h,2h,4h --start 2023-01-01 --end 2023-06-30"
echo

echo "6. Gap filling in current directory:"
echo "   uv run gapless-crypto-data --fill-gaps"
echo

echo "7. Gap filling in specific directory:"
echo "   uv run gapless-crypto-data --fill-gaps --directory ./data"
echo

echo "🔧 Advanced Examples:"
echo

echo "8. High-frequency data collection:"
echo "   uv run gapless-crypto-data --symbol BTCUSDT --timeframes 1m --start 2024-01-01 --end 2024-01-07"
echo

echo "9. Multi-asset collection (native multi-symbol - recommended):"
echo "   uv run gapless-crypto-data --symbol BTCUSDT,ETHUSDT,SOLUSDT,ADAUSDT --timeframes 1h,4h --start 2024-01-01 --end 2024-01-31"
echo

echo "10. Multi-asset with error handling:"
echo "    uv run gapless-crypto-data --symbol BTCUSDT,INVALIDCOIN,ETHUSDT --timeframes 1h"
echo "    # Continues with valid symbols, reports failed ones"
echo

echo "📊 Performance Benchmarks:"
echo

echo "11. Quick demo (small date range for testing):"
echo "    uv run gapless-crypto-data --symbol BTCUSDT --timeframes 1h --start 2024-01-01 --end 2024-01-02"
echo

echo "12. Full month collection (typical production use):"
echo "    uv run gapless-crypto-data --symbol SOLUSDT --timeframes 1m,5m,1h --start 2024-01-01 --end 2024-01-31"
echo

echo "🎯 Workflow Examples:"
echo

echo "13. Complete data pipeline:"
echo "    # Step 1: Collect data"
echo "    uv run gapless-crypto-data --symbol ETHUSDT --timeframes 1h --start 2024-01-01 --end 2024-01-31"
echo "    "
echo "    # Step 2: Fill any gaps"
echo "    uv run gapless-crypto-data --fill-gaps"
echo "    "
echo "    # Step 3: Verify results"
echo "    ls -la *.csv"
echo

echo "14. Batch processing with gap filling (native multi-symbol):"
echo "    # Collect data for multiple symbols (single command)"
echo "    uv run gapless-crypto-data --symbol BTCUSDT,ETHUSDT,SOLUSDT,ADAUSDT,DOTUSDT --timeframes 1h,4h --start 2024-01-01 --end 2024-01-31"
echo "    "
echo "    # Fill gaps for all collected data"
echo "    echo \"Filling gaps...\""
echo "    uv run gapless-crypto-data --fill-gaps"
echo

echo "15. Legacy batch processing (for comparison):"
echo "    # Old loop-based approach (still works but slower)"
echo "    symbols=(BTCUSDT ETHUSDT SOLUSDT ADAUSDT DOTUSDT)"
echo "    for symbol in \"\${symbols[@]}\"; do"
echo "      echo \"Collecting \$symbol...\""
echo "      uv run gapless-crypto-data --symbol \$symbol --timeframes 1h,4h --start 2024-01-01 --end 2024-01-31"
echo "    done"
echo

echo "💡 Pro Tips:"
echo

echo "16. Use environment variables for repeated parameters:"
echo "    export GAPLESS_SYMBOL=BTCUSDT"
echo "    export GAPLESS_START=2024-01-01"
echo "    export GAPLESS_END=2024-01-31"
echo "    # Note: Environment variable support would need to be implemented"
echo

echo "17. Pipe output for logging:"
echo "    uv run gapless-crypto-data --symbol BTCUSDT --timeframes 1h | tee collection.log"
echo

echo "18. Background processing (multi-symbol):"
echo "    nohup uv run gapless-crypto-data --symbol BTCUSDT,ETHUSDT,SOLUSDT --timeframes 1m --start 2023-01-01 --end 2023-12-31 > collection.log 2>&1 &"
echo

echo "🚀 Performance Notes:"
echo "- Ultra-fast: 22x faster than API-based collection"
echo "- Multi-symbol: Native support for comma-separated symbols"
echo "- Parallel downloads: Multiple monthly files downloaded concurrently"
echo "- Zero gaps: Automatic gap detection and authentic API-first validation"
echo "- Production ready: Atomic file operations prevent corruption"
echo

echo "📚 Getting Help:"
echo "   uv run gapless-crypto-data --help"
echo

echo "Demo completed! Try running any of the above commands to see the tool in action."
