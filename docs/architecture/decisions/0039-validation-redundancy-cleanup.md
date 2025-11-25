# ADR-0039: Validation System Redundancy Cleanup

**Status**: Accepted

**Date**: 2025-11-25

**Supersedes**: None

**Related**: ADR-0035, ADR-0037, ADR-0038

---

## Context

After implementing ADR-0038 (Real Binance Data Validation), the validation system contains redundant components:

1. **Dual CDN validation** - `binance-cdn-availability` job does HTTP HEAD while `binance-real-data-validation` job downloads from CDN (superset)
2. **Dead code** - `e2e_core.py` module created per ADR-0036 but never imported
3. **Deprecated Earthfile target** - `release-validation-pipeline` marked deprecated but not removed
4. **Stale documentation** - CLAUDE.md references deleted scripts

Investigation triggered by failed workflow run #19679775010 (root cause: `DOPPLER_TOKEN` deleted before ADR-0038 merge, self-healed in v13.0.0).

## Decision

Remove redundant validation components:

1. **Delete `binance-cdn-availability` job** from `production-validation.yml`
   - Stage 1 of `binance-real-data-validation` already downloads from CDN
   - Redundant HTTP HEAD check provides no additional value

2. **Delete `scripts/validate_binance_cdn.py`**
   - No longer used after job removal

3. **Delete `src/gapless_crypto_clickhouse/validation/e2e_core.py`**
   - Dead code (grep shows zero imports)

4. **Delete `release-validation-pipeline` Earthfile target**
   - Deprecated, GitHub Actions calls individual targets directly

5. **Keep `+production-health-check`** in release validation
   - Fast 1s quick-fail detection before 30s full validation
   - Defense-in-depth for connection issues

6. **Update documentation**
   - CLAUDE.md: Remove stale references to deleted scripts
   - ADR-0038: Mark validation checkboxes complete
   - ADR-0035: Add superseded note

## Consequences

### Positive

- Single-job production validation workflow (simpler)
- No dead code in codebase
- Documentation matches implementation
- Reduced confusion for future maintainers

### Negative

- Slightly less granular failure reporting (CDN vs full validation)

### Neutral

- No impact on validation coverage (real data validation includes CDN download)

## Validation

- [x] Production validation workflow succeeds with single job
- [x] No imports of deleted modules
- [x] CLAUDE.md references current scripts
- [x] ADR status reflects implementation state
