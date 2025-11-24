#!/usr/bin/env python3
"""GitHub Release Validation - ADR-0037

Validates that a GitHub release exists and is published.
Based on Agent 5's 6-stage validation with exponential backoff.
"""

import argparse
import json
import subprocess
import sys
import time
from datetime import datetime, timezone


def validate_github_release(version: str, repository: str, max_retries: int = 3) -> dict:
    """Validate GitHub release exists and is published.

    Returns structured validation result for ClickHouse storage.
    """
    result = {
        "validation_type": "github_release",
        "release_version": version,
        "status": "failed",
        "error_message": "",
        "duration_ms": 0,
        "validation_context": {},
    }

    start_time = datetime.now(timezone.utc)

    # Retry with exponential backoff (5s → 10s → 20s)
    retry_delay = 5
    for attempt in range(1, max_retries + 1):
        try:
            # Run gh release view with JSON output
            cmd = ["gh", "release", "view", version, "--repo", repository, "--json",
                   "tagName,name,createdAt,publishedAt,url,isDraft,isPrerelease,targetCommitish,assets"]

            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=30)

            if proc.returncode == 0:
                # Parse release data
                release_data = json.loads(proc.stdout)

                # Validate release is published
                is_draft = release_data.get("isDraft", True)
                published_at = release_data.get("publishedAt")

                if is_draft:
                    result["error_message"] = "Release is still a draft"
                    break

                if not published_at or published_at == "null":
                    result["error_message"] = "Release has no published timestamp"
                    break

                # Success
                result["status"] = "passed"
                result["validation_context"] = {
                    "tag_name": release_data.get("tagName", ""),
                    "release_url": release_data.get("url", ""),
                    "published_at": published_at,
                    "target_commit": release_data.get("targetCommitish", ""),
                    "asset_count": str(len(release_data.get("assets", []))),
                }
                break

            # Retry on failure
            if attempt < max_retries:
                time.sleep(retry_delay)
                retry_delay *= 2
            else:
                result["error_message"] = f"Release not found after {max_retries} attempts: {proc.stderr}"

        except subprocess.TimeoutExpired:
            result["error_message"] = f"GitHub CLI timeout on attempt {attempt}"
        except json.JSONDecodeError as e:
            result["error_message"] = f"Failed to parse GitHub CLI output: {e}"
        except Exception as e:
            result["error_message"] = f"Unexpected error: {e}"

    end_time = datetime.now(timezone.utc)
    result["duration_ms"] = int((end_time - start_time).total_seconds() * 1000)

    return result


def main():
    parser = argparse.ArgumentParser(description="Validate GitHub Release")
    parser.add_argument("--version", required=True, help="Release version (e.g., v9.0.0)")
    parser.add_argument("--repository", required=True, help="Repository (e.g., terrylica/repo)")
    parser.add_argument("--output", required=True, help="Output JSON file path")
    args = parser.parse_args()

    print(f"[GitHub Release Validation] Checking {args.version} in {args.repository}...")

    result = validate_github_release(args.version, args.repository)

    # Write JSON result
    with open(args.output, "w") as f:
        json.dump(result, f, indent=2)

    # Print status
    if result["status"] == "passed":
        print(f"✅ GitHub Release validation passed ({result['duration_ms']}ms)")
        return 0
    else:
        print(f"❌ GitHub Release validation failed: {result['error_message']}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
