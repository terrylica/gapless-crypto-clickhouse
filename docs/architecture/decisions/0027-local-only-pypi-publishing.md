# ADR-0027: Local-Only PyPI Publishing Enforcement

**Status**: Accepted

**Date**: 2025-11-22

**ADR ID**: 0027

**Related Plans**: [`docs/development/plan/0027-local-only-pypi-publishing/plan.md`](/Users/terryli/eon/gapless-crypto-clickhouse/docs/development/plan/0027-local-only-pypi-publishing/plan.md)

## Context

Following ADR-0026 (ClickHouse Cloud Data Pipeline), v7.0.0 was successfully released using a hybrid workflow: GitHub Actions for versioning + local PyPI publishing. Analysis of the semantic-release configuration revealed potential vulnerabilities:

**Critical Finding**: `.releaserc.json` contains `publishCmd` that attempts PyPI publishing during GitHub Actions execution. Currently fails due to missing Doppler credentials in CI, but would succeed if credentials were added to repository secrets.

**Workspace-Wide Requirement**: User requires **all repositories** in `~/` to enforce local-only PyPI publishing. No workspace should ever use CI/CD pipelines for PyPI publishing.

**Design Goals**:
- Guarantee PyPI publishing happens ONLY on local machines
- Use `pypi-doppler` skill for credential management
- Preserve GitHub Actions for versioning automation (tags, releases, changelogs)
- Apply cleanest configuration possible (minimal complexity)

**Current Vulnerability**:
- `publishCmd` exists in `.releaserc.json` with Doppler token retrieval
- `prepareCmd` includes `uv build` (unnecessary in CI, creates attack surface)
- No safeguards in `scripts/publish-to-pypi.sh` against CI execution
- Documentation doesn't explain local-only architecture

## Decision

Enforce **local-only PyPI publishing** through configuration simplification and defense-in-depth safeguards:

### 1. Remove Publishing Logic from CI Configuration

**Intent**: Eliminate all PyPI publishing capability from GitHub Actions

**Abstractions**:
- Delete `publishCmd` from `@semantic-release/exec` plugin (cleanest approach)
- Remove `uv build` from `prepareCmd` (versioning-only workflow)
- No publishing credentials in GitHub secrets (zero-trust model)

**Files**:
- `.releaserc.json` (semantic-release configuration)

### 2. Add CI Detection Guards to Publishing Script

**Intent**: Block accidental CI execution with explicit error messages

**Abstractions**:
- Environment variable detection (CI, GITHUB_ACTIONS, GITLAB_CI, etc.)
- Repository verification (prevent fork abuse)
- Clear error messages explaining architecture

**Files**:
- `scripts/publish-to-pypi.sh` (local publishing script)

### 3. Document Local-Only Architecture

**Intent**: Prevent future misconfiguration through clear documentation

**Abstractions**:
- Workspace-wide policy statement
- Architecture rationale (security, speed, control)
- Complete workflow documentation

**Files**:
- `docs/development/PUBLISHING.md` (comprehensive publishing guide)
- `CLAUDE.md` (project memory for AI assistants)
- `.github/workflows/release.yml` (inline comment)

## Consequences

### Positive

- ✅ **Guaranteed local-only publishing**: No configuration exists for CI publishing
- ✅ **Fastest CI runs**: 20-30s faster (no building, no publishing attempts)
- ✅ **Cleanest configuration**: Minimal complexity, clear intent
- ✅ **Defense-in-depth**: Multiple safeguards prevent accidental enablement
- ✅ **Workspace consistency**: Same pattern applies to all repositories
- ✅ **Clear documentation**: Future maintainers understand architecture

### Negative

- ⚠️ **Manual step required**: Developer must run `./scripts/publish-to-pypi.sh` after release
- ⚠️ **Two-step workflow**: GitHub release creation + local publishing (not atomic)

### Neutral

- Publishing time unchanged (~30 seconds local)
- Total workflow time unchanged (~90 seconds: 60s CI + 30s local)
- Doppler credential management unchanged

## Alternatives Considered

### Alternative 1: Keep publishCmd with CI Detection Logic

**Rejected**: Adds complexity to `.releaserc.json`. User requested "cleanest way" - removing publishCmd is cleaner than adding conditional logic.

### Alternative 2: Use GitHub Environments with Manual Approval

**Rejected**: Still uses CI/CD for publishing. User explicitly stated "None of my workspace should be used CI/CD pipeline to publish ever again."

### Alternative 3: PyPI OIDC Trusted Publishing

**Rejected**: Requires GitHub Actions to publish. Conflicts with workspace-wide local-only policy.

### Alternative 4: Separate Workflow File for Publishing

**Rejected**: Doesn't prevent enablement. User wants guarantee against CI publishing, not just default-disabled state.

## Implementation

See: [`docs/development/plan/0027-local-only-pypi-publishing/plan.md`](/Users/terryli/eon/gapless-crypto-clickhouse/docs/development/plan/0027-local-only-pypi-publishing/plan.md)

**ADR-Task Sync**: Plan contains (a) plan, (b) context, (c) task list maintained via TodoWrite tool

## Validation

- [ ] `publishCmd` removed from `.releaserc.json`
- [ ] `uv build` removed from `prepareCmd`
- [ ] CI detection guards added to `scripts/publish-to-pypi.sh`
- [ ] Repository verification added to publish script
- [ ] `PUBLISHING.md` updated with local-only architecture
- [ ] `CLAUDE.md` updated with workspace policy
- [ ] `release.yml` comment added
- [ ] Test GitHub Actions run completes successfully (no publish attempt)
- [ ] Test local publish script executes successfully
- [ ] Test CI detection blocks script execution (CI=true test)
- [ ] Conventional commit created
- [ ] Logged to `logs/0027-local-only-pypi-publishing-20251122_005327.log`

## References

- **ADR-0026**: ClickHouse Cloud data pipeline (hybrid workflow origin)
- **Sub-Agent Reports**: 5 parallel agents (GitHub Actions, Security, semantic-release, pypi-doppler, Solution Design)
- **semantic-release Skill**: [`~/.claude/skills/semantic-release/SKILL.md`](/Users/terryli/.claude/skills/semantic-release/SKILL.md)
- **pypi-doppler Skill**: Doppler-based local PyPI publishing (credential management)
- **User Clarification**: "None of my workspace should be used CI/CD pipeline to publish ever again"
