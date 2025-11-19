"""CSV validation module for cryptocurrency market data quality assurance.

This module provides comprehensive validation for CSV files containing OHLCV data,
ensuring data integrity, completeness, and quality before use in trading systems.

Validation Layers:
    1. Structure Validation: Column presence and format detection
    2. DateTime Validation: Chronological order and gap detection
    3. OHLCV Quality: Logical consistency and value ranges
    4. Coverage Validation: Expected vs actual bar counts
    5. Statistical Anomaly Detection: Outlier and pattern analysis

SLO Targets:
    Correctness: 100% - all validation rules must be accurate
    Observability: Complete reporting with errors, warnings, and metrics
    Maintainability: Single source of truth for CSV validation
"""

import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional, Union

import pandas as pd

from .models import ValidationReport
from .storage import ValidationStorage, extract_symbol_timeframe_from_path


class CSVValidator:
    """Validator for cryptocurrency market data CSV files.

    Provides multi-layer validation including structure checking, datetime
    sequence validation, OHLCV quality analysis, coverage calculation, and
    statistical anomaly detection.

    Examples:
        >>> validator = CSVValidator()
        >>> results = validator.validate_csv_file("BTCUSDT-1h.csv", expected_timeframe="1h")
        >>> if results["total_errors"] == 0:
        ...     print("Validation passed!")
        ... else:
        ...     print(f"Validation failed: {results['validation_summary']}")

    Note:
        All validation errors and warnings are logged to console and returned
        in the validation results dictionary.
    """

    def _run_structure_validation_layer(self, df: pd.DataFrame, validation_results: dict) -> None:
        """Run structure validation layer and update results.

        Args:
            df: DataFrame to validate
            validation_results: Validation results dict to update
        """
        print("\n1. BASIC STRUCTURE VALIDATION")
        structure_validation = self._validate_csv_structure(df)
        validation_results["structure_validation"] = structure_validation
        print(f"  Columns: {structure_validation['status']}")

        if structure_validation["errors"]:
            for error in structure_validation["errors"]:
                print(f"    ❌ {error}")
                validation_results["total_errors"] += 1

    def _run_datetime_validation_layer(
        self, df: pd.DataFrame, expected_timeframe: Optional[str], validation_results: dict
    ) -> None:
        """Run datetime validation layer and update results.

        Args:
            df: DataFrame to validate
            expected_timeframe: Expected timeframe for gap detection
            validation_results: Validation results dict to update
        """
        print("\n2. DATE/TIME VALIDATION")
        datetime_validation = self._validate_datetime_sequence(df, expected_timeframe)
        validation_results["datetime_validation"] = datetime_validation
        print(
            f"  Date Range: {datetime_validation['date_range']['start']} to {datetime_validation['date_range']['end']}"
        )
        print(f"  Duration: {datetime_validation['duration_days']:.1f} days")
        print(f"  Gaps Found: {datetime_validation['gaps_found']}")
        print(f"  Sequence: {datetime_validation['chronological_order']}")

        if datetime_validation["errors"]:
            for error in datetime_validation["errors"]:
                print(f"    ❌ {error}")
                validation_results["total_errors"] += 1
        if datetime_validation["warnings"]:
            for warning in datetime_validation["warnings"]:
                print(f"    ⚠️  {warning}")
                validation_results["total_warnings"] += 1

    def _run_ohlcv_validation_layer(self, df: pd.DataFrame, validation_results: dict) -> None:
        """Run OHLCV quality validation layer and update results.

        Args:
            df: DataFrame to validate
            validation_results: Validation results dict to update
        """
        print("\n3. OHLCV DATA QUALITY VALIDATION")
        ohlcv_validation = self._validate_ohlcv_quality(df)
        validation_results["ohlcv_validation"] = ohlcv_validation
        print(
            f"  Price Range: ${ohlcv_validation['price_range']['min']:.4f} - ${ohlcv_validation['price_range']['max']:.4f}"
        )
        print(
            f"  Volume Range: {ohlcv_validation['volume_stats']['min']:.2f} - {ohlcv_validation['volume_stats']['max']:,.0f}"
        )
        print(f"  OHLC Logic Errors: {ohlcv_validation['ohlc_errors']}")
        print(f"  Negative/Zero Values: {ohlcv_validation['negative_zero_values']}")

        if ohlcv_validation["errors"]:
            for error in ohlcv_validation["errors"]:
                print(f"    ❌ {error}")
                validation_results["total_errors"] += 1
        if ohlcv_validation["warnings"]:
            for warning in ohlcv_validation["warnings"]:
                print(f"    ⚠️  {warning}")
                validation_results["total_warnings"] += 1

    def _run_coverage_and_anomaly_layers(
        self, df: pd.DataFrame, expected_timeframe: Optional[str], validation_results: dict
    ) -> None:
        """Run coverage and anomaly validation layers.

        Args:
            df: DataFrame to validate
            expected_timeframe: Expected timeframe for coverage calculation
            validation_results: Validation results dict to update
        """
        print("\n4. EXPECTED COVERAGE VALIDATION")
        coverage_validation = self._validate_expected_coverage(df, expected_timeframe)
        validation_results["coverage_validation"] = coverage_validation
        print(f"  Expected Bars: {coverage_validation['expected_bars']:,}")
        print(f"  Actual Bars: {coverage_validation['actual_bars']:,}")
        print(f"  Coverage: {coverage_validation['coverage_percentage']:.1f}%")

        print("\n5. STATISTICAL ANOMALY DETECTION")
        anomaly_validation = self._validate_statistical_anomalies(df)
        validation_results["anomaly_validation"] = anomaly_validation
        print(f"  Price Outliers: {anomaly_validation['price_outliers']}")
        print(f"  Volume Outliers: {anomaly_validation['volume_outliers']}")
        print(f"  Suspicious Patterns: {anomaly_validation['suspicious_patterns']}")

    def _generate_final_validation_summary(self, validation_results: dict) -> None:
        """Generate and print final validation summary.

        Args:
            validation_results: Validation results dict to update with summary
        """
        if validation_results["total_errors"] == 0:
            if validation_results["total_warnings"] == 0:
                validation_results["validation_summary"] = "PERFECT - No errors or warnings"
                print("\n✅ VALIDATION RESULT: PERFECT")
                print("   No errors or warnings found. Data quality is excellent.")
            else:
                validation_results["validation_summary"] = (
                    f"GOOD - {validation_results['total_warnings']} warnings"
                )
                print("\n✅ VALIDATION RESULT: GOOD")
                print(f"   No errors, but {validation_results['total_warnings']} warnings found.")
        else:
            validation_results["validation_summary"] = (
                f"FAILED - {validation_results['total_errors']} errors, {validation_results['total_warnings']} warnings"
            )
            print("\n❌ VALIDATION RESULT: FAILED")
            print(
                f"   {validation_results['total_errors']} errors and {validation_results['total_warnings']} warnings found."
            )

    def validate_csv_file(
        self,
        csv_filepath: Union[str, Path],
        expected_timeframe: Optional[str] = None,
        store_report: bool = False,
    ) -> Dict[str, Any]:
        """
        Comprehensive validation of CSV file data integrity, completeness, and quality.

        Args:
            csv_filepath: Path to CSV file to validate
            expected_timeframe: Expected timeframe (e.g., '30m') for interval validation
            store_report: If True, persist validation report to DuckDB for analysis (default: False)

        Returns:
            dict: Validation results with detailed analysis

        Examples:
            >>> validator = CSVValidator()
            >>> results = validator.validate_csv_file("data.csv", "1h")
            >>> print(f"Errors: {results['total_errors']}, Warnings: {results['total_warnings']}")

            >>> # Store validation report for AI agent analysis
            >>> results = validator.validate_csv_file("data.csv", "1h", store_report=True)
        """
        # Start timing for performance metrics
        start_time = time.perf_counter()

        csv_filepath = Path(csv_filepath)

        print(f"\n{'=' * 60}")
        print(f"VALIDATING: {csv_filepath.name}")
        print(f"{'=' * 60}")

        validation_results = {
            "validation_timestamp": datetime.now(timezone.utc).isoformat() + "Z",
            "file_path": str(csv_filepath),
            "file_exists": csv_filepath.exists(),
            "file_size_mb": 0,
            "total_errors": 0,
            "total_warnings": 0,
            "validation_summary": "UNKNOWN",
        }

        if not csv_filepath.exists():
            validation_results["validation_summary"] = "FAILED - File not found"
            validation_results["total_errors"] = 1
            return validation_results

        validation_results["file_size_mb"] = csv_filepath.stat().st_size / (1024 * 1024)

        try:
            # Load CSV data efficiently
            print("Loading and parsing CSV data...")
            df = pd.read_csv(csv_filepath, comment="#")
            validation_results["total_bars"] = len(df)
            print(f"  ✅ Loaded {len(df):,} data bars")

            # Run all validation layers
            self._run_structure_validation_layer(df, validation_results)
            self._run_datetime_validation_layer(df, expected_timeframe, validation_results)
            self._run_ohlcv_validation_layer(df, validation_results)
            self._run_coverage_and_anomaly_layers(df, expected_timeframe, validation_results)

            # Generate final summary
            self._generate_final_validation_summary(validation_results)

        except Exception as e:
            validation_results["validation_summary"] = f"ERROR - {str(e)}"
            validation_results["total_errors"] += 1
            print(f"❌ Validation failed with exception: {e}")

        # Calculate validation duration
        end_time = time.perf_counter()
        duration_ms = (end_time - start_time) * 1000

        # Store report to DuckDB if requested
        if store_report:
            try:
                # Extract symbol and timeframe from filepath
                symbol, timeframe = extract_symbol_timeframe_from_path(str(csv_filepath))

                # Convert legacy dict to typed ValidationReport
                report = ValidationReport.from_legacy_dict(
                    validation_results, duration_ms=duration_ms, symbol=symbol, timeframe=timeframe
                )

                # Persist to DuckDB
                storage = ValidationStorage()
                storage.insert_report(report)
                print(f"\n📊 Validation report stored to database ({duration_ms:.2f}ms)")

            except Exception as e:
                print(f"⚠️  Failed to store validation report: {e}")

        return validation_results

    def _detect_csv_format_type(
        self, df: pd.DataFrame, expected_columns: list, legacy_columns: list
    ) -> tuple[str, bool, bool]:
        """Detect CSV format type (enhanced, legacy, or incomplete).

        Args:
            df: DataFrame to analyze
            expected_columns: List of enhanced format columns
            legacy_columns: List of legacy format columns

        Returns:
            tuple: (format_type, has_enhanced_format, has_legacy_format)
        """
        has_enhanced_format = all(col in df.columns for col in expected_columns)
        has_legacy_format = all(col in df.columns for col in legacy_columns)

        if has_enhanced_format:
            format_type = "enhanced"
        elif has_legacy_format:
            format_type = "legacy"
        else:
            format_type = "incomplete"

        return format_type, has_enhanced_format, has_legacy_format

    def _validate_column_completeness(
        self,
        df: pd.DataFrame,
        format_type: str,
        expected_columns: list,
        legacy_columns: list,
        errors: list,
        warnings: list,
    ) -> None:
        """Validate column completeness based on format type.

        Args:
            df: DataFrame to validate
            format_type: Detected format type
            expected_columns: List of enhanced format columns
            legacy_columns: List of legacy format columns
            errors: List to append errors to
            warnings: List to append warnings to
        """
        if format_type == "enhanced":
            missing_columns = [col for col in expected_columns if col not in df.columns]
            if missing_columns:
                errors.append(f"Missing enhanced columns: {missing_columns}")
        elif format_type == "legacy":
            warnings.append(
                "Legacy format detected - missing microstructure columns for advanced analysis"
            )
            missing_enhanced = [col for col in expected_columns if col not in df.columns]
            warnings.append(f"Enhanced features unavailable: {missing_enhanced}")
        else:  # incomplete format
            missing_basic = [col for col in legacy_columns if col not in df.columns]
            errors.append(f"Missing basic required columns: {missing_basic}")

    def _check_extra_columns(
        self, df: pd.DataFrame, expected_columns: list, warnings: list
    ) -> None:
        """Check for unexpected extra columns.

        Args:
            df: DataFrame to check
            expected_columns: List of expected columns
            warnings: List to append warnings to
        """
        extra_columns = [col for col in df.columns if col not in expected_columns]
        if extra_columns:
            warnings.append(f"Unexpected extra columns: {extra_columns}")

    def _validate_csv_structure(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Validate CSV has correct structure and columns.

        Args:
            df: DataFrame to validate

        Returns:
            dict: Structure validation results with status, format type, errors, and warnings

        Note:
            Supports both enhanced (11-column) and legacy (6-column) formats for
            backward compatibility.
        """
        # Enhanced expected columns for complete microstructure data
        expected_columns = [
            "date",
            "open",
            "high",
            "low",
            "close",
            "volume",
            "close_time",
            "quote_asset_volume",
            "number_of_trades",
            "taker_buy_base_asset_volume",
            "taker_buy_quote_asset_volume",
        ]

        # Legacy format for backward compatibility
        legacy_columns = ["date", "open", "high", "low", "close", "volume"]

        errors = []
        warnings = []

        # Detect format type
        format_type, has_enhanced_format, has_legacy_format = self._detect_csv_format_type(
            df, expected_columns, legacy_columns
        )

        # Validate column completeness based on format
        self._validate_column_completeness(
            df, format_type, expected_columns, legacy_columns, errors, warnings
        )

        # Check for extra columns
        self._check_extra_columns(df, expected_columns, warnings)

        # Check for empty data
        if len(df) == 0:
            errors.append("CSV file is empty (no data rows)")

        return {
            "status": "VALID" if not errors else "INVALID",
            "format_type": format_type,
            "errors": errors,
            "warnings": warnings,
            "columns_found": list(df.columns),
            "expected_columns": expected_columns,
            "legacy_columns": legacy_columns,
        }

    def _validate_datetime_sequence(
        self, df: pd.DataFrame, expected_timeframe: Optional[str]
    ) -> Dict[str, Any]:
        """Validate datetime sequence is complete and chronological.

        Args:
            df: DataFrame with 'date' column to validate
            expected_timeframe: Expected timeframe for gap detection (e.g., '1h', '30m')

        Returns:
            dict: DateTime validation results with status, date range, gaps, and errors

        Note:
            Detects all gaps > expected interval and reports chronological ordering issues.
        """
        errors = []
        warnings = []
        gaps_found = 0

        # Convert date column to datetime
        try:
            df["datetime"] = pd.to_datetime(df["date"])
        except Exception as e:
            errors.append(f"Failed to parse dates: {e}")
            return {"status": "INVALID", "errors": errors, "warnings": warnings}

        # Check chronological order
        is_sorted = df["datetime"].is_monotonic_increasing

        # Find gaps if we have expected timeframe
        gap_details = []
        if expected_timeframe and len(df) > 1:
            # Calculate expected interval in minutes
            interval_map = {"1m": 1, "3m": 3, "5m": 5, "15m": 15, "30m": 30, "1h": 60, "2h": 120}
            expected_interval = interval_map.get(expected_timeframe, 0)

            if expected_interval > 0:
                expected_delta = pd.Timedelta(minutes=expected_interval)

                # Check for gaps
                for i in range(1, len(df)):
                    actual_delta = df["datetime"].iloc[i] - df["datetime"].iloc[i - 1]
                    if actual_delta > expected_delta:
                        gaps_found += 1
                        gap_details.append(
                            {
                                "position": i,
                                "expected_time": (
                                    df["datetime"].iloc[i - 1] + expected_delta
                                ).isoformat(),
                                "actual_time": df["datetime"].iloc[i].isoformat(),
                                "gap_duration": str(actual_delta - expected_delta),
                            }
                        )

                        # Record every single gap for complete validation tracking
                        warnings.append(
                            f"Gap at position {i}: expected {expected_delta}, got {actual_delta}"
                        )

        if not is_sorted:
            errors.append("Timestamps are not in chronological order")

        if gaps_found > 10:
            errors.append(f"Too many gaps found: {gaps_found} (data may be incomplete)")
        elif gaps_found > 0:
            warnings.append(f"{gaps_found} timestamp gaps found (market closures or data issues)")

        return {
            "status": "VALID" if not errors else "INVALID",
            "errors": errors,
            "warnings": warnings,
            "date_range": {
                "start": df["datetime"].min().isoformat(),
                "end": df["datetime"].max().isoformat(),
            },
            "duration_days": (df["datetime"].max() - df["datetime"].min()).days,
            "chronological_order": is_sorted,
            "gaps_found": gaps_found,
            "gap_details": gap_details,  # Complete gap details for thorough analysis
        }

    def _validate_ohlcv_quality(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Validate OHLCV data quality and logical consistency.

        Args:
            df: DataFrame with OHLCV columns to validate

        Returns:
            dict: OHLCV quality validation results with price ranges, volume stats, and errors

        Note:
            Checks OHLC logic (High >= Low, Open/Close within range), detects negative/zero
            values, and flags volume anomalies.
        """
        errors = []
        warnings = []

        # Check for negative or zero values
        negative_zero_count = 0
        for col in ["open", "high", "low", "close"]:
            negative_zero = (df[col] <= 0).sum()
            if negative_zero > 0:
                errors.append(f"Found {negative_zero} negative/zero values in {col}")
                negative_zero_count += negative_zero

        # Check volume (can be zero but not negative)
        negative_volume = (df["volume"] < 0).sum()
        if negative_volume > 0:
            errors.append(f"Found {negative_volume} negative volume values")

        zero_volume = (df["volume"] == 0).sum()
        if zero_volume > 0:
            warnings.append(f"Found {zero_volume} zero volume bars")

        # Check OHLC logic: High >= Low, Open/Close within High/Low range
        ohlc_errors = 0

        # High should be >= Low
        high_low_errors = (df["high"] < df["low"]).sum()
        if high_low_errors > 0:
            errors.append(f"Found {high_low_errors} bars where High < Low")
            ohlc_errors += high_low_errors

        # Open should be within High/Low range
        open_range_errors = ((df["open"] > df["high"]) | (df["open"] < df["low"])).sum()
        if open_range_errors > 0:
            errors.append(f"Found {open_range_errors} bars where Open is outside High/Low range")
            ohlc_errors += open_range_errors

        # Close should be within High/Low range
        close_range_errors = ((df["close"] > df["high"]) | (df["close"] < df["low"])).sum()
        if close_range_errors > 0:
            errors.append(f"Found {close_range_errors} bars where Close is outside High/Low range")
            ohlc_errors += close_range_errors

        return {
            "status": "VALID" if not errors else "INVALID",
            "errors": errors,
            "warnings": warnings,
            "price_range": {
                "min": min(df["low"].min(), df["high"].min(), df["open"].min(), df["close"].min()),
                "max": max(df["low"].max(), df["high"].max(), df["open"].max(), df["close"].max()),
            },
            "volume_stats": {
                "min": df["volume"].min(),
                "max": df["volume"].max(),
                "mean": df["volume"].mean(),
            },
            "ohlc_errors": ohlc_errors,
            "negative_zero_values": negative_zero_count,
        }

    def _validate_expected_coverage(
        self, df: pd.DataFrame, expected_timeframe: Optional[str]
    ) -> Dict[str, Any]:
        """Validate data coverage matches expected timeframe and duration.

        Args:
            df: DataFrame with 'date' column
            expected_timeframe: Expected timeframe for coverage calculation (e.g., '1h')

        Returns:
            dict: Coverage validation results with expected/actual bar counts and percentage

        Note:
            Warns if coverage < 95% (missing data) or > 105% (duplicate data).
        """
        warnings = []

        if not expected_timeframe or len(df) == 0:
            return {"status": "SKIPPED", "warnings": ["Cannot validate coverage without timeframe"]}

        # Calculate expected bars based on timeframe and actual date range
        df["datetime"] = pd.to_datetime(df["date"])
        start_time = df["datetime"].min()
        end_time = df["datetime"].max()
        duration = end_time - start_time

        # Calculate expected number of bars
        interval_map = {"1m": 1, "3m": 3, "5m": 5, "15m": 15, "30m": 30, "1h": 60, "2h": 120}
        interval_minutes = interval_map.get(expected_timeframe, 0)

        if interval_minutes > 0:
            expected_bars = int(duration.total_seconds() / (interval_minutes * 60)) + 1
            actual_bars = len(df)
            coverage_percentage = (actual_bars / expected_bars) * 100

            if coverage_percentage < 95:
                warnings.append(
                    f"Low coverage: {coverage_percentage:.1f}% (may indicate missing data)"
                )
            elif coverage_percentage > 105:
                warnings.append(
                    f"High coverage: {coverage_percentage:.1f}% (may indicate duplicate data)"
                )
        else:
            expected_bars = 0
            coverage_percentage = 0
            warnings.append(f"Unknown timeframe '{expected_timeframe}' for coverage calculation")

        return {
            "status": "VALID" if not warnings else "WARNING",
            "warnings": warnings,
            "expected_bars": expected_bars,
            "actual_bars": len(df),
            "coverage_percentage": coverage_percentage,
            "duration_days": duration.days,
        }

    def _validate_statistical_anomalies(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Detect statistical anomalies in price and volume data.

        Args:
            df: DataFrame with OHLCV columns

        Returns:
            dict: Anomaly validation results with outlier counts and suspicious pattern detection

        Note:
            Uses IQR (Interquartile Range) method for outlier detection. Flags if > 5% price
            outliers, > 2% volume outliers, or > 10% repeated values in any price column.
        """
        warnings = []

        # Calculate basic statistics
        price_cols = ["open", "high", "low", "close"]

        # Price outliers (using IQR method)
        price_outliers = 0
        for col in price_cols:
            Q1 = df[col].quantile(0.25)
            Q3 = df[col].quantile(0.75)
            IQR = Q3 - Q1
            lower_bound = Q1 - 1.5 * IQR
            upper_bound = Q3 + 1.5 * IQR
            outliers = ((df[col] < lower_bound) | (df[col] > upper_bound)).sum()
            price_outliers += outliers

        # Volume outliers
        vol_Q1 = df["volume"].quantile(0.25)
        vol_Q3 = df["volume"].quantile(0.75)
        vol_IQR = vol_Q3 - vol_Q1
        vol_upper_bound = vol_Q3 + 1.5 * vol_IQR
        volume_outliers = (df["volume"] > vol_upper_bound).sum()

        # Suspicious patterns
        suspicious_patterns = 0

        # Check for repeated identical prices (suspicious)
        for col in price_cols:
            repeated = df[col].value_counts()
            max_repeats = repeated.max()
            if max_repeats > len(df) * 0.1:  # More than 10% identical values
                warnings.append(f"Suspicious: {col} has {max_repeats} repeated values")
                suspicious_patterns += 1

        if price_outliers > len(df) * 0.05:  # More than 5% outliers
            warnings.append(
                f"High number of price outliers: {price_outliers} ({100 * price_outliers / len(df):.1f}%)"
            )

        if volume_outliers > len(df) * 0.02:  # More than 2% volume outliers
            warnings.append(
                f"High number of volume outliers: {volume_outliers} ({100 * volume_outliers / len(df):.1f}%)"
            )

        return {
            "status": "VALID" if not warnings else "WARNING",
            "warnings": warnings,
            "price_outliers": price_outliers,
            "volume_outliers": volume_outliers,
            "suspicious_patterns": suspicious_patterns,
        }
