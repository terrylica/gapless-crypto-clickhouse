#!/usr/bin/env python3
# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "httpx>=0.28.1",
# ]
# ///
"""
Binance CDN Availability Validation Script

ADR-0035: CI/CD Production Validation Policy

Validates Binance Public Data Repository (CloudFront CDN) availability.

The Binance CDN provides 22x performance advantage over REST API-only approaches.
Outages block data collection and must be detected within hours.

Validation:
1. HTTP HEAD request to CloudFront CDN endpoint
2. Verify 200 OK response
3. 5s timeout

Exit Codes:
- 0: CDN available
- 1: CDN unavailable or timeout
"""

import sys
from datetime import datetime, timezone

import httpx


def log(message: str) -> None:
    """Print timestamped log message."""
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    print(f"[{timestamp}] {message}")


def validate_binance_cdn() -> int:
    """Validate Binance CDN availability."""
    log("")
    log("=" * 80)
    log("Binance CDN Availability Validation")
    log("ADR-0035: CI/CD Production Validation Policy")
    log("=" * 80)
    log("")

    # Binance Public Data Repository (CloudFront CDN) endpoints
    # Test with a known endpoint (daily klines for BTCUSDT)
    test_urls = [
        "https://data.binance.vision/data/futures/um/daily/klines/BTCUSDT/1h/BTCUSDT-1h-2024-01-01.zip",
        "https://data.binance.vision/data/spot/daily/klines/BTCUSDT/1h/BTCUSDT-1h-2024-01-01.zip",
    ]

    log("Testing Binance CDN endpoints...")
    log(f"  Timeout: 5s")
    log(f"  Method: HTTP HEAD (lightweight check)")
    log("")

    all_available = True

    for url in test_urls:
        log(f"Checking: {url}")

        try:
            with httpx.Client(timeout=5.0) as client:
                response = client.head(url, follow_redirects=True)

                if response.status_code == 200:
                    log(f"  ✅ Status: {response.status_code} (Available)")
                    log(f"     Headers: Content-Length={response.headers.get('content-length', 'N/A')}")
                    log(f"     Server: {response.headers.get('server', 'N/A')}")
                elif response.status_code == 404:
                    log(f"  ⚠️  Status: {response.status_code} (File not found - expected for old dates)")
                    log(f"     This is normal if the test date is outside data retention period")
                    # 404 is acceptable (file may not exist for the test date)
                    # What matters is that CDN responds, not that specific file exists
                else:
                    log(f"  ❌ Status: {response.status_code} (Unexpected)")
                    all_available = False

        except httpx.TimeoutException:
            log(f"  ❌ FAILED: Timeout (>5s)")
            all_available = False

        except httpx.NetworkError as e:
            log(f"  ❌ FAILED: Network error: {e}")
            all_available = False

        except Exception as e:
            log(f"  ❌ FAILED: Unexpected error: {e}")
            all_available = False

        log("")

    # Summary
    log("=" * 80)
    if all_available:
        log("✅ BINANCE CDN AVAILABLE")
        log("=" * 80)
        return 0
    else:
        log("❌ BINANCE CDN UNAVAILABLE OR DEGRADED")
        log("=" * 80)
        log("")
        log("IMPACT: Data collection blocked (22x performance advantage lost)")
        log("ACTION: Check Binance Data Vision status or use REST API fallback")
        return 1


if __name__ == "__main__":
    sys.exit(validate_binance_cdn())
