# Documentation Hub

Complete documentation for gapless-crypto-clickhouse - ultra-fast cryptocurrency data collection from Binance's public repository with zero-gap guarantee.

**Version**: 1.0.0 | **Type**: Cryptocurrency Data Collection | **Compatibility**: UV-native Python SDK

---

## Quick Navigation

- [Getting Started](#getting-started) - Installation, quick start, first steps
- [User Guides](#user-guides) - API usage, tutorials, how-to guides
- [Examples](#examples) - Code examples from simple to advanced
- [API Reference](#api-reference) - Technical specifications, standards
- [Development](#development) - Contributing, architecture, build guides
- [Release Documentation](#release-documentation) - Changelogs, release notes

---

## Getting Started

**New to gapless-crypto-clickhouse? Start here.**

### Core Documentation

- [README.md](README.md) - Main project documentation
  - Installation (uv, pip, pipx)
  - Quick start (Python API and CLI - **CLI deprecated**)
  - Feature overview
  - Supported symbols and timeframes
  - **Start here for first-time users**

- [docs/README.md](docs/README.md) - Documentation structure overview
  - Navigation guide to all documentation sections
  - Recommended learning path

### Quick Start Guides

- [docs/api/quick-start.md](docs/api/quick-start.md) - Quick start guide
  - Simple API examples
  - Advanced usage patterns
  - Common workflows

- [examples/README.md](examples/README.md) - Examples catalog
  - Quick start workflows
  - Example descriptions
  - Use case categorization

### AI Agent Integration

- [CLAUDE.md](CLAUDE.md) - Claude Code AI assistant guidance
  - Architecture overview
  - Development patterns
  - Network architecture validation
  - Data flow documentation

- [PROBE_USAGE_EXAMPLE.md](PROBE_USAGE_EXAMPLE.md) - AI agent probe hooks
  - API discovery examples
  - Capabilities detection
  - Task graph generation

---

## User Guides

**Learn how to use gapless-crypto-clickhouse effectively.**

### API Documentation

- [docs/guides/pypi-documentation.md](docs/guides/pypi-documentation.md) - Complete API reference (440+ lines)
  - Installation methods
  - Function-based API (simple)
  - Class-based API (advanced)
  - Configuration options
  - **Comprehensive reference for PyPI users**

### Key Concepts

- Zero-gap guarantee - Automatic gap detection and filling
- 22x performance - Faster than API-only collection
- Authentic data - Real Binance market data, never synthetic
- 11-column microstructure format - Complete order flow data

---

## Examples

**Code examples from beginner to advanced.**

### Beginner Examples

- [examples/simple_api_examples.py](examples/simple_api_examples.py) - Function-based API
  - Simplest data collection patterns
  - Single function calls
  - **Perfect for beginners**

- [examples/basic_data_collection.py](examples/basic_data_collection.py) - Basic workflow
  - Standard data collection
  - Simple configuration

- [examples/cli_usage_examples.sh](examples/cli_usage_examples.sh) - CLI patterns ⚠️ **DEPRECATED**
  - Command-line usage examples (legacy)
  - Shell script integration (deprecated in v1.0.0)
  - **Use Python API instead - see [CLI_MIGRATION_GUIDE.md](docs/development/CLI_MIGRATION_GUIDE.md)**

### Intermediate Examples

- [examples/advanced_api_examples.py](examples/advanced_api_examples.py) - Class-based API
  - Complex workflows
  - Custom configuration
  - Multi-symbol collection

- [examples/gap_filling_example.py](examples/gap_filling_example.py) - Gap filling
  - Gap detection demonstration
  - Automatic gap filling
  - Quality validation

### Advanced Examples

- [examples/complete_workflow.py](examples/complete_workflow.py) - End-to-end pipeline
  - Full data collection workflow
  - Validation and gap filling
  - Production-ready patterns

- [examples/safe_data_collection.py](examples/safe_data_collection.py) - Error handling
  - Robust error handling
  - Safe collection patterns
  - Production best practices

---

## API Reference

**Technical specifications and machine-readable documentation.**

### Current Architecture

- [docs/CURRENT_ARCHITECTURE_STATUS.yaml](docs/CURRENT_ARCHITECTURE_STATUS.yaml) - Canonical architecture status
  - OpenAPI 3.1.1 specification
  - Production-ready capabilities
  - Technical status tracking
  - **Single source of truth for current state**

### SDK Quality Standards

- [docs/sdk-quality-standards.yaml](docs/sdk-quality-standards.yaml) - SDK quality specification
  - Type safety standards (PEP 561)
  - Exception hierarchy
  - AI discoverability
  - Coverage targets

### API Enhancement Specifications

- [docs/api/dual-parameter-enhancement.yaml](docs/api/dual-parameter-enhancement.yaml) - CCXT compatibility
  - Dual parameter support (timeframe/interval)
  - Migration guide
  - Backward compatibility

- [docs/api/gapless-dataframe-enhancement.yaml](docs/api/gapless-dataframe-enhancement.yaml) - DataFrame enhancement
  - GaplessDataFrame specification
  - API design rationale

- [docs/api/pruning-parquet-implementation.yaml](docs/api/pruning-parquet-implementation.yaml) - Parquet support
  - Parquet format implementation
  - Dependency pruning strategy

### Stabilization Plans

- [docs/api/v3.0.0-stabilization-plan.yaml](docs/api/v3.0.0-stabilization-plan.yaml) - v3.0.0 stabilization
  - Production readiness roadmap
  - API stability guarantees

- [docs/api/v3.1.0-test-quality-plan.yaml](docs/api/v3.1.0-test-quality-plan.yaml) - Test quality plan
  - Test coverage strategy
  - Quality metrics targets

---

## Development

**Contributing, building, and understanding the architecture.**

### Contributing

- [CONTRIBUTING.md](CONTRIBUTING.md) - Contributing guide
  - Development environment setup
  - Code standards
  - Testing requirements
  - Pull request workflow
  - **Read before contributing**

- [AUTHORS.md](AUTHORS.md) - Contributors and acknowledgments
  - Project contributors
  - Acknowledgments

### Publishing & Release

- [docs/development/PUBLISHING.md](docs/development/PUBLISHING.md) - PyPI publishing guide
  - Automated publishing with GitHub Actions
  - Trusted Publishing (OIDC) setup
  - Sigstore artifact signing
  - Manual publishing fallback

- [docs/PYPI_PUBLISHING_CONFIGURATION.yaml](docs/PYPI_PUBLISHING_CONFIGURATION.yaml) - Publishing configuration
  - GitHub Actions workflow specification
  - Environment variables
  - Security configuration

### Build Documentation

- [UV_BUILD_SUCCESS.md](UV_BUILD_SUCCESS.md) - UV build success
  - UV build system validation
  - Build configuration

### Milestone Planning

- [docs/MILESTONE_v3.0.0.yaml](docs/MILESTONE_v3.0.0.yaml) - v3.0.0 milestone
  - Production stabilization goals
  - Implementation timeline

- [docs/MILESTONE_v3.1.0.yaml](docs/MILESTONE_v3.1.0.yaml) - v3.1.0 milestone
  - Feature roadmap
  - Quality targets

### Audit Documentation

- [CONFORMITY_AUDIT_REPORT.md](CONFORMITY_AUDIT_REPORT.md) - Conformity audit
  - Code quality assessment
  - Standards compliance

- [dead_code_audit_plan.md](dead_code_audit_plan.md) - Dead code audit
  - Dead code detection strategy
  - Cleanup plan

- [docs/audit/comprehensive-audit-plan.yaml](docs/audit/comprehensive-audit-plan.yaml) - Audit plan
  - Comprehensive audit strategy
  - Quality metrics

- [docs/audit/comprehensive-audit-findings.yaml](docs/audit/comprehensive-audit-findings.yaml) - Audit findings
  - Detailed audit results
  - Recommendations

---

## Architecture & Specifications

**Deep technical documentation and machine-readable specifications.**

### Historical Milestones (OpenAPI 3.1.1 Format)

Complete version history with technical details, hard-learned lessons, and implementation rationale.

**v2.15.x Series** (Latest v2 Branch)

- [docs/milestones/MILESTONE_v2.15.1.yaml](docs/milestones/MILESTONE_v2.15.1.yaml) - Latest v2 series
- [docs/milestones/MILESTONE_v2.15.0.yaml](docs/milestones/MILESTONE_v2.15.0.yaml) - AI agent integration

**v2.14.x Series** (DataFrame Simplification)

- [docs/milestones/MILESTONE_v2.14.0.yaml](docs/milestones/MILESTONE_v2.14.0.yaml) - DataFrame simplification

**v2.12.x Series** (GaplessDataFrame)

- [docs/milestones/MILESTONE_v2.12.0.yaml](docs/milestones/MILESTONE_v2.12.0.yaml) - GaplessDataFrame implementation

**v2.11.x Series** (Datetime Enhancement)

- [docs/milestones/MILESTONE_v2.11.0.yaml](docs/milestones/MILESTONE_v2.11.0.yaml) - Datetime index enhancement

**v2.10.x Series** (Dependency Pruning)

- [docs/milestones/MILESTONE_v2.10.0.yaml](docs/milestones/MILESTONE_v2.10.0.yaml) - Dependency pruning & Parquet

**v2.9.x Series** (Performance Optimization)

- [docs/milestones/MILESTONE_v2.9.0.yaml](docs/milestones/MILESTONE_v2.9.0.yaml) - Performance optimization

**v2.8.x Series** (Gap Filling Enhancement)

- [docs/milestones/MILESTONE_v2.8.0.yaml](docs/milestones/MILESTONE_v2.8.0.yaml) - Gap filling enhancement

**v2.7.x Series** (Quality Improvements)

- [docs/milestones/MILESTONE_v2.7.0.yaml](docs/milestones/MILESTONE_v2.7.0.yaml) - Quality improvements

**v2.6.x Series** (CLI Enhancement)

- [docs/milestones/MILESTONE_v2.6.1.yaml](docs/milestones/MILESTONE_v2.6.1.yaml) - Patch release
- [docs/milestones/MILESTONE_v2.6.0.yaml](docs/milestones/MILESTONE_v2.6.0.yaml) - CLI enhancement

**v2.5.x Series** (Validation & Checkpointing)

- [docs/milestones/MILESTONE_v2.5.0.yaml](docs/milestones/MILESTONE_v2.5.0.yaml) - Validation & checkpointing

**v2.4.x Series** (Gap Filling Integration)

- [docs/milestones/MILESTONE_v2.4.0.yaml](docs/milestones/MILESTONE_v2.4.0.yaml) - Gap filling integration

**v2.3.x Series** (Metadata Enhancement)

- [docs/milestones/MILESTONE_v2.3.0.yaml](docs/milestones/MILESTONE_v2.3.0.yaml) - Metadata enhancement

**v2.2.x Series** (Timestamp Format Support)

- [docs/milestones/MILESTONE_v2.2.0.yaml](docs/milestones/MILESTONE_v2.2.0.yaml) - Timestamp format support

**v2.1.x Series** (UTC Timezone Fix)

- [docs/milestones/MILESTONE_v2.1.0.yaml](docs/milestones/MILESTONE_v2.1.0.yaml) - UTC timezone fix

**v2.0.x Series** (Multi-Symbol Support)

- [docs/milestones/MILESTONE_v2.0.1.yaml](docs/milestones/MILESTONE_v2.0.1.yaml) - Patch release
- [docs/milestones/MILESTONE_v2.0.0.yaml](docs/milestones/MILESTONE_v2.0.0.yaml) - Multi-symbol support

---

## Release Documentation

**Changelogs and release notes.**

### Changelogs

- [CHANGELOG.md](CHANGELOG.md) - Complete changelog
  - Follows Keep a Changelog format
  - Categorized by version
  - Breaking changes highlighted

- [docs/release-notes.md](docs/release-notes.md) - Documentation release notes
  - Documentation-specific changes
  - Structural improvements

### Release Notes

- [RELEASE_NOTES.md](RELEASE_NOTES.md) - Detailed release notes
  - Version-specific features
  - Migration guides

- [RELEASE_NOTES_SHORT.md](RELEASE_NOTES_SHORT.md) - Short release notes
  - Quick version summaries
  - Key highlights only

---

## Documentation Statistics

- **Total Files**: 65+ documentation files
- **Formats**: Markdown (26), YAML (36+), Python examples (5), Shell (1)
- **Milestone Tracking**: 28 version milestones (v2.0.0 → v2.15.1)
- **OpenAPI Compliance**: All YAML specifications follow OpenAPI 3.1.1
- **AI-Readable**: Machine-parseable YAML specifications for AI coding agents

---

## Documentation Conventions

### Markdown Files

- GitHub Flavored Markdown throughout
- Relative links from project root
- Clear section headings
- Code examples with syntax highlighting

### YAML Specifications

- OpenAPI 3.1.1 format
- Machine-readable for AI agents
- Structured with metadata, goals, implementation details
- Hard-learned lessons captured

### Examples

- Runnable Python/shell code
- Comprehensive comments
- Progressive complexity (simple → advanced)
- Production-ready patterns

---

## Need Help?

- **Quick Start**: [docs/api/quick-start.md](docs/api/quick-start.md)
- **API Reference**: [docs/guides/pypi-documentation.md](docs/guides/pypi-documentation.md)
- **Examples**: [examples/README.md](examples/README.md)
- **Contributing**: [CONTRIBUTING.md](CONTRIBUTING.md)
- **Issues**: [GitHub Issues](https://github.com/terrylica/gapless-crypto-clickhouse/issues)

---

**Last Updated**: 2025-10-18 (v3.2.0)
