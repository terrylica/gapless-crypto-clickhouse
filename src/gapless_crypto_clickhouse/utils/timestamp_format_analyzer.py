"""Timestamp format detection and analysis for Binance data.

This module provides timestamp format detection supporting both millisecond
and microsecond precision timestamps, with comprehensive validation and
transition tracking capabilities.

Classes:
    TimestampFormatAnalyzer: Analyzes and validates timestamp formats

SLO Targets:
    Correctness: 100% - accurate format detection for all valid timestamps
    Observability: Complete reporting of format transitions and statistics
    Maintainability: Single source of truth for timestamp format logic
"""


class TimestampFormatAnalyzer:
    """Analyzes timestamp formats in cryptocurrency data with transition tracking.

    Supports both legacy millisecond precision (13-digit) and modern microsecond
    precision (16-digit) timestamps from Binance data. Tracks format transitions
    and provides comprehensive statistics.

    Attributes:
        format_stats: Statistics for each detected format type
        format_transitions: List of detected format transition points
        current_format: Current timestamp format being processed

    Examples:
        >>> analyzer = TimestampFormatAnalyzer()
        >>> analyzer.initialize_tracking()
        >>> fmt, secs, valid = analyzer.analyze_timestamp_format(1609459200000, 0)
        >>> fmt
        'milliseconds'
        >>> analyzer.update_format_stats(fmt, 1609459200000, 0)
        >>> analyzer.report_format_analysis()
        📈 COMPREHENSIVE FORMAT ANALYSIS:
          MILLISECONDS: 1 rows (100.0%)
        ...
    """

    def __init__(self):
        """Initialize timestamp format analyzer."""
        self.format_stats = {}
        self.format_transitions = []
        self.current_format = None
        self._format_analysis_summary = {}

    def initialize_tracking(self):
        """Initialize format tracking state for new data processing."""
        self.format_stats = {
            "milliseconds": {
                "count": 0,
                "first_seen": None,
                "last_seen": None,
                "sample_values": [],
            },
            "microseconds": {
                "count": 0,
                "first_seen": None,
                "last_seen": None,
                "sample_values": [],
            },
            "unknown": {"count": 0, "errors": []},
        }
        self.format_transitions = []
        self.current_format = None
        self._format_analysis_summary = {}

    def analyze_timestamp_format(self, raw_timestamp_value, csv_row_index):
        """Comprehensive timestamp format analysis with validation.

        Detects whether a timestamp is in milliseconds (13-digit) or microseconds
        (16+ digit) format and validates the timestamp is within expected range
        (2010-2030).

        Args:
            raw_timestamp_value: Integer timestamp value to analyze
            csv_row_index: Row index for error reporting

        Returns:
            tuple: (detected_format_type, converted_seconds, validation_result)
                - detected_format_type: "milliseconds", "microseconds", or "unknown"
                - converted_seconds: Timestamp converted to seconds (float or None)
                - validation_result: Dict with "valid" bool and optional "error_details"

        Examples:
            >>> analyzer = TimestampFormatAnalyzer()
            >>> fmt, secs, valid = analyzer.analyze_timestamp_format(1609459200000, 0)
            >>> fmt
            'milliseconds'
            >>> secs
            1609459200.0
            >>> valid
            {'valid': True}

            >>> fmt, secs, valid = analyzer.analyze_timestamp_format(1609459200000000, 1)
            >>> fmt
            'microseconds'
            >>> secs
            1609459200.0
        """
        timestamp_digit_count = len(str(raw_timestamp_value))

        # Enhanced format detection logic
        if timestamp_digit_count >= 16:  # Microseconds (16+ digits) - 2025+ format
            detected_format_type = "microseconds"
            converted_seconds = raw_timestamp_value / 1000000
            timestamp_min_bound = 1262304000000000  # 2010-01-01 00:00:00 (microseconds)
            timestamp_max_bound = 1893456000000000  # 2030-01-01 00:00:00 (microseconds)

        elif timestamp_digit_count >= 10:  # Milliseconds (10-15 digits) - Legacy format
            detected_format_type = "milliseconds"
            converted_seconds = raw_timestamp_value / 1000
            timestamp_min_bound = 1262304000000  # 2010-01-01 00:00:00 (milliseconds)
            timestamp_max_bound = 1893456000000  # 2030-01-01 00:00:00 (milliseconds)

        else:  # Unknown format (less than 10 digits)
            detected_format_type = "unknown"
            converted_seconds = None
            timestamp_min_bound = timestamp_max_bound = None

        # Enhanced validation with detailed error reporting
        if detected_format_type == "unknown":
            timestamp_validation_result = {
                "valid": False,
                "error_details": {
                    "row_index": csv_row_index,
                    "error_type": "unknown_timestamp_format",
                    "timestamp_value": raw_timestamp_value,
                    "digit_count": timestamp_digit_count,
                    "expected_formats": "milliseconds (10-15 digits) or microseconds (16+ digits)",
                    "raw_row": f"Timestamp too short: {timestamp_digit_count} digits",
                },
            }
        elif raw_timestamp_value < timestamp_min_bound or raw_timestamp_value > timestamp_max_bound:
            timestamp_validation_result = {
                "valid": False,
                "error_details": {
                    "row_index": csv_row_index,
                    "error_type": "invalid_timestamp_range",
                    "timestamp_value": raw_timestamp_value,
                    "timestamp_format": detected_format_type,
                    "digit_count": timestamp_digit_count,
                    "valid_range": f"{timestamp_min_bound} to {timestamp_max_bound}",
                    "parsed_date": "out_of_range",
                    "raw_row": f"Out of valid {detected_format_type} range (2010-2030)",
                },
            }
        else:
            timestamp_validation_result = {"valid": True}

        return detected_format_type, converted_seconds, timestamp_validation_result

    def update_format_stats(self, detected_timestamp_format, raw_timestamp_value, csv_row_index):
        """Update format statistics and detect transitions.

        Args:
            detected_timestamp_format: Format type ("milliseconds", "microseconds", "unknown")
            raw_timestamp_value: Original timestamp value
            csv_row_index: Row index for tracking

        Returns:
            bool: True if format transition detected, False otherwise
        """
        transition_detected = False

        # Track format transitions
        if self.current_format is None:
            self.current_format = detected_timestamp_format
        elif (
            self.current_format != detected_timestamp_format
            and detected_timestamp_format != "unknown"
        ):
            self.format_transitions.append(
                {
                    "row_index": csv_row_index,
                    "from_format": self.current_format,
                    "to_format": detected_timestamp_format,
                    "timestamp_value": raw_timestamp_value,
                }
            )
            self.current_format = detected_timestamp_format
            transition_detected = True

        # Update format statistics
        self.format_stats[detected_timestamp_format]["count"] += 1
        if self.format_stats[detected_timestamp_format]["first_seen"] is None:
            self.format_stats[detected_timestamp_format]["first_seen"] = csv_row_index
        self.format_stats[detected_timestamp_format]["last_seen"] = csv_row_index

        # Store sample values (first 3 per format)
        if len(self.format_stats[detected_timestamp_format]["sample_values"]) < 3:
            self.format_stats[detected_timestamp_format]["sample_values"].append(
                raw_timestamp_value
            )

        return transition_detected

    def report_format_analysis(self):
        """Report comprehensive format analysis with transition detection.

        Prints format statistics and transitions to console, and stores
        analysis summary in self._format_analysis_summary for metadata.
        """
        total_rows = sum(stats["count"] for stats in self.format_stats.values())

        print("    📈 COMPREHENSIVE FORMAT ANALYSIS:")

        for format_type, stats in self.format_stats.items():
            if stats["count"] > 0:
                percentage = (stats["count"] / total_rows) * 100 if total_rows > 0 else 0
                print(f"      {format_type.upper()}: {stats['count']:,} rows ({percentage:.1f}%)")

                if format_type != "unknown" and stats["sample_values"]:
                    first_sample = stats["sample_values"][0]
                    print(
                        f"        Sample: {first_sample} (rows {stats['first_seen']}-{stats['last_seen']})"
                    )

        # Report format transitions
        if len(self.format_transitions) > 0:
            print(f"    🔄 FORMAT TRANSITIONS DETECTED: {len(self.format_transitions)}")
            for i, transition in enumerate(self.format_transitions[:3]):  # Show first 3
                print(
                    f"      #{i + 1}: Row {transition['row_index']} - {transition['from_format']} → {transition['to_format']}"
                )
                print(f"          Timestamp: {transition['timestamp_value']}")
            if len(self.format_transitions) > 3:
                print(f"      ... and {len(self.format_transitions) - 3} more transitions")
        else:
            print(
                f"    ✅ SINGLE FORMAT: No transitions detected - consistent {self.current_format}"
            )

        # Store format analysis results for metadata
        self._format_analysis_summary = {
            "total_rows_analyzed": total_rows,
            "formats_detected": {
                fmt: stats["count"]
                for fmt, stats in self.format_stats.items()
                if stats["count"] > 0
            },
            "transitions_detected": len(self.format_transitions),
            "transition_details": self.format_transitions,
            "primary_format": self.current_format,
            "format_consistency": len(self.format_transitions) == 0,
        }

    def get_format_analysis_summary(self):
        """Get format analysis summary for metadata.

        Returns:
            dict: Format analysis summary with statistics and transitions
        """
        return self._format_analysis_summary
