# Plan 0039: Validation System Redundancy Cleanup

**ADR**: [ADR-0039](../../../architecture/decisions/0039-validation-redundancy-cleanup.md)

**Status**: Complete

**Author**: Claude Code

**Last Updated**: 2025-11-25

---

## Overview

Remove redundant validation components discovered after ADR-0038 implementation. Consolidate production validation to single Earthly-based job.

### Goals

1. Remove redundant `binance-cdn-availability` job (superset exists)
2. Delete dead code (`e2e_core.py`, `validate_binance_cdn.py`)
3. Remove deprecated Earthfile target
4. Update stale documentation

### Non-Goals

- Adding new validation functionality
- Performance optimization
- Changing validation coverage

---

## Context

### Problem

Investigation of failed workflow #19679775010 revealed:

| Component | Issue | Impact |
|-----------|-------|--------|
| `binance-cdn-availability` job | Redundant with Stage 1 of real data validation | Extra job runs unnecessarily |
| `validate_binance_cdn.py` | Unused after job removal | Dead code |
| `e2e_core.py` | Never imported by any script | Dead code |
| `release-validation-pipeline` target | Deprecated, never called | Confusion |
| CLAUDE.md | References deleted scripts | Misleading docs |

### Root Cause of Failed Workflow

- `DOPPLER_TOKEN` GitHub secret was deleted before ADR-0038 merge
- Old workflow (v12.0.12) required DOPPLER_TOKEN
- New workflow (v13.0.0) uses direct GitHub secrets
- **Self-healed**: Manual trigger of v13.0.0 workflow succeeded

---

## Task List

| # | Task | Status | Notes |
|---|------|--------|-------|
| 1 | Verify v13.0.0 workflow works | ✅ Done | Manual trigger succeeded |
| 2 | Create ADR-0039 and plan | ✅ Done | This document |
| 3 | Remove `binance-cdn-availability` job | ✅ Done | production-validation.yml |
| 4 | Delete `validate_binance_cdn.py` | ✅ Done | scripts/ |
| 5 | Delete `e2e_core.py` | ✅ Done | src/.../validation/ |
| 6 | Delete deprecated Earthfile target | ✅ Done | Earthfile |
| 7 | Update CLAUDE.md | ✅ Done | Fix stale references |
| 8 | Update ADR-0038 and ADR-0035 | ✅ Done | Mark status |
| 9 | Commit and push | ⏳ Pending | refactor commit |

---

## Files Changed

### Delete

- `scripts/validate_binance_cdn.py`
- `src/gapless_crypto_clickhouse/validation/e2e_core.py`

### Modify

- `.github/workflows/production-validation.yml` - Remove `binance-cdn-availability` job
- `Earthfile` - Remove `release-validation-pipeline` target
- `CLAUDE.md` - Update CI/CD section
- `docs/architecture/decisions/0038-real-binance-data-validation.md` - Mark complete
- `docs/architecture/decisions/0035-cicd-production-validation.md` - Mark superseded

---

## Success Criteria

| Criterion | Metric |
|-----------|--------|
| Single job workflow | `production-validation.yml` has 1 job |
| No dead code | `validate_binance_cdn.py` and `e2e_core.py` deleted |
| No deprecated targets | `release-validation-pipeline` removed from Earthfile |
| Documentation current | CLAUDE.md matches implementation |
| Workflow passes | Next scheduled/triggered run succeeds |
