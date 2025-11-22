# Plan: Local-Only PyPI Publishing Enforcement

**ADR ID**: 0027
**Date**: 2025-11-22
**Status**: In Progress
**Owner**: Terry Li

## Objective

Guarantee PyPI publishing happens **ONLY** on local machines via `pypi-doppler` skill, **NEVER** through GitHub Actions CI/CD, using the cleanest configuration approach.

## Background

### Context

**Investigation Phase** (2025-11-22 00:53 UTC):

Spawned 5 parallel sub-agents using DCTL (Dynamic Todo List Creation) pattern to investigate local-only publishing enforcement:

1. **GitHub Actions Agent**: Discovered `publishCmd` in `.releaserc.json` attempts PyPI publishing during CI (currently fails due to missing Doppler credentials)
2. **Security Agent**: Research industry best practices for preventing CI/CD publishing
3. **semantic-release Agent**: Analyzed plugin execution flow and configuration options
4. **pypi-doppler Agent**: Validated local publishing workflow already operational
5. **Solution Design Agent**: Designed 5-layer defense-in-depth approach

**User Clarifications** (iterative loop):

- **Workspace-Wide Policy**: "None of my workspace should be used CI/CD pipeline to publish ever again"
- **Cleanest Approach**: Remove `publishCmd` entirely (not conditional logic)
- **Most Efficient**: Remove `uv build` from CI (`prepareCmd`), building happens locally
- **CI Guards**: Add error-based blocking in `scripts/publish-to-pypi.sh`
- **Documentation**: Comprehensive updates to prevent future misconfiguration

### Goals

1. **Eliminate CI publishing capability**: Remove all PyPI publishing logic from GitHub Actions
2. **Enforce local-only workflow**: Add CI detection guards to publishing script
3. **Document architecture**: Clear explanation of local-only publishing policy
4. **Preserve existing workflows**: GitHub Actions continues versioning automation
5. **Cleanest configuration**: Minimal complexity, clear intent

### Non-Goals

- GitHub Actions publishing with manual approval (still uses CI/CD)
- PyPI OIDC Trusted Publishing (requires GitHub Actions)
- Backward compatibility with old workflow (fresh start acceptable)

## Plan

### Architecture

**Pattern**: Configuration simplification + defense-in-depth safeguards

```
GitHub Actions (.github/workflows/release.yml)
├─ ✅ Analyze commits (conventional commits)
├─ ✅ Determine next version (semantic versioning)
├─ ✅ Update pyproject.toml, package.json versions
├─ ✅ Update CHANGELOG.md
├─ ✅ Create git tag (e.g., v7.0.1)
├─ ✅ Create GitHub release
├─ ✅ Commit version files back to repo [skip ci]
│
├─ ❌ DO NOT build package (REMOVED from prepareCmd)
└─ ❌ DO NOT publish to PyPI (publishCmd DELETED)

Local Machine (scripts/publish-to-pypi.sh)
├─ ✅ CI detection guards (NEW: blocks if CI=true)
├─ ✅ Repository verification (NEW: prevents fork abuse)
├─ ✅ Pull latest release commit
├─ ✅ Verify Doppler credentials
├─ ✅ Build package with uv build
├─ ✅ Publish to PyPI with uv publish
└─ ✅ Verify publication
```

**Workflow Preservation**: CI tests, E2E validation, benchmarks continue unchanged

### Implementation Steps

#### Phase 1: Documentation Structure (ADR + Plan)

1. ✅ Create ADR-0027 (MADR format)
2. ✅ Create plan directory: `docs/development/plan/0027-local-only-pypi-publishing/`
3. ✅ Create plan.md (this file, Google Design Doc format)
4. ✅ Initialize TodoWrite task list
5. ✅ Initialize log file: `logs/0027-local-only-pypi-publishing-20251122_005327.log`

#### Phase 2: Configuration Simplification

6. Remove `publishCmd` from `.releaserc.json`:
   - Delete lines 97-98: `"publishCmd": "UV_PUBLISH_TOKEN..."`
   - Add `_comment` field explaining local-only publishing

7. Remove `uv build` from `prepareCmd`:
   - Line 96: Remove `&& uv build` from command chain
   - Versions update only, building happens locally

#### Phase 3: Script Safeguards

8. Add CI detection guards to `scripts/publish-to-pypi.sh`:
   - After line 6 (`set -e`)
   - Check for CI environment variables (CI, GITHUB_ACTIONS, GITLAB_CI, JENKINS_URL, CIRCLECI)
   - Exit with error if CI detected

9. Add repository verification:
   - After CI guards
   - Check GITHUB_REPOSITORY matches expected value
   - Prevent fork abuse

#### Phase 4: Documentation Updates

10. Update `docs/development/PUBLISHING.md`:
    - Add critical warning banner at top
    - Add "Why Local-Only Publishing?" section
    - Add "Complete Release Workflow" section
    - Add "Safety Mechanisms" section
    - Update troubleshooting

11. Update `CLAUDE.md`:
    - Add "PyPI Publishing Architecture" section
    - Document workspace-wide policy
    - Reference PUBLISHING.md

12. Add comment to `.github/workflows/release.yml`:
    - After `semantic-release` step
    - Explain no PyPI publishing happens in CI

#### Phase 5: Validation

13. Test GitHub Actions workflow:
    ```bash
    # Push a test commit, verify GitHub release created
    # Check workflow logs for no publishing attempt
    ```

14. Test local publishing script:
    ```bash
    ./scripts/publish-to-pypi.sh
    # Verify executes successfully
    ```

15. Test CI detection:
    ```bash
    CI=true ./scripts/publish-to-pypi.sh
    # Verify blocks with error message
    ```

16. Verify existing workflows unchanged:
    ```bash
    # CI tests, E2E validation should continue working
    ```

#### Phase 6: Commit

17. Create conventional commit:
    ```
    feat(publish): enforce local-only PyPI publishing workspace-wide

    Remove all CI/CD publishing capability to guarantee local-only workflow:
    - DELETE publishCmd from .releaserc.json (cleanest configuration)
    - REMOVE uv build from prepareCmd (versioning-only in CI)
    - ADD CI detection guards to scripts/publish-to-pypi.sh
    - ADD repository verification (prevent fork abuse)
    - UPDATE PUBLISHING.md with local-only architecture
    - UPDATE CLAUDE.md with workspace policy
    - ADD release.yml comment explaining no CI publishing

    This enforces workspace-wide policy: NO CI/CD for PyPI publishing.
    All repos use pypi-doppler skill for local publishing only.

    Benefits:
    - Guaranteed local-only (no config for CI publishing exists)
    - 20-30s faster CI (no building/publishing)
    - Cleanest config (minimal complexity)
    - Defense-in-depth (multiple safeguards)

    Refs: ADR-0027
    ```

18. Log completion to `logs/0027-local-only-pypi-publishing-20251122_005327.log`

### Success Criteria

- [ ] `publishCmd` removed from `.releaserc.json`
- [ ] `uv build` removed from `prepareCmd`
- [ ] CI detection guards added to `scripts/publish-to-pypi.sh`
- [ ] Repository verification added to publish script
- [ ] `PUBLISHING.md` updated with comprehensive documentation
- [ ] `CLAUDE.md` updated with workspace policy
- [ ] `release.yml` comment added
- [ ] GitHub Actions test run completes (no publish attempt)
- [ ] Local publish script test succeeds
- [ ] CI detection test blocks execution
- [ ] Conventional commit created
- [ ] Logged to `logs/0027-local-only-pypi-publishing-20251122_005327.log`

## Context

### Source Material

**Sub-Agent Reports** (5 parallel DCTL agents):

- **GitHub Actions Agent**: Mapped complete publishing flow, found `publishCmd` vulnerability
- **Security Agent**: Researched PyPI security best practices, environment protection, Trusted Publishing
- **semantic-release Agent**: Analyzed plugin execution order, dry-run behavior, CI detection
- **pypi-doppler Agent**: Confirmed local workflow operational, Doppler integration validated
- **Solution Design Agent**: Designed 5-layer defense strategy, validated edge cases

**User Requirements** (from clarification loop):

1. **Workspace-wide policy**: No CI/CD for PyPI publishing in any repository
2. **Cleanest approach**: Remove `publishCmd` entirely (not conditional logic)
3. **Most efficient**: Remove building from CI (happens locally only)
4. **CI guards**: Error-based blocking in publish script
5. **Comprehensive documentation**: Prevent future misconfiguration

### Existing Configuration

**Current `.releaserc.json`**:
- Line 96: `prepareCmd` includes `&& uv build` (unnecessary in CI)
- Line 97: `publishCmd` attempts PyPI publishing with Doppler (vulnerability)

**Current `scripts/publish-to-pypi.sh`**:
- No CI detection guards
- No repository verification
- Works locally but could be triggered in CI

**Current Documentation**:
- `PUBLISHING.md` describes old OIDC workflow (outdated)
- No mention of local-only policy

### Related Work

- **ADR-0026**: ClickHouse Cloud data pipeline (hybrid workflow origin)
- **semantic-release Skill**: [`~/.claude/skills/semantic-release/SKILL.md`](/Users/terryli/.claude/skills/semantic-release/SKILL.md)
- **pypi-doppler Skill**: Local PyPI publishing with Doppler credential management

### Constraints

- **SLO focus**: Availability, correctness, observability, maintainability (not speed/perf/security)
- **No backward compatibility needed**: Fresh start acceptable
- **Auto-validate outputs**: After each change, verify still works
- **Raise+propagate errors**: No fallback/default/retry/silent failures

## Task List

**Status**: 5/18 tasks complete (28%)

**Completed**:

- [x] Create ADR-0027
- [x] Create plan directory and plan.md
- [x] Initialize TodoWrite task list
- [x] Initialize log file
- [x] **In Progress** → Remove publishCmd from .releaserc.json

**Pending**:

- [ ] Remove uv build from prepareCmd
- [ ] Add CI detection guards to publish script
- [ ] Add repository verification to publish script
- [ ] Update PUBLISHING.md with local-only architecture
- [ ] Update CLAUDE.md with workspace policy
- [ ] Add comment to release.yml workflow
- [ ] Test GitHub Actions workflow
- [ ] Test local publishing script
- [ ] Test CI detection blocking
- [ ] Verify existing workflows unchanged
- [ ] Create conventional commit
- [ ] Log completion
- [ ] Update plan.md with completion status

**Sync with TodoWrite**: This task list mirrors TodoWrite tool state (12 todos tracked)

## Risks and Mitigations

| Risk                                          | Impact | Mitigation                                                    |
| --------------------------------------------- | ------ | ------------------------------------------------------------- |
| GitHub Actions fails after publishCmd removal | Medium | Test dry-run first, semantic-release handles missing publish |
| Local script fails with new CI guards         | Medium | Test with CI=true before committing                           |
| Documentation becomes stale                   | Low    | Add date + ADR reference to each doc section                  |
| Future maintainer re-adds publishCmd          | High   | Clear documentation + workspace policy in CLAUDE.md           |

## Timeline

**Start**: 2025-11-22 00:53 UTC
**Estimated Duration**: 30 minutes
**Log file**: `logs/0027-local-only-pypi-publishing-20251122_005327.log`

**Progress logging**: Status updates every 15-60s for operations >1min

## References

- **ADR-0027**: [`docs/architecture/decisions/0027-local-only-pypi-publishing.md`](/Users/terryli/eon/gapless-crypto-clickhouse/docs/architecture/decisions/0027-local-only-pypi-publishing.md)
- **Project Memory**: [`CLAUDE.md`](/Users/terryli/eon/gapless-crypto-clickhouse/CLAUDE.md)
- **semantic-release Skill**: [`~/.claude/skills/semantic-release/SKILL.md`](/Users/terryli/.claude/skills/semantic-release/SKILL.md)
- **Sub-Agent Reports**: Ephemeral (in-memory during planning)
