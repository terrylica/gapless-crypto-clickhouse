---
adr: 2025-12-10-clickhouse-codec-t64-optimization
source: ~/.claude/plans/golden-foraging-tulip.md
implementation-status: released
phase: phase-3
release-version: v17.0.0
last-updated: 2025-12-10
---

# ClickHouse Codec T64 Optimization - Design Specification

**ADR**: [ClickHouse Codec T64 Optimization](/docs/adr/2025-12-10-clickhouse-codec-t64-optimization.md)

## Overview

Optimize the `number_of_trades` column codec from `CODEC(Delta, LZ4)` to `CODEC(T64, ZSTD)` per ClickHouse Architect skill recommendations. This requires table recreation in both local and cloud ClickHouse environments.

## Implementation Tasks

### Task 1: Update Schema File

**File**: `src/gapless_crypto_clickhouse/clickhouse/schema.sql`

**Change**:

```sql
-- Line 38: Change from
number_of_trades Int64 CODEC(Delta, LZ4),

-- To
number_of_trades Int64 CODEC(T64, ZSTD),
```

**Verification**: Review schema.sql to confirm change is correct.

### Task 2: Local ClickHouse Migration

**Prerequisites**: Local ClickHouse must be running (`mise run ch-start`)

**Steps**:

1. Drop existing table:

   ```bash
   clickhouse client --host localhost --port 9000 -q "DROP TABLE IF EXISTS default.ohlcv"
   ```

2. Redeploy schema:

   ```bash
   mise run local-init
   ```

3. Verify schema:

   ```bash
   clickhouse client --host localhost --port 9000 -q "DESCRIBE TABLE ohlcv FORMAT Vertical"
   ```

4. (Optional) Re-seed with sample data:

   ```bash
   mise run seed-local
   ```

### Task 3: Cloud ClickHouse Migration

**Prerequisites**: Doppler credentials configured for `aws-credentials/prd`

**Steps**:

1. Drop existing table:

   ```bash
   doppler run --project aws-credentials --config prd -- \
     clickhouse-client -q "DROP TABLE IF EXISTS default.ohlcv"
   ```

2. Redeploy schema:

   ```bash
   doppler run --project aws-credentials --config prd -- \
     clickhouse-client --multiquery < src/gapless_crypto_clickhouse/clickhouse/schema.sql
   ```

3. Verify schema:

   ```bash
   doppler run --project aws-credentials --config prd -- \
     clickhouse-client -q "DESCRIBE TABLE ohlcv FORMAT Vertical"
   ```

### Task 4: Validation

**Local Validation**:

```bash
mise run validate-local
```

**Cloud Validation**:

```bash
mise run validate-cloud
```

**Compression Check** (after data ingestion):

```sql
SELECT
    column,
    compression_codec,
    formatReadableSize(data_compressed_bytes) AS compressed,
    formatReadableSize(data_uncompressed_bytes) AS uncompressed,
    round(data_uncompressed_bytes / data_compressed_bytes, 2) AS ratio
FROM system.columns
WHERE table = 'ohlcv' AND column = 'number_of_trades'
```

## Success Criteria

- [x] Schema file updated with `CODEC(T64, ZSTD)` for `number_of_trades`
- [x] Local ClickHouse table recreated with new schema
- [x] Cloud ClickHouse table recreated with new schema
- [x] Direct validation confirms `CODEC(T64, ZSTD(1))` on both environments
- [x] ADR status updated to `accepted`
- [x] Doppler credentials updated (password + HTTP port 443)

## Risk Mitigation

| Risk              | Mitigation                                                |
| ----------------- | --------------------------------------------------------- |
| Data loss         | User confirmed acceptable; can re-ingest from Binance CDN |
| Schema mismatch   | Verify with DESCRIBE TABLE after each migration           |
| Connection issues | Test Doppler credentials before cloud migration           |

## Rollback Plan

If issues occur, revert schema.sql and re-run migration:

```sql
-- Revert to original codec
number_of_trades Int64 CODEC(Delta, LZ4),
```

Then repeat Task 2 and Task 3.
