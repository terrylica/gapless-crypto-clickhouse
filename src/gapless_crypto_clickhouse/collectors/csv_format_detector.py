"""
CSV Format Detector for Binance kline data.

Detects whether a CSV file is in spot format (11 columns, no header) or
futures format (12 columns, with header row).

Usage:
    from gapless_crypto_clickhouse.collectors.csv_format_detector import detect_csv_format

    format_type = detect_csv_format("BTCUSDT-1h-2024-01.csv")
    # Returns: "spot" or "futures"
"""

import logging
from pathlib import Path
from typing import Literal

logger = logging.getLogger(__name__)


def detect_csv_format(csv_path: Path) -> Literal["spot", "futures"]:
    """
    Detect CSV format by reading first line.

    Binance CSV formats:
        - Spot: 11 columns, no header (starts with timestamp)
        - Futures: 12 columns, with header row (starts with "open_time")

    Detection strategy:
        1. Read first line
        2. Check if first field is "open_time" (futures header)
        3. If not, assume spot format (no header, starts with timestamp)

    Args:
        csv_path: Path to CSV file

    Returns:
        "spot" or "futures"

    Raises:
        FileNotFoundError: If CSV file doesn't exist
        ValueError: If first line is empty or unreadable
        RuntimeError: If format detection fails

    Examples:
        >>> detect_csv_format(Path("BTCUSDT-1h-2024-01.csv"))
        "spot"

        >>> detect_csv_format(Path("BTCUSDT-1h-2024-01-futures.csv"))
        "futures"
    """
    if not csv_path.exists():
        raise FileNotFoundError(f"CSV file not found: {csv_path}")

    try:
        with open(csv_path, "r", encoding="utf-8") as f:
            first_line = f.readline().strip()

        if not first_line:
            raise ValueError(f"CSV file is empty: {csv_path}")

        # Futures CSV has header row starting with "open_time"
        # Spot CSV has no header, first line starts with timestamp (numeric)
        if first_line.startswith("open_time"):
            logger.debug(f"Detected futures format (header present): {csv_path}")
            return "futures"
        else:
            # Verify it's a valid spot format (first field should be numeric timestamp)
            first_field = first_line.split(",")[0]
            try:
                int(first_field)  # Timestamp should be parseable as integer
                logger.debug(f"Detected spot format (no header, timestamp first): {csv_path}")
                return "spot"
            except ValueError as e:
                raise RuntimeError(
                    f"Failed to detect format for {csv_path}. "
                    f"First field '{first_field}' is neither 'open_time' (futures header) "
                    f"nor a valid timestamp (spot format). Error: {e}"
                ) from e

    except (OSError, UnicodeDecodeError) as e:
        raise RuntimeError(f"Failed to read CSV file {csv_path}: {e}") from e


def count_csv_columns(csv_path: Path, has_header: bool = False) -> int:
    """
    Count columns in CSV file by reading first data line.

    Args:
        csv_path: Path to CSV file
        has_header: If True, skip first line (header)

    Returns:
        Number of columns

    Raises:
        FileNotFoundError: If CSV file doesn't exist
        ValueError: If CSV has no data lines

    Examples:
        >>> count_csv_columns(Path("spot.csv"), has_header=False)
        11

        >>> count_csv_columns(Path("futures.csv"), has_header=True)
        12
    """
    if not csv_path.exists():
        raise FileNotFoundError(f"CSV file not found: {csv_path}")

    try:
        with open(csv_path, "r", encoding="utf-8") as f:
            if has_header:
                f.readline()  # Skip header
            first_data_line = f.readline().strip()

        if not first_data_line:
            raise ValueError(f"CSV file has no data lines: {csv_path}")

        columns = first_data_line.split(",")
        return len(columns)

    except (OSError, UnicodeDecodeError) as e:
        raise RuntimeError(f"Failed to read CSV file {csv_path}: {e}") from e
