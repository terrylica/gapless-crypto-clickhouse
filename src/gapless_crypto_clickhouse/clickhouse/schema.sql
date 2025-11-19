-- ClickHouse Schema for gapless-crypto-data v4.0.0
-- ADR-0005: ClickHouse Migration for Future-Proofing
--
-- ReplacingMergeTree engine with deterministic versioning for zero-gap guarantee.
-- Preserves ADR-0004 futures support (instrument_type column for spot/futures).
--
-- Error Handling: Raise and propagate (no silent failures)
-- SLOs: Availability, Correctness (zero-gap via _version), Observability, Maintainability

CREATE TABLE IF NOT EXISTS ohlcv (
    -- Primary timestamp (millisecond precision)
    timestamp DateTime64(3) CODEC(DoubleDelta, LZ4),

    -- Metadata columns (low-cardinality, optimized for indexing)
    symbol LowCardinality(String) CODEC(ZSTD(3)),           -- Trading pair (e.g., "BTCUSDT")
    timeframe LowCardinality(String) CODEC(ZSTD(3)),       -- Timeframe (e.g., "1h", "1mo")
    instrument_type LowCardinality(String) CODEC(ZSTD(3)), -- 'spot' or 'futures' (ADR-0004)
    data_source LowCardinality(String) CODEC(ZSTD(3)),     -- 'cloudfront'

    -- OHLCV data (core price/volume metrics)
    open Float64 CODEC(Gorilla, LZ4),
    high Float64 CODEC(Gorilla, LZ4),
    low Float64 CODEC(Gorilla, LZ4),
    close Float64 CODEC(Gorilla, LZ4),
    volume Float64 CODEC(Gorilla, LZ4),

    -- Additional microstructure metrics (Binance 11-column format)
    close_time DateTime64(3) CODEC(DoubleDelta, LZ4),
    quote_asset_volume Float64 CODEC(Gorilla, LZ4),
    number_of_trades Int64 CODEC(Delta, LZ4),
    taker_buy_base_asset_volume Float64 CODEC(Gorilla, LZ4),
    taker_buy_quote_asset_volume Float64 CODEC(Gorilla, LZ4),

    -- Deduplication support (application-level, preserves zero-gap guarantee)
    _version UInt64 CODEC(Delta, LZ4),  -- Deterministic hash of row content
    _sign Int8 DEFAULT 1                -- ReplacingMergeTree sign (1 for active rows)

) ENGINE = ReplacingMergeTree(_version)
ORDER BY (timestamp, symbol, timeframe, instrument_type)
PARTITION BY toYYYYMMDD(timestamp)
SETTINGS
    index_granularity = 8192,           -- Default granularity (good for time-series)
    allow_nullable_key = 0,             -- Disallow NULL in ORDER BY keys (data quality)
    merge_with_ttl_timeout = 86400;     -- Merge within 24 hours (background deduplication)

-- Rationale:
-- 1. ReplacingMergeTree(_version): Handles duplicates via background merges
--    - _version is deterministic hash of (timestamp, OHLCV, symbol, timeframe, instrument_type)
--    - Identical writes → identical _version → consistent merge outcome
--    - Preserves zero-gap guarantee via deterministic deduplication
--
-- 2. ORDER BY composite key: (timestamp, symbol, timeframe, instrument_type)
--    - Optimizes queries filtering by these columns
--    - ClickHouse uses ORDER BY as primary key (unlike PostgreSQL)
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
-- 6. DateTime64(3): Millisecond precision
--    - Matches Binance kline data timestamp format
--    - ClickHouse equivalent to QuestDB TIMESTAMP type

-- Zero-Gap Guarantee:
-- Unlike QuestDB DEDUP ENABLE UPSERT KEYS (immediate consistency),
-- ClickHouse uses eventual consistency (duplicates visible until merge).
-- Application-level deterministic versioning ensures consistent merge outcomes.
--
-- Query pattern for deduplicated results:
--   SELECT * FROM ohlcv FINAL WHERE symbol = 'BTCUSDT' AND timeframe = '1h';
--
-- FINAL keyword forces deduplication at query time (10-30% performance overhead).
-- This is an acceptable trade-off for zero-gap guarantee preservation.

-- Migration from QuestDB (ADR-0003):
-- QuestDB SYMBOL → ClickHouse LowCardinality(String)
-- QuestDB DEDUP ENABLE UPSERT KEYS → ClickHouse ReplacingMergeTree(_version)
-- QuestDB PARTITION BY DAY → ClickHouse PARTITION BY toYYYYMMDD(timestamp)
-- QuestDB PostgreSQL wire protocol → ClickHouse native protocol (clickhouse-driver)
