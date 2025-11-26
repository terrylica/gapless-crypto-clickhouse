# ADR-0042: Documentation Rectification

## Status

Accepted (2025-11-25)

## Context

9-agent parallel audit revealed ~1,140 documentation issues across 110 files:

| Category | Issues | Severity |
|----------|--------|----------|
| Package name violations | 283 | CRITICAL |
| Code blocks without language tags | 530+ | HIGH |
| Architecture inaccuracies | 7 | CRITICAL |
| Broken code examples | 3 | CRITICAL |
| Broken links | 105 | HIGH |
| API documentation gaps | 6 | MODERATE |

Root cause: Fork from `gapless-crypto-data` (ADR-0011) performed code rename but incomplete documentation update.

## Decision

Implement systematic documentation rectification with:

1. **Package name updates**: Fix all except ADRs (preserve historical context) and cache paths (per ADR-0012)
2. **Architecture corrections**: Update OVERVIEW.md with accurate schema, ORDER BY, scope
3. **Code block formatting**: Add language tags to all 530+ blocks
4. **Code example fixes**: Correct method names and parameters
5. **Link repairs**: Fix broken relative paths
6. **API documentation**: Add missing `query_ohlcv()` section

## Consequences

### Positive

- Documentation accuracy matches v13+ codebase
- Code examples executable without modification
- Proper syntax highlighting in all code blocks
- Architecture documentation reflects ADR-0034 optimizations

### Negative

- Large changeset (~900 line changes across ~48 files)
- ADRs retain historical package references (intentional for context)

## Compliance

- **Correctness**: Automated grep validation post-implementation
- **Maintainability**: Single commit per logical change category
- **Observability**: Plan task list tracks progress

## References

- [ADR-0011](0011-pypi-package-fork-clickhouse.md): PyPI package fork
- [ADR-0012](0012-documentation-accuracy-remediation.md): Cache path preservation
- [ADR-0034](0034-schema-optimization-prop-trading.md): Schema optimization
- [Plan-0042](../../development/plan/0042-documentation-rectification/plan.md): Implementation plan
