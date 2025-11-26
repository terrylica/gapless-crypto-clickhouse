"""Schema validation tests for ClickHouse v6.0.0.

Validates SchemaValidator detects schema drift and raises exceptions.

ADR: ADR-0024 (Comprehensive Validation Canonicity)
ADR: ADR-0043 (ClickHouse Cloud-Only Policy)

NOTE: Destructive schema tests (DROP/ALTER operations) have been REMOVED
to prevent accidental damage to production ClickHouse Cloud. Only read-only
validation tests remain.
"""

import pytest

from gapless_crypto_clickhouse.clickhouse import ClickHouseConnection
from gapless_crypto_clickhouse.clickhouse.schema_validator import (
    SchemaValidator,
)


@pytest.mark.integration
@pytest.mark.slow
def test_schema_validation_passes_on_correct_schema():
    """Verify schema validator accepts correct schema.sql."""
    with ClickHouseConnection() as conn:
        validator = SchemaValidator(conn)
        report = validator.validate_schema()
        assert report["status"] == "valid"
        assert len(report["errors"]) == 0
