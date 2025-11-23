-- ClickHouse Schema for gapless-crypto-clickhouse
-- ADR-0005: ClickHouse Migration for Future-Proofing
-- ADR-0034: Schema Optimization for Prop Trading Production Readiness
--
-- ReplacingMergeTree engine with deterministic versioning for zero-gap guarantee.
-- Preserves ADR-0004 futures support (instrument_type column for spot/futures).
-- Symbol-first ORDER BY for 10-100x faster trading queries (ADR-0034).
--
-- Error Handling: Raise and propagate (no silent failures)
-- SLOs: Availability, Correctness (zero-gap via _version), Observability, Maintainability

CREATE TABLE IF NOT EXISTS ohlcv (
    -- Primary timestamp (microsecond precision - ADR-0021)
    -- Upgraded from DateTime64(3) to support Binance's 2025-01-01 format transition:
    --   Spot data: microseconds (16 digits) after 2025-01-01
    --   Futures data: milliseconds (13 digits), converted to microseconds during ingestion
    timestamp DateTime64(6) CODEC(DoubleDelta, LZ4),

    -- Metadata columns (low-cardinality, optimized for indexing)
    symbol LowCardinality(String) CODEC(ZSTD(3)),           -- Trading pair (e.g., "BTCUSDT")
    timeframe LowCardinality(String) CODEC(ZSTD(3)),       -- Timeframe (e.g., "1h", "1mo")
    instrument_type LowCardinality(String) CODEC(ZSTD(3)), -- 'spot' or 'futures-um' (ADR-0004, ADR-0021)
    data_source LowCardinality(String) CODEC(ZSTD(3)),     -- 'cloudfront'

    -- OHLCV data (core price/volume metrics)
    open Float64 CODEC(Gorilla, LZ4),
    high Float64 CODEC(Gorilla, LZ4),
    low Float64 CODEC(Gorilla, LZ4),
    close Float64 CODEC(Gorilla, LZ4),
    volume Float64 CODEC(Gorilla, LZ4),

    -- Additional microstructure metrics (Binance 11-column format)
    close_time DateTime64(6) CODEC(DoubleDelta, LZ4),  -- Upgraded to microsecond precision
    quote_asset_volume Float64 CODEC(Gorilla, LZ4),
    number_of_trades Int64 CODEC(Delta, LZ4),
    taker_buy_base_asset_volume Float64 CODEC(Gorilla, LZ4),
    taker_buy_quote_asset_volume Float64 CODEC(Gorilla, LZ4),

    -- Futures-specific data (ADR-0021, v3.2.0+)
    funding_rate Nullable(Float64) CODEC(Gorilla, LZ4),  -- NULL for spot, initially NULL for futures

    -- Deduplication support (application-level, preserves zero-gap guarantee)
    _version UInt64 CODEC(Delta, LZ4),  -- Deterministic hash of row content
    _sign Int8 DEFAULT 1                -- ReplacingMergeTree sign (1 for active rows)

) ENGINE = ReplacingMergeTree(_version)
-- ADR-0034: Symbol-first ORDER BY for prop trading query patterns (10-100x faster)
-- Optimizes for: "get all data for BTCUSDT" (80% of queries)
-- vs timestamp-first which optimizes for: "what happened at 12:00 across all symbols" (5% of queries)
ORDER BY (symbol, timeframe, toStartOfHour(timestamp), timestamp)
PARTITION BY toYYYYMMDD(timestamp)
SETTINGS
    index_granularity = 8192,           -- Default granularity (good for time-series)
    allow_nullable_key = 0,             -- Disallow NULL in ORDER BY keys (data quality)
    merge_with_ttl_timeout = 86400;     -- Merge within 24 hours (background deduplication)

-- ADR-0034: Partition-aware FINAL optimization (reduces overhead from 10-30% to 2-5%)
-- NOTE: do_not_merge_across_partitions_select_final is a query/session setting, not table setting
-- Configure in client connection:
--   settings = {"do_not_merge_across_partitions_select_final": 1}

-- Rationale:
-- 1. ReplacingMergeTree(_version): Handles duplicates via background merges
--    - _version is deterministic hash of (timestamp, OHLCV, symbol, timeframe, instrument_type)
--    - Identical writes → identical _version → consistent merge outcome
--    - Preserves zero-gap guarantee via deterministic deduplication
--
-- 2. ORDER BY composite key: (symbol, timeframe, toStartOfHour(timestamp), timestamp) [ADR-0034]
--    - Symbol-first: Optimizes for "get all BTCUSDT data" (80% of trading queries)
--    - Timeframe-second: Usually query one timeframe at a time (e.g., "1h")
--    - Hour-bucketed timestamp: Groups by hour for efficient range scans
--    - Full timestamp: Deterministic ordering within each hour
--    - ClickHouse uses ORDER BY as primary key (unlike PostgreSQL)
--    - Performance: 10-100x faster vs timestamp-first ORDER BY
--
-- 3. PARTITION BY toYYYYMMDD(timestamp): Daily partitions
--    - Matches ADR-0003 QuestDB partition strategy (PARTITION BY DAY)
--    - Enables efficient partition pruning for date-range queries
--
-- 4. LowCardinality(String): ClickHouse equivalent to QuestDB SYMBOL
--    - Optimizes storage for low-cardinality columns (symbol, timeframe, etc.)
--    - Automatic dictionary encoding (similar to SYMBOL capacity)
--
-- 5. CODEC compression:
--    - DoubleDelta: Optimized for timestamps (sequential values)
--    - Gorilla: Optimized for float values (OHLCV data)
--    - Delta: Optimized for integer sequences (number_of_trades)
--    - ZSTD: General-purpose compression for string columns
--
-- 6. DateTime64(6): Microsecond precision (ADR-0021)
--    - Upgraded from DateTime64(3) to support Binance's 2025-01-01 format transition
--    - Spot data: microseconds (16 digits) after 2025-01-01
--    - Futures data: milliseconds (13 digits), converted to microseconds during ingestion
--    - Universal microsecond precision prevents timestamp errors
--    - ClickHouse equivalent to QuestDB TIMESTAMP type

-- Zero-Gap Guarantee:
-- Unlike QuestDB DEDUP ENABLE UPSERT KEYS (immediate consistency),
-- ClickHouse uses eventual consistency (duplicates visible until merge).
-- Application-level deterministic versioning ensures consistent merge outcomes.
--
-- Query pattern for deduplicated results:
--   SELECT * FROM ohlcv FINAL WHERE symbol = 'BTCUSDT' AND timeframe = '1h';
--
-- FINAL keyword forces deduplication at query time.
-- With ADR-0034 optimization (do_not_merge_across_partitions_select_final=1),
-- overhead reduced from 10-30% to 2-5% (acceptable for <100ms latency targets).

-- Migration from QuestDB (ADR-0003):
-- QuestDB SYMBOL → ClickHouse LowCardinality(String)
-- QuestDB DEDUP ENABLE UPSERT KEYS → ClickHouse ReplacingMergeTree(_version)
-- QuestDB PARTITION BY DAY → ClickHouse PARTITION BY toYYYYMMDD(timestamp)
-- QuestDB PostgreSQL wire protocol → ClickHouse native protocol (clickhouse-driver)
