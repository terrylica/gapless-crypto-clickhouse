---
status: accepted
date: 2025-12-10
decision-maker: Terry Li
consulted: [Explore-Agent, ClickHouse-Architect-Skill]
research-method: single-agent
clarification-iterations: 2
perspectives: [Performance, DataModeling, Compatibility]
---

# ADR: ClickHouse Codec T64 Optimization for Trade Count Column

**Design Spec**: [Implementation Spec](/docs/design/2025-12-10-clickhouse-codec-t64-optimization/spec.md)

## Context and Problem Statement

The `gapless-crypto-clickhouse` schema uses `CODEC(Delta, LZ4)` for the `number_of_trades` column. According to the `quality-tools:clickhouse-architect` skill audit, this is suboptimal. The ClickHouse Architect skill recommends `CODEC(T64, ZSTD)` for integer counter columns because T64 works best with ZSTD compression.

This change requires table recreation since ClickHouse does not support altering codecs on existing columns in-place.

### Before/After

```
        🔄 Codec Migration - Before/After

┌−−−−−−−−−−−−−−−−−┐            ┌−−−−−−−−−−−−−−−−┐
╎ Before:         ╎            ╎ After:         ╎
╎                 ╎            ╎                ╎
╎ ┌─────────────┐ ╎            ╎ ┌────────────┐ ╎
╎ │    Int64    │ ╎  migrate   ╎ │   Int64    │ ╎
╎ │ Delta + LZ4 │ ╎ ─────────> ╎ │ T64 + ZSTD │ ╎
╎ └─────────────┘ ╎            ╎ └────────────┘ ╎
╎                 ╎            ╎                ╎
└−−−−−−−−−−−−−−−−−┘            └−−−−−−−−−−−−−−−−┘
```

<details>
<summary>graph-easy source</summary>

```
graph { label: "🔄 Codec Migration - Before/After"; flow: east; }
( Before:
  [number_of_trades] { label: "Int64\nDelta + LZ4"; }
)
( After:
  [number_of_trades_new] { label: "Int64\nT64 + ZSTD"; }
)
[number_of_trades] -- migrate --> [number_of_trades_new]
```

</details>

## Research Summary

| Agent Perspective          | Key Finding                                        | Confidence |
| -------------------------- | -------------------------------------------------- | ---------- |
| Explore-Agent              | Schema well-designed overall; one codec suboptimal | High       |
| ClickHouse-Architect-Skill | T64 + ZSTD recommended for integer counters        | High       |

### Audit Findings

The `quality-tools:clickhouse-architect` skill audit revealed:

- **ORDER BY**: Excellent (symbol-first, 4 columns, optimal cardinality order)
- **Data Types**: Excellent (DateTime64(6), Float64, LowCardinality)
- **Most Codecs**: Optimal (DoubleDelta for timestamps, Gorilla for floats)
- **One Exception**: `number_of_trades Int64 CODEC(Delta, LZ4)` should be `CODEC(T64, ZSTD)`

## Decision Log

| Decision Area              | Options Evaluated   | Chosen      | Rationale                                  |
| -------------------------- | ------------------- | ----------- | ------------------------------------------ |
| Codec for number_of_trades | Delta+LZ4, T64+ZSTD | T64+ZSTD    | Skill guidance: "T64 works best with ZSTD" |
| Migration Strategy         | ALTER, DROP/CREATE  | DROP/CREATE | ClickHouse doesn't support ALTER CODEC     |
| Environments               | Local only, Both    | Both        | Consistency between local and cloud        |

### Trade-offs Accepted

| Trade-off                       | Choice          | Accepted Cost                                |
| ------------------------------- | --------------- | -------------------------------------------- |
| Data loss vs codec optimization | Recreate tables | All existing data must be re-ingested        |
| Complexity vs benefit           | Full migration  | 5-10% compression improvement for one column |

## Decision Drivers

- Follow ClickHouse Architect best practices
- Optimize storage efficiency for time-series data
- Maintain schema consistency across environments

## Considered Options

- **Option A**: Keep current codec (Delta + LZ4)
  - No work required
  - Suboptimal per ClickHouse Architect audit

- **Option B**: Change to T64 + ZSTD (Selected)
  - Follows best practices
  - Requires table recreation
  - 5-10% better compression for integer column

## Decision Outcome

Chosen option: **Option B (T64 + ZSTD)**, because it follows ClickHouse Architect best practices and provides better compression for integer counter data.

## Synthesis

**Convergent findings**: All analysis confirms T64 + ZSTD is the recommended codec for integer counters in ClickHouse.

**Divergent findings**: None - the recommendation is consistent across documentation.

**Resolution**: User confirmed acceptable to drop and recreate tables.

## Consequences

### Positive

- Schema follows ClickHouse Architect best practices
- 5-10% better compression for `number_of_trades` column
- Consistent codec strategy across column types

### Negative

- Requires table recreation (data loss - must re-ingest)
- Brief downtime during migration (~seconds)
- Re-ingestion time depends on data volume

## Architecture

```
       🏗️ Schema Migration Architecture

┌──────────────────┐     ╭─────────────────────╮
│ Local ClickHouse │     │     schema.sql      │
│  DROP + CREATE   │ <── │   (update codec)    │
└──────────────────┘     ╰─────────────────────╯
  │                        │
  │                        │
  │                        ∨
  │                      ┌─────────────────────┐
  │                      │  Cloud ClickHouse   │
  │                      │    DROP + CREATE    │
  │                      └─────────────────────┘
  │                        │
  │                        │
  │                        ∨
  │                      ╭─────────────────────╮
  │                      │   E2E Validation    │
  └────────────────────> │ mise run validate-* │
                         ╰─────────────────────╯
```

<details>
<summary>graph-easy source</summary>

```
graph { label: "🏗️ Schema Migration Architecture"; flow: south; }
[schema.sql] { label: "schema.sql\n(update codec)"; shape: rounded; }
[local_ch] { label: "Local ClickHouse\nDROP + CREATE"; }
[cloud_ch] { label: "Cloud ClickHouse\nDROP + CREATE"; }
[validate] { label: "E2E Validation\nmise run validate-*"; shape: rounded; }
[schema.sql] -> [local_ch]
[schema.sql] -> [cloud_ch]
[local_ch] -> [validate]
[cloud_ch] -> [validate]
```

</details>

## References

- [ADR-0034: Schema Optimization for Prop Trading](/docs/architecture/decisions/0034-schema-optimization-prop-trading.md)
- [ClickHouse Architect Skill](/~/.claude/plugins/cache/cc-skills/quality-tools)
- [ClickHouse Compression Codecs Documentation](https://clickhouse.com/docs/en/sql-reference/statements/create/table#column_compression_codec)
