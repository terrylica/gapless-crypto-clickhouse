#!/usr/bin/env python3
"""PyPI Version Validation - ADR-0037

Validates that PyPI package version matches the expected release tag.
Queries PyPI JSON API for current published version.
"""

import argparse
import json
import sys
from datetime import datetime, timezone

import requests


def validate_pypi_version(package_name: str, expected_version: str) -> dict:
    """Validate PyPI package version matches expected release version.

    Returns structured validation result for ClickHouse storage.
    """
    result = {
        "validation_type": "pypi_version",
        "release_version": expected_version,
        "status": "failed",
        "error_message": "",
        "duration_ms": 0,
        "validation_context": {},
    }

    start_time = datetime.now(timezone.utc)

    try:
        # Query PyPI JSON API
        url = f"https://pypi.org/pypi/{package_name}/json"
        response = requests.get(url, timeout=30)
        response.raise_for_status()

        data = response.json()
        actual_version = data["info"]["version"]

        # Strip 'v' prefix from expected version if present
        expected_clean = expected_version.lstrip("v")

        if actual_version == expected_clean:
            result["status"] = "passed"
            result["validation_context"] = {
                "expected_version": expected_clean,
                "actual_version": actual_version,
                "package_name": package_name,
                "pypi_url": f"https://pypi.org/project/{package_name}/{actual_version}/",
            }
        else:
            result["error_message"] = f"Version mismatch: expected {expected_clean}, found {actual_version}"
            result["validation_context"] = {
                "expected_version": expected_clean,
                "actual_version": actual_version,
                "package_name": package_name,
            }

    except requests.HTTPError as e:
        if e.response.status_code == 404:
            result["error_message"] = f"Package {package_name} not found on PyPI"
        else:
            result["error_message"] = f"PyPI HTTP error: {e.response.status_code}"
    except requests.RequestException as e:
        result["error_message"] = f"PyPI request failed: {str(e)}"
    except KeyError as e:
        result["error_message"] = f"Unexpected PyPI response format: missing {e}"
    except Exception as e:
        result["error_message"] = f"Unexpected error: {str(e)}"

    end_time = datetime.now(timezone.utc)
    result["duration_ms"] = int((end_time - start_time).total_seconds() * 1000)

    return result


def main():
    parser = argparse.ArgumentParser(description="Validate PyPI Package Version")
    parser.add_argument("--expected-version", required=True, help="Expected version (e.g., v9.0.0 or 9.0.0)")
    parser.add_argument("--package", required=True, help="Package name on PyPI")
    parser.add_argument("--output", required=True, help="Output JSON file path")
    args = parser.parse_args()

    print(f"[PyPI Version Validation] Checking {args.package} for version {args.expected_version}...")

    result = validate_pypi_version(args.package, args.expected_version)

    # Write JSON result
    with open(args.output, "w") as f:
        json.dump(result, f, indent=2)

    # Print status
    if result["status"] == "passed":
        print(f"✅ PyPI version validation passed ({result['duration_ms']}ms)")
        return 0
    else:
        print(f"❌ PyPI version validation failed: {result['error_message']}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
