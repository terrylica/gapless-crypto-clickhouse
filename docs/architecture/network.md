# Network Architecture

**Last Updated**: 2025-01-19

**Status**: Empirically Validated - DO NOT modify without evidence

## Data Source

**Provider**: AWS S3 + CloudFront CDN

**Infrastructure**:
- 400+ edge locations globally
- 99.99% SLA
- Automatic failover and routing

## Download Strategy

### Dual Approach

The package uses two different HTTP clients optimized for different use cases:

**Monthly/Daily Files** (Primary Data Collection):
- **Client**: `urllib` (Python standard library)
- **Performance**: 2x faster for single large files
- **Use Case**: CloudFront CDN downloads of monthly/daily ZIP archives
- **Rationale**: Simple HTTP requests, no connection pooling overhead

**Concurrent Downloads** (Gap Filling):
- **Client**: `httpx` with connection pooling
- **Use Case**: Multiple small requests to Binance REST API
- **Configuration**:
  - `max_keepalive_connections=20`
  - `max_connections=30`
  - `keepalive_expiry=30.0`

## Connection Pooling

**When Used**:
- Concurrent API requests (gap filling via Binance REST API)
- Multiple small requests benefit from connection reuse

**When NOT Used**:
- CloudFront CDN downloads
- Each request routed to different edge server
- Connection pooling provides no benefit

**Empirical Evidence**: Testing showed urllib is 2x faster than httpx for single large CloudFront downloads due to eliminated pooling overhead.

## Retry Logic

**CloudFront Behavior**: Automatic failover handled at CDN level

**Production Results**:
- 0% failure rate in production usage
- CDN automatically routes around failed edge servers
- No application-level retry logic required

## Optimization Opportunities

**ETag-Based Caching** (Future Enhancement):
- CloudFront supports ETag headers
- Bandwidth reduction for repeat downloads
- Status: Not implemented (v1.0.0)

## Related Documentation

- [Architecture Overview](OVERVIEW.md) - Complete system architecture
- [Core Components](CORE_COMPONENTS.md) - Component descriptions and data flow
- [Data Collection Guide](../guides/DATA_COLLECTION.md) - Usage and troubleshooting
