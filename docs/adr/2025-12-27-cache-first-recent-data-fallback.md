---
status: proposed
date: 2025-12-27
decision-maker: Terry Li
consulted: [SDK Users, Alpha-Forge Consumers]
research-method: multi-agent
clarification-iterations: 3
perspectives:
  [Data Architecture, Cache Strategy, Network Resilience, REST API Patterns]
---

# Cache-First Architecture with REST API Fallback for Recent Data

**Design Spec**: [Implementation Spec](/docs/design/2025-12-27-cache-first-recent-data-fallback/spec.md)

## Context and Problem Statement

The `gapless-crypto-clickhouse` package should fetch data from remote sources (exchange APIs) and use ClickHouse as a cache. While the current `query_ohlcv()` implementation already follows a cache-first pattern, there is a gap when requesting same-day or recent data.

### Current Architecture Gap

When CDN archives don't exist (same-day/recent data), the auto-ingest step fails silently:

```
query_ohlcv("BTCUSDT", "1h", "2025-12-26", "2025-12-27")  # Today's data

Step 1: Check ClickHouse → empty
Step 2: Attempt CDN download → HTTP 404 (daily ZIP not published yet)
Step 3: Query returns empty DataFrame
Step 4: Gap detection fails (no baseline data to detect gaps from)
```

### Before: Same-Day Data Request

```
⏮️ Before: Same-Day Data Request

     ╭──────────────────────╮
     │         User         │
     ╰──────────────────────╯
       │
       │
       ∨
     ┌──────────────────────┐
     │    query_ohlcv()     │
     │ ("2025-12-27" today) │
     └──────────────────────┘
       │
       │
       ∨
     ┌──────────────────────┐
     │ Check ClickHouse     │
     │     (empty)          │
     └──────────────────────┘
       │
       │
       ∨
     ┌──────────────────────┐
     │ CDN ingest_month()   │
     └──────────────────────┘
       │
       │ HTTP 404
       ∨
     ╔══════════════════════╗
     ║   Empty DataFrame    ║
     ║   (data not found)   ║
     ╚══════════════════════╝
```

<details>
<summary>graph-easy source</summary>

```
graph { label: "⏮️ Before: Same-Day Data Request"; flow: south; }
[ User ] { shape: rounded; }
[ query_ohlcv()\n("2025-12-27" today) ]
[ Check ClickHouse\n(empty) ]
[ CDN ingest_month() ]
[ Empty DataFrame\n(data not found) ] { border: double; }

[ User ] -> [ query_ohlcv()\n("2025-12-27" today) ]
[ query_ohlcv()\n("2025-12-27" today) ] -> [ Check ClickHouse\n(empty) ]
[ Check ClickHouse\n(empty) ] -> [ CDN ingest_month() ]
[ CDN ingest_month() ] -- HTTP 404 --> [ Empty DataFrame\n(data not found) ]
```

</details>

### After: Same-Day Data Request with REST API Fallback

```
⏭️ After: Same-Day Data Request with REST API Fallback

     ╭──────────────────────╮
     │         User         │
     ╰──────────────────────╯
       │
       │
       ∨
     ┌──────────────────────┐
     │    query_ohlcv()     │
     │ ("2025-12-27" today) │
     └──────────────────────┘
       │
       │
       ∨
     ┌──────────────────────┐
     │ Check ClickHouse     │
     │     (empty)          │
     └──────────────────────┘
       │
       │
       ∨
     ┌──────────────────────┐
     │ CDN ingest_month()   │
     └──────────────────────┘
       │
       │ HTTP 404
       ∨
     ┌──────────────────────┐
     │ [+] _is_recent()?    │ ─┐
     └──────────────────────┘  │
       │                       │
       │ Yes                   │ No
       ∨                       │
     ┌──────────────────────┐  │
     │ [+] REST API ingest  │  │
     │ (exponential backoff)│  │
     └──────────────────────┘  │
       │                       │
       │                       ∨
       │                     ╔══════════════════════╗
       │                     ║        Raise         ║
       │                     ╚══════════════════════╝
       ∨
     ┌──────────────────────┐
     │ Insert to ClickHouse │
     └──────────────────────┘
       │
       │
       ∨
      ══════════════════════
     ║      DataFrame       ║
     ║   (real-time data)   ║
      ══════════════════════
```

<details>
<summary>graph-easy source</summary>

```
graph { label: "⏭️ After: Same-Day Data Request with REST API Fallback"; flow: south; }
[ User ] { shape: rounded; }
[ query_ohlcv()\n("2025-12-27" today) ]
[ Check ClickHouse\n(empty) ]
[ CDN ingest_month() ]
[ _is_recent()? ] { label: "[+] _is_recent()?"; }
[ REST API ingest\n(exponential backoff) ] { label: "[+] REST API ingest\n(exponential backoff)"; }
[ Insert to ClickHouse ]
[ DataFrame\n(real-time data) ] { border: double; shape: rounded; }
[ Raise ] { border: double; }

[ User ] -> [ query_ohlcv()\n("2025-12-27" today) ]
[ query_ohlcv()\n("2025-12-27" today) ] -> [ Check ClickHouse\n(empty) ]
[ Check ClickHouse\n(empty) ] -> [ CDN ingest_month() ]
[ CDN ingest_month() ] -- HTTP 404 --> [ _is_recent()? ]
[ _is_recent()? ] -- Yes --> [ REST API ingest\n(exponential backoff) ]
[ _is_recent()? ] -- No --> [ Raise ]
[ REST API ingest\n(exponential backoff) ] -> [ Insert to ClickHouse ]
[ Insert to ClickHouse ] -> [ DataFrame\n(real-time data) ]
```

</details>

## Decision Drivers

- **Lazy real-time data access**: Users expect `query_ohlcv()` to return data for any date including today
- **Cache-first efficiency**: Avoid wasting network resources by checking ClickHouse before remote fetch
- **No TTL for historical data**: Immutable historical data never expires (ReplacingMergeTree handles updates)
- **Network resilience**: REST API must handle rate limits and transient failures gracefully
- **ADR compliance**: Must respect ADR-0001 (raise and propagate), ADR-0040 (tenacity patterns), ADR-0046 (centralized constants)

## Considered Options

1. **REST API fallback in auto-ingest with exponential backoff** (recommended)
2. **Document as known limitation** (T-1 data only)
3. **Always use REST API** (bypass CDN, wasteful for historical data)

## Decision Outcome

Chosen option: **Option 1 - REST API fallback in auto-ingest with exponential backoff**

The implementation adds REST API fallback to `_auto_ingest_date_range()` when CDN returns HTTP 404 for recent months, and upgrades the retry logic from linear to exponential backoff with jitter.

### Key Changes

1. **Add `_is_recent_month()` helper**: Detect if month is within CDN publication lag window (T-2 days)
2. **Add `_ingest_recent_from_api()` function**: Ingest data via REST API when CDN unavailable
3. **Modify `_auto_ingest_date_range()`**: Catch HTTP 404, fallback to REST API for recent months
4. **Upgrade retry logic**: Change from linear (1s→2s→3s) to exponential with jitter (AWS best practice)
5. **Add `RETRY_JITTER` constant**: Centralize jitter configuration per ADR-0046

### Consequences

**Good**:

- Same-day data queries work without user intervention
- Data is automatically cached in ClickHouse for subsequent queries
- Historical data still uses CDN (22x faster)
- Exponential backoff with jitter prevents thundering herd
- No breaking changes to existing API

**Bad**:

- Same-day queries slightly slower (REST API vs CDN)
- More retry attempts (5 instead of 3) may increase latency on persistent failures

**Neutral**:

- `fill_gaps=True` (Step 4) still runs after REST API ingest for completeness

## Architecture

```
🏗️ Cache-First Architecture with REST API Fallback

  ╭────────────╮
  │ User Code  │
  ╰────────────╯
        │
        │
        ∨
  ┌─────────────────┐
  │  query_ohlcv()  │
  └─────────────────┘
        │
        │
        ∨
  ┌─────────────────┐     ╔════════════╗
  │ Check ClickHouse│ ──> ║ ClickHouse ║
  │ (Step 1: COUNT) │     ╚════════════╝
  └─────────────────┘           │
        │                       │ cache hit
        │ cache miss            ∨
        ∨                 ┌─────────────────┐
  ┌─────────────────┐     │ Return cached   │
  │ Auto-Ingest     │     │ data (fast)     │
  │ (Step 2)        │     └─────────────────┘
  └─────────────────┘
        │
        ├───────────────────────────────────────┐
        │                                       │
        ∨                                       ∨
  ┌─────────────────┐                     ┌─────────────────┐
  │ Try CDN ingest  │                     │ [+] REST API    │
  │ (CloudFront)    │ ─── HTTP 404 ───>   │ ingest fallback │
  └─────────────────┘                     └─────────────────┘
        │                                       │
        │ success                               │
        ∨                                       ∨
  ┌─────────────────┐                     ┌─────────────────┐
  │ Insert to       │                     │ Insert to       │
  │ ClickHouse      │                     │ ClickHouse      │
  └─────────────────┘                     └─────────────────┘
        │                                       │
        └───────────────────┬───────────────────┘
                            │
                            ∨
                      ┌─────────────────┐
                      │ Query with FINAL│
                      │ (Step 3)        │
                      └─────────────────┘
                            │
                            ∨
                      ┌─────────────────┐
                      │ Gap Filling     │
                      │ (Step 4)        │
                      └─────────────────┘
                            │
                            ∨
                       ══════════════════
                      ║    DataFrame    ║
                       ══════════════════
```

<details>
<summary>graph-easy source</summary>

```
graph { label: "🏗️ Cache-First Architecture with REST API Fallback"; flow: south; }
[ User Code ] { shape: rounded; }
[ query_ohlcv() ]
[ Check ClickHouse\n(Step 1: COUNT) ]
[ ClickHouse ] { border: double; }
[ Return cached\ndata (fast) ]
[ Auto-Ingest\n(Step 2) ]
[ Try CDN ingest\n(CloudFront) ]
[ REST API\ningest fallback ] { label: "[+] REST API\ningest fallback"; }
[ Insert to\nClickHouse (CDN) ] { label: "Insert to\nClickHouse"; }
[ Insert to\nClickHouse (API) ] { label: "Insert to\nClickHouse"; }
[ Query with FINAL\n(Step 3) ]
[ Gap Filling\n(Step 4) ]
[ DataFrame ] { border: double; shape: rounded; }

[ User Code ] -> [ query_ohlcv() ]
[ query_ohlcv() ] -> [ Check ClickHouse\n(Step 1: COUNT) ]
[ Check ClickHouse\n(Step 1: COUNT) ] -> [ ClickHouse ]
[ ClickHouse ] -- cache hit --> [ Return cached\ndata (fast) ]
[ Check ClickHouse\n(Step 1: COUNT) ] -- cache miss --> [ Auto-Ingest\n(Step 2) ]
[ Auto-Ingest\n(Step 2) ] -> [ Try CDN ingest\n(CloudFront) ]
[ Try CDN ingest\n(CloudFront) ] -- HTTP 404 --> [ REST API\ningest fallback ]
[ Try CDN ingest\n(CloudFront) ] -- success --> [ Insert to\nClickHouse (CDN) ]
[ REST API\ningest fallback ] -> [ Insert to\nClickHouse (API) ]
[ Insert to\nClickHouse (CDN) ] -> [ Query with FINAL\n(Step 3) ]
[ Insert to\nClickHouse (API) ] -> [ Query with FINAL\n(Step 3) ]
[ Query with FINAL\n(Step 3) ] -> [ Gap Filling\n(Step 4) ]
[ Gap Filling\n(Step 4) ] -> [ DataFrame ]
```

</details>

### Component Changes

| Component                    | Change                                                                                    | Impact                            |
| ---------------------------- | ----------------------------------------------------------------------------------------- | --------------------------------- |
| `query_api.py`               | Add `_is_recent_month()`, `_ingest_recent_from_api()`, modify `_auto_ingest_date_range()` | REST API fallback for recent data |
| `gap_filling/rest_client.py` | Upgrade to `wait_exponential_jitter`                                                      | Better retry resilience           |
| `constants/network.py`       | Add `RETRY_JITTER`, `RETRY_EXP_MAX`                                                       | Centralized constants             |

### Data Flow

```
Before (same-day query):
  query_ohlcv("2025-12-27") → CDN 404 → empty DataFrame

After (same-day query):
  query_ohlcv("2025-12-27") → CDN 404 → REST API → ClickHouse → DataFrame with data
```

## Validation

### Success Criteria

- [ ] `query_ohlcv("BTCUSDT", "1h", "2025-12-27", "2025-12-27")` returns today's data
- [ ] Data is cached in ClickHouse for subsequent queries
- [ ] Historical data still uses CDN (22x faster)
- [ ] No breaking changes to existing API
- [ ] REST API pagination uses exponential backoff with jitter
- [ ] Rate limit handling respects `retry_after` header

### Testing Plan

| Test                            | Location                    | Description                              |
| ------------------------------- | --------------------------- | ---------------------------------------- |
| `test_is_recent_month`          | `tests/test_query_api.py`   | Verify recent month detection            |
| `test_auto_ingest_cdn_fallback` | `tests/test_query_api.py`   | Verify REST API fallback on CDN 404      |
| `test_exponential_backoff`      | `tests/test_rest_client.py` | Verify retry timing with jitter          |
| `test_same_day_query_cached`    | `tests/test_query_api.py`   | Verify data cached after REST API ingest |

## Decision Log

| Date       | Decision                                     | Rationale                                      |
| ---------- | -------------------------------------------- | ---------------------------------------------- |
| 2025-12-27 | Fallback only for recent months (T-2 days)   | Avoid masking genuine 404s for historical data |
| 2025-12-27 | Reuse `fetch_gap_data()` for REST API ingest | No new REST client code needed                 |
| 2025-12-27 | Exponential backoff with full jitter         | AWS best practice, prevents thundering herd    |
| 2025-12-27 | 5 retry attempts (up from 3)                 | More resilience for transient failures         |

## Related Decisions

- **ADR-0001**: Error handling philosophy (raise and propagate)
- **ADR-0040**: query_ohlcv() gap filling implementation (tenacity patterns)
- **ADR-0046**: Centralized constants (RETRY\_\* constants)
- **ADR-0048**: \_version hash computation (ClickHouse DEFAULT expressions)

## More Information

- [Implementation Spec](/docs/design/2025-12-27-cache-first-recent-data-fallback/spec.md)
- [Global Plan](/Users/terryli/.claude/plans/idempotent-humming-eich.md) (ephemeral)
