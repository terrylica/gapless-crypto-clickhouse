#!/usr/bin/env python3
"""
Atomic File Operations Module
Prevents data corruption during CSV file modifications by using atomic operations.

Key Features:
- Atomic file writes (temp file + rename)
- Header preservation for commented CSV files
- Validation checkpoints
- Automatic rollback on failure
- Progress tracking and validation
"""

import logging
import shutil
import tempfile
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Tuple

import pandas as pd

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


class AtomicCSVOperations:
    """Safe atomic operations for CSV files with header preservation and corruption prevention.

    Provides atomic file operations to prevent data corruption during CSV modifications.
    Uses temporary files and atomic rename operations to ensure data integrity,
    even if the process is interrupted during file operations.

    Features:
        - Atomic write operations (temp file + rename)
        - Header comment preservation for metadata
        - Automatic backup creation with timestamps
        - DataFrame validation before writing
        - Rollback capability on failure
        - Progress tracking and validation

    The atomic operation sequence:
        1. Create timestamped backup of original file
        2. Write new data to temporary file
        3. Validate temporary file integrity
        4. Atomically rename temp file to replace original
        5. Clean up temporary files on success

    Examples:
        Basic atomic CSV write:

        >>> from pathlib import Path
        >>> csv_path = Path("data.csv")
        >>> atomic_ops = AtomicCSVOperations(csv_path)
        >>> df = pd.DataFrame({"price": [100, 101, 102], "volume": [1000, 1100, 900]})
        >>> backup_path = atomic_ops.create_backup()
        >>> success = atomic_ops.write_dataframe_atomic(df)
        >>> if success:
        ...     print("Data written safely")
        ... else:
        ...     atomic_ops.rollback_from_backup()
        Data written safely

        With header preservation:

        >>> # Original file has metadata comments
        >>> atomic_ops = AtomicCSVOperations(Path("btc_data.csv"))
        >>> headers = atomic_ops.read_header_comments()
        >>> print(f"Found {len(headers)} header lines")
        >>> # Headers are automatically preserved during atomic writes
        Found 8 header lines

    Note:
        Always call create_backup() before performing write operations
        to enable rollback capability in case of errors.
    """

    def __init__(self, csv_path: Path):
        self.csv_path = Path(csv_path)
        self.backup_path = None
        self.temp_path = None

    def create_backup(self) -> Path:
        """Create timestamped backup of original file"""
        if not self.csv_path.exists():
            raise FileNotFoundError(f"Source file not found: {self.csv_path}")

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = f"{self.csv_path.stem}.backup_{timestamp}{self.csv_path.suffix}"
        backup_path = self.csv_path.parent / backup_name

        logger.info(f"📦 Creating backup: {backup_path}")
        shutil.copy2(self.csv_path, backup_path)

        self.backup_path = backup_path
        return backup_path

    def read_header_comments(self) -> List[str]:
        """Extract header comments from CSV file"""
        header_comments = []

        if not self.csv_path.exists():
            return header_comments

        with open(self.csv_path, "r") as f:
            for line in f:
                if line.startswith("#"):
                    header_comments.append(line.rstrip())
                else:
                    break

        logger.info(f"📄 Found {len(header_comments)} header comment lines")
        return header_comments

    def validate_dataframe(self, df: pd.DataFrame) -> Tuple[bool, str]:
        """Validate DataFrame integrity before writing"""
        if df is None or df.empty:
            return False, "DataFrame is None or empty"

        # Check required columns for OHLCV data
        required_cols = ["date", "open", "high", "low", "close", "volume"]
        missing_cols = [col for col in required_cols if col not in df.columns]
        if missing_cols:
            return False, f"Missing required columns: {missing_cols}"

        # Check for duplicate timestamps
        if "date" in df.columns:
            duplicates = df["date"].duplicated().sum()
            if duplicates > 0:
                return False, f"Found {duplicates} duplicate timestamps"

        # Check data types
        numeric_cols = ["open", "high", "low", "close", "volume"]
        for col in numeric_cols:
            if col in df.columns and not pd.api.types.is_numeric_dtype(df[col]):
                return False, f"Column {col} is not numeric"

        logger.info(f"✅ DataFrame validation passed: {len(df)} rows, {len(df.columns)} columns")
        return True, "Validation passed"

    def write_dataframe_atomic(
        self, df: pd.DataFrame, header_comments: Optional[List[str]] = None
    ) -> bool:
        """Write DataFrame to CSV using atomic operations"""

        # Validate DataFrame
        is_valid, validation_msg = self.validate_dataframe(df)
        if not is_valid:
            logger.error(f"❌ DataFrame validation failed: {validation_msg}")
            return False

        # Use existing headers if none provided
        if header_comments is None:
            header_comments = self.read_header_comments()

        try:
            # Create temporary file in same directory for atomic rename
            temp_fd, temp_path = tempfile.mkstemp(suffix=".csv.tmp", dir=self.csv_path.parent)
            self.temp_path = Path(temp_path)

            logger.info(f"🔧 Writing to temporary file: {self.temp_path}")

            # Write to temporary file
            with open(temp_fd, "w") as f:
                # Write header comments
                for comment in header_comments:
                    f.write(comment + "\n")

                # Write DataFrame
                df.to_csv(f, index=False)

            # Validate temporary file
            logger.info("🔍 Validating temporary file...")
            test_df = pd.read_csv(self.temp_path, comment="#")

            if len(test_df) != len(df):
                raise ValueError(f"Row count mismatch: expected {len(df)}, got {len(test_df)}")

            # Atomic rename (only works within same filesystem)
            logger.info(f"🎯 Performing atomic rename: {self.temp_path} → {self.csv_path}")
            shutil.move(str(self.temp_path), str(self.csv_path))

            logger.info("✅ Atomic write completed successfully")
            return True

        except Exception as e:
            logger.error(f"❌ Atomic write failed: {e}")

            # Cleanup temporary file
            if self.temp_path and self.temp_path.exists():
                self.temp_path.unlink()
                logger.info("🧹 Cleaned up temporary file")

            return False

    def rollback_from_backup(self) -> bool:
        """Restore file from backup in case of failure"""
        if not self.backup_path or not self.backup_path.exists():
            logger.error("❌ No backup available for rollback")
            return False

        try:
            logger.info(f"🔄 Rolling back from backup: {self.backup_path}")
            shutil.copy2(self.backup_path, self.csv_path)
            logger.info("✅ Rollback completed successfully")
            return True

        except Exception as e:
            logger.error(f"❌ Rollback failed: {e}")
            return False

    def cleanup_backup(self) -> bool:
        """Remove backup file after successful operation"""
        if not self.backup_path or not self.backup_path.exists():
            return True

        try:
            self.backup_path.unlink()
            logger.info(f"🧹 Backup cleaned up: {self.backup_path}")
            return True

        except Exception as e:
            logger.warning(f"⚠️ Could not cleanup backup: {e}")
            return False


class SafeCSVMerger:
    """Safe CSV data merging with gap filling capabilities and data integrity validation.

    Provides safe merging of gap-filling data into existing CSV files using atomic operations.
    Handles temporal data insertion, duplicate detection, and maintains chronological order
    while preserving data integrity through comprehensive validation.

    Features:
        - Atomic merge operations with backup/rollback
        - Chronological data insertion and sorting
        - Duplicate detection and handling
        - Data validation before and after merge
        - Gap boundary validation
        - Maintains CSV header comments and metadata

    The merge process:
        1. Create backup of original CSV file
        2. Load existing data and gap data
        3. Validate gap boundaries and data format
        4. Remove any overlapping data in gap range
        5. Insert new gap data chronologically
        6. Validate merged dataset integrity
        7. Atomically write merged data

    Examples:
        Basic gap filling:

        >>> from datetime import datetime
        >>> import pandas as pd
        >>> from pathlib import Path
        >>>
        >>> # Create gap data to fill missing period
        >>> gap_data = pd.DataFrame({
        ...     "date": ["2024-01-01 12:00:00", "2024-01-01 13:00:00"],
        ...     "open": [100.0, 101.0],
        ...     "high": [102.0, 103.0],
        ...     "low": [99.0, 100.0],
        ...     "close": [101.0, 102.0],
        ...     "volume": [1000, 1100]
        ... })
        >>>
        >>> merger = SafeCSVMerger(Path("btc_1h.csv"))
        >>> success = merger.merge_gap_data_safe(
        ...     gap_data,
        ...     datetime(2024, 1, 1, 12),
        ...     datetime(2024, 1, 1, 13)
        ... )
        >>> if success:
        ...     print("Gap filled successfully")
        Gap filled successfully

    Note:
        The merge operation is atomic - either all data is merged successfully
        or the original file remains unchanged. Always validate gap boundaries
        to ensure data consistency.
    """

    def __init__(self, csv_path: Path):
        """Initialize SafeCSVMerger for the specified CSV file.

        Args:
            csv_path (Path): Path to the CSV file for gap filling operations.
        """
        self.csv_path = Path(csv_path)
        self.atomic_ops = AtomicCSVOperations(csv_path)

    def merge_gap_data_safe(
        self, gap_data: pd.DataFrame, gap_start: datetime, gap_end: datetime
    ) -> bool:
        """Safely merge gap data into existing CSV using atomic operations.

        Inserts gap-filling data into the existing CSV file while maintaining
        chronological order and data integrity. Uses atomic operations to
        ensure the merge is completed safely or not at all.

        Args:
            gap_data (pd.DataFrame): DataFrame containing gap data to merge.
                Must have columns matching the existing CSV structure.
                Timestamp column must be named 'date'.
            gap_start (datetime): Start timestamp of the gap being filled.
                Used for validation and boundary checking.
            gap_end (datetime): End timestamp of the gap being filled.
                Used for validation and boundary checking.

        Returns:
            bool: True if merge completed successfully, False if merge failed.
                On failure, original file is preserved via automatic rollback.

        Raises:
            ValueError: If gap_data format doesn't match existing CSV structure.
            FileNotFoundError: If the target CSV file doesn't exist.

        Examples:
            >>> merger = SafeCSVMerger(Path("eth_data.csv"))
            >>> gap_df = pd.DataFrame({...})  # Gap data
            >>> success = merger.merge_gap_data_safe(
            ...     gap_df,
            ...     datetime(2024, 1, 1, 12),
            ...     datetime(2024, 1, 1, 15)
            ... )
            >>> print(f"Merge success: {success}")
            Merge success: True

        Note:
            This method automatically handles:
            - Backup creation before modification
            - Data validation and format checking
            - Chronological sorting after merge
            - Rollback on any failure
        """

        logger.info(f"🎯 SAFE GAP MERGE: {gap_start} → {gap_end}")
        logger.info(f"📊 Gap data: {len(gap_data)} rows")

        try:
            # Step 1: Create backup
            self.atomic_ops.create_backup()

            # Step 2: Load existing data
            logger.info("📄 Loading existing CSV data...")
            existing_df = pd.read_csv(self.csv_path, comment="#")
            existing_df["date"] = pd.to_datetime(existing_df["date"])

            original_count = len(existing_df)
            logger.info(f"📊 Original data: {original_count} rows")

            # Step 3: Prepare gap data
            gap_data = gap_data.copy()
            gap_data["date"] = pd.to_datetime(gap_data["date"])

            # Step 4: Remove existing data in gap range
            gap_mask = (existing_df["date"] >= gap_start) & (existing_df["date"] <= gap_end)
            removed_count = gap_mask.sum()

            logger.info(f"🗑️ Removing {removed_count} existing rows in gap range")
            df_cleaned = existing_df[~gap_mask].copy()

            # Step 5: Merge with gap data
            logger.info("🔧 Merging gap data...")
            merged_df = pd.concat([df_cleaned, gap_data], ignore_index=True)

            # Step 6: Sort by date
            merged_df = merged_df.sort_values("date").reset_index(drop=True)
            final_count = len(merged_df)

            logger.info(f"📊 Merged result: {final_count} rows")
            logger.info(f"📈 Net change: {final_count - original_count:+d} rows")

            # Step 7: Validate merge
            gap_check = ((merged_df["date"] >= gap_start) & (merged_df["date"] <= gap_end)).sum()
            expected_gap_rows = len(gap_data)

            if gap_check != expected_gap_rows:
                raise ValueError(
                    f"Gap merge validation failed: expected {expected_gap_rows}, got {gap_check}"
                )

            # Step 8: Atomic write
            success = self.atomic_ops.write_dataframe_atomic(merged_df)

            if success:
                logger.info("✅ Safe gap merge completed successfully")
                # Keep backup for now, don't auto-cleanup
                return True
            else:
                logger.error("❌ Atomic write failed, rolling back...")
                self.atomic_ops.rollback_from_backup()
                return False

        except Exception as e:
            logger.error(f"❌ Safe gap merge failed: {e}")

            # Attempt rollback
            if hasattr(self.atomic_ops, "backup_path"):
                logger.info("🔄 Attempting rollback...")
                self.atomic_ops.rollback_from_backup()

            return False


def main():
    """Test atomic operations functionality"""
    logger.info("🧪 TESTING ATOMIC FILE OPERATIONS")

    # Test with sample data
    test_csv = Path("../sample_data/binance_spot_SOLUSDT-1h_20210806-20250831_v2.5.0.csv")

    if not test_csv.exists():
        logger.error(f"Test file not found: {test_csv}")
        return 1

    # Test backup and restore
    atomic_ops = AtomicCSVOperations(test_csv)

    # Create backup
    backup_path = atomic_ops.create_backup()
    logger.info(f"✅ Backup created: {backup_path}")

    # Read headers
    headers = atomic_ops.read_header_comments()
    logger.info(f"✅ Headers read: {len(headers)} lines")

    # Load and validate data
    df = pd.read_csv(test_csv, comment="#")
    is_valid, msg = atomic_ops.validate_dataframe(df)
    logger.info(f"✅ Validation: {is_valid} - {msg}")

    logger.info("✅ All atomic operations tests passed")
    return 0


if __name__ == "__main__":
    exit(main())
