#!/usr/bin/env python3
"""Send Pushover Notification - ADR-0037

Reads validation results and sends summary notification via Pushover API.
"""

import argparse
import json
import os
import sys
from pathlib import Path

import requests


def format_pushover_message(results_dir: str, release_version: str, release_url: str) -> tuple[str, str]:
    """Format Pushover notification from validation results.

    Returns (title, message) tuple with HTML formatting.
    """
    # Load validation results
    results_path = Path(results_dir)
    json_files = list(results_path.glob("*-result.json"))

    if len(json_files) == 0:
        return (
            f"Release Validation: {release_version}",
            "❌ No validation results found"
        )

    # Parse results
    validation_results = []
    for json_file in json_files:
        try:
            with open(json_file) as f:
                data = json.load(f)
                validation_results.append(data)
        except Exception as e:
            print(f"Warning: Failed to parse {json_file.name}: {e}", file=sys.stderr)

    # Calculate overall status
    all_passed = all(r.get("status") == "passed" for r in validation_results)
    status_emoji = "✅" if all_passed else "❌"

    # Build message
    title = f"{status_emoji} Release Validation: {release_version}"

    message_parts = []
    for result in validation_results:
        validation_type = result.get("validation_type", "unknown")
        status = result.get("status", "unknown")
        status_icon = "✅" if status == "passed" else "❌"

        if validation_type == "github_release":
            message_parts.append(f"{status_icon} <b>GitHub Release</b>: {status}")
        elif validation_type == "pypi_version":
            message_parts.append(f"{status_icon} <b>PyPI Version</b>: {status}")
        elif validation_type == "production_health":
            message_parts.append(f"{status_icon} <b>Production Health</b>: {status}")
        else:
            message_parts.append(f"{status_icon} <b>{validation_type}</b>: {status}")

        # Add error message if failed
        if status != "passed" and result.get("error_message"):
            message_parts.append(f"  → {result['error_message']}")

    message_parts.append(f"\n<a href='{release_url}'>View Release</a>")

    message = "\n".join(message_parts)

    return (title, message)


def send_pushover_notification(title: str, message: str, url: str) -> bool:
    """Send notification via Pushover API.

    Returns True if successful, False otherwise.
    """
    app_token = os.getenv("PUSHOVER_APP_TOKEN")
    user_key = os.getenv("PUSHOVER_USER_KEY")

    if not app_token or not user_key:
        print("Error: PUSHOVER_APP_TOKEN or PUSHOVER_USER_KEY not set", file=sys.stderr)
        return False

    try:
        response = requests.post(
            "https://api.pushover.net/1/messages.json",
            data={
                "token": app_token,
                "user": user_key,
                "title": title,
                "message": message,
                "url": url,
                "html": 1,
            },
            timeout=30,
        )

        response.raise_for_status()
        return True

    except requests.RequestException as e:
        print(f"Error: Pushover API request failed: {e}", file=sys.stderr)
        return False


def main():
    parser = argparse.ArgumentParser(description="Send Pushover Notification")
    parser.add_argument("--results-dir", required=True, help="Directory containing validation JSON files")
    parser.add_argument("--release-version", required=True, help="Release version (e.g., v9.0.0)")
    parser.add_argument("--release-url", required=True, help="GitHub Release URL")
    args = parser.parse_args()

    print(f"[Pushover Notification] Sending alert for release {args.release_version}...")

    # Format message
    title, message = format_pushover_message(args.results_dir, args.release_version, args.release_url)

    print(f"Title: {title}")
    print(f"Message:\n{message}\n")

    # Send notification
    success = send_pushover_notification(title, message, args.release_url)

    if success:
        print("✅ Pushover notification sent successfully")
        return 0
    else:
        print("❌ Failed to send Pushover notification")
        return 1


if __name__ == "__main__":
    sys.exit(main())
