# ADR-0010: Optional Development Tooling Enhancement (chdig)

## Status

Implemented (2025-11-18)

## Context

### Problem Statement

ADR-0008 (ClickHouse Local Visualization Toolchain) documented chdig as an optional Tier 2 tool for performance monitoring and profiling. Current validation shows 6/6 critical tools operational, but chdig remains uninstalled despite being documented as available.

**Current State**:
- Validation script checks for chdig but shows warning: "chdig not installed (optional)"
- Performance monitoring capability documented but not enabled
- Development environment lacks TUI-based query profiling and flamegraph visualization

**Impact**:
- Incomplete tooling setup (documented but not installed)
- No local performance profiling capability for slow query investigation
- Developers must use SQL-based system table queries for performance analysis

**Scope**: Local development environment enhancement, zero impact on production or CI/CD

### Documented Tool (ADR-0008)

**chdig** (ClickHouse Dig):
- Rust-based TUI for ClickHouse performance monitoring
- Features: flamegraph visualization, slow query analysis, live metrics, cluster support
- License: MIT
- Installation: `brew install chdig`
- Status: Pre-alpha (interface may change, monitoring-only)

### Decision Drivers

1. **Completeness**: Install all documented tools to match ADR-0008 specification
2. **Observability**: Enable local performance profiling for development workflows
3. **Developer Experience**: Provide modern TUI alternative to SQL-based monitoring
4. **Low Risk**: Optional tool, pre-alpha acceptable for local development

## Decision

**Install chdig via Homebrew** to complete the full 5-tool visualization stack documented in ADR-0008.

### Implementation Strategy

**Single-Step Installation**: Homebrew installation with validation

**Rationale**: chdig already documented and validated script already checks for it. Installation completes the planned toolchain.

**Scope Limitation**: Local development only, not required for CI/CD or production

## Implementation

### Installation

```bash
# Install via Homebrew
brew install chdig

# Verify installation
chdig --version
```

**Expected Output**: Version string (e.g., `chdig 0.x.x`)

### Validation

```bash
# Run validation script
bash scripts/validate-clickhouse-tools.sh
```

**Expected Change**:
- Before: `⚠️ WARN: chdig not installed (optional)`
- After: `✅ PASS: chdig installed and operational`
- Test count: 6/6 → 7/7

### Usage

```bash
# Monitor local ClickHouse instance
chdig --host localhost --port 9000

# View slow queries, system metrics, flamegraphs
# Navigate TUI with keyboard shortcuts
```

**Use Cases**:
- Investigate slow queries during development
- Profile query execution plans
- Monitor system resource usage
- Analyze ClickHouse performance bottlenecks

## Validation

### Automated Validation

**Installation Check**:
```bash
command -v chdig && echo "✅ Installed"
```
**Expected**: Exit code 0

**Functional Check**:
```bash
chdig --version
```
**Expected**: Version output

**Integration Check**:
```bash
bash scripts/validate-clickhouse-tools.sh | grep chdig
```
**Expected**: `✅ PASS: chdig installed and operational`

### Manual Validation Checklist

- [ ] chdig installed via Homebrew
- [ ] chdig --version returns version string
- [ ] chdig connects to localhost:9000 (ClickHouse)
- [ ] TUI displays system metrics and query statistics
- [ ] Validation script passes 7/7 tests

## Consequences

### Positive

- **Complete Tooling**: All 5 tools from ADR-0008 now operational (7/7 validation)
- **Enhanced Observability**: TUI-based performance monitoring available locally
- **Developer Productivity**: Faster performance investigation (no SQL queries needed)
- **Modern UX**: Rust-based TUI with flamegraph support
- **Consistency**: Implementation matches documentation

### Negative

- **Pre-Alpha Risk**: chdig interface may change (acceptable for optional local tool)
- **Homebrew Dependency**: Requires Homebrew (already standard on macOS)
- **Limited Scope**: Monitoring-only, no data manipulation

### Neutral

- **Optional Tool**: Not required for core workflows, development-only enhancement
- **No Production Impact**: Local tooling change only

## Alternatives Considered

### Alternative 1: Skip chdig Installation (Rejected)

**Pros**: No additional dependencies, simpler setup

**Cons**:
- Documentation-implementation mismatch (tool documented but not installed)
- Missing performance monitoring capability
- Validation script perpetually shows warning

**Verdict**: Rejected - contradicts completeness principle

### Alternative 2: Remove chdig from Documentation (Rejected)

**Pros**: Sync documentation with current state

**Cons**:
- Loses valuable observability tool
- Degrades developer experience
- chdig is actively maintained and stable enough for local use

**Verdict**: Rejected - tool provides significant value

### Alternative 3: Wait for chdig v1.0 Stable (Rejected)

**Pros**: Avoid pre-alpha risk

**Cons**:
- Indefinite wait (no v1.0 timeline)
- Pre-alpha acceptable for local optional tool
- Current version functional and stable

**Verdict**: Rejected - pre-alpha risk acceptable for this use case

## Compliance

- **Error Handling**: Homebrew installation fails fast if brew unavailable
- **SLOs**:
  - Availability: Tool installed and accessible via PATH
  - Correctness: Validation script confirms chdig --version succeeds
  - Observability: chdig provides TUI monitoring capability
  - Maintainability: Homebrew handles updates (brew upgrade chdig)
- **OSS Preference**: chdig is MIT licensed, open source
- **Auto-Validation**: Automated validation script checks installation
- **Semantic Release**: chore commit type (tooling enhancement, no API changes)

## References

- ADR-0008: ClickHouse Local Visualization Toolchain
- chdig repository: https://github.com/azat/chdig
- Plan: `docs/plan/0010-optional-development-tooling-chdig/plan.yaml`
