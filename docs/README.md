# Gapless Crypto Data Documentation

This directory contains comprehensive documentation for the gapless-crypto-data package.

## Documentation Structure

### API Documentation

- [`api/quick-start.md`](api/quick-start.md) - API quick start guide
- [`api/dual-parameter-enhancement.yaml`](api/dual-parameter-enhancement.yaml) - OpenAPI specification

### User Guides

- [`guides/pypi-documentation.md`](guides/pypi-documentation.md) - Complete API documentation for PyPI users

### Development Documentation

- [`development/PUBLISHING.md`](development/PUBLISHING.md) - Package publishing guidelines
- [`CURRENT_ARCHITECTURE_STATUS.yaml`](CURRENT_ARCHITECTURE_STATUS.yaml) - Current system architecture

### Release Documentation

- [`release-notes.md`](release-notes.md) - Release notes and announcements
- [`milestones/`](milestones/) - Version milestone documentation

### Project Milestones

The `milestones/` directory contains detailed documentation for each version release:

- **Current Version**: v2.7.0 - CCXT-Compatible Dual Parameter Support
- **Previous Versions**: v2.0.0 through v2.6.1 with comprehensive implementation details

## Getting Started

For new users, we recommend starting with:

1. **[Project README](../README.md)** - Overview and installation
2. **[API Quick Start](api/quick-start.md)** - Basic usage examples
3. **[PyPI Documentation](guides/pypi-documentation.md)** - Complete API reference

### Database Integration (v4.0.0+)

For users leveraging ClickHouse database features:

1. **[ClickHouse Migration Guide](CLICKHOUSE_MIGRATION.md)** - Migrating from v3.x file-based to v4.0.0 database integration
2. **[ADR-0005: ClickHouse Migration Decision](architecture/decisions/0005-clickhouse-migration.md)** - Technical rationale and implementation details
3. **[Docker Compose Setup](../docker-compose.yml)** - Production-ready ClickHouse container configuration

**Breaking Changes**: v4.0.0 introduces optional ClickHouse database support. File-based workflows remain supported for backward compatibility.

### Validation System (v3.3.0+, v6.0.0 canonical)

Comprehensive data quality validation framework:

1. **[Validation Architecture](validation/ARCHITECTURE.md)** - Three-layer validation system (CSV, ClickHouse, Performance)
2. **[Validation Overview](validation/OVERVIEW.md)** - 5-layer CSV validation pipeline with DuckDB persistence
3. **[E2E Testing Guide](validation/E2E_TESTING_GUIDE.md)** - Playwright E2E validation with visual regression
4. **[ADR-0024: Validation Canonicity](architecture/decisions/0024-comprehensive-validation-canonicity.md)** - v6.0.0 comprehensive validation update

## Development

For contributors and developers:

1. **[Contributing Guidelines](../CONTRIBUTING.md)** - How to contribute
2. **[Publishing Documentation](development/PUBLISHING.md)** - Release process
3. **[Architecture Status](CURRENT_ARCHITECTURE_STATUS.yaml)** - Technical overview

## Support

- **Issues**: [GitHub Issues](https://github.com/terrylica/gapless-crypto-clickhouse/issues)
- **Discussions**: [GitHub Discussions](https://github.com/terrylica/gapless-crypto-clickhouse/discussions)
- **Email**: terry@eonlabs.com
