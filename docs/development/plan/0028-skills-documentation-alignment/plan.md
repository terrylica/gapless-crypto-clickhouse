# Plan: Skills and Documentation Alignment with Local-Only Publishing Policy

**ADR ID**: 0028
**Date**: 2025-11-22
**Status**: Completed
**Owner**: Terry Li
**Completion Date**: 2025-11-22
**Commit**: 08bf588

## Objective

Ensure **complete alignment** of all workspace skills and project documentation with the workspace-wide local-only PyPI publishing policy established in ADR-0027, preventing AI agents from reintroducing forbidden CI/CD publishing patterns.

## Background

### Context

**Investigation Phase** (2025-11-22):

Spawned 5 parallel sub-agents using DCTL (Dynamic Todo List Creation) pattern to investigate skills and documentation alignment after ADR-0027 implementation:

1. **Global User Skills Agent**: Found 6 PyPI-related skills, identified pypi-doppler as critically misaligned
2. **Project Skills Agent**: Verified all 4 project skills aligned (ClickHouse infrastructure only)
3. **pypi-doppler Deep Analysis Agent**: Scored idiomatic alignment at 4/10, identified forbidden patterns
4. **semantic-release Agent**: Verified perfect alignment (already promotes local-first)
5. **Documentation Audit Agent**: Performed 16 search patterns, found only COMMANDS.md with issues

**User Requirement** (explicit mandate):

> "None of my workspace should be used CI/CD pipeline to publish ever again. Everything must not be used GitHub Actions to publish to PyPI but to use my publishing skill identified by pypi-doppler skill"

### Goals

1. **Eliminate contradictory guidance** in pypi-doppler skill
2. **Remove obsolete OIDC documentation** that contradicts ADR-0027
3. **Update COMMANDS.md** to reference only ADR-0027 compliant workflow
4. **Achieve 10/10 consistency** across all skills and documentation
5. **Prevent future policy violations** by AI agents

### Non-Goals

- Creating new skills (pypi-doppler will be rewritten, not created from scratch)
- Updating semantic-release skill (already aligned)
- Modifying project skills (already aligned)
- Backward compatibility with pre-ADR-0027 workflows

## Plan

### Architecture

**Pattern**: Skills alignment + documentation cleanup

```bash
Workspace Skills (~/.claude/skills/)
├─ semantic-release/
│  └─ ✅ Already aligned (promotes local-first)
│
├─ pypi-doppler/  [TO BE REWRITTEN]
│  ├─ ❌ DELETE: Lines 158-174 (publishCmd configuration)
│  ├─ ❌ DELETE: Lines 221-237 (GitHub Actions workflow)
│  ├─ ✅ ADD: Workspace policy header
│  ├─ ✅ ADD: CI detection guard documentation
│  ├─ ✅ ADD: Reference to scripts/publish-to-pypi.sh
│  └─ ✅ ADD: ADR-0027 cross-references

Project Documentation (docs/)
├─ PYPI_PUBLISHING_CONFIGURATION.yaml  [TO BE DELETED]
│  └─ ❌ Obsolete OIDC configuration
│
├─ development/COMMANDS.md  [TO BE UPDATED]
│  ├─ ❌ DELETE: Lines 296-298 (phantom CI job)
│  ├─ ❌ DELETE: Lines 300-318 (non-existent publish.yml)
│  └─ ✅ REPLACE: Lines 333-346 (manual publishing → ADR-0027 workflow)
│
└─ development/PUBLISHING.md
   └─ ✅ Already perfect (canonical reference)
```

### Implementation Steps

#### Phase 1: Documentation Structure (ADR + Plan)

1. ✅ Create ADR-0028 (MADR format)
2. ✅ Create plan directory: `docs/development/plan/0028-skills-documentation-alignment/`
3. Create plan.md (this file, Google Design Doc format)
4. Initialize TodoWrite task list
5. Initialize log file: `logs/0028-skills-documentation-alignment-YYYYMMDD_HHMMSS.log`

#### Phase 2: pypi-doppler Skill Rewrite

6. Read current pypi-doppler skill (if exists, else create from scratch)
7. Add workspace policy header:

   ```markdown
   ## ⚠️ WORKSPACE-WIDE POLICY: LOCAL-ONLY PUBLISHING

   FORBIDDEN:

   - Publishing from GitHub Actions
   - Publishing from any CI/CD pipeline
   - `publishCmd` in semantic-release configuration

   REQUIRED:

   - Use `scripts/publish-to-pypi.sh` on local machine
   - CI detection guards prevent accidental CI execution
   - Manual approval before each release

   Rationale: Security (no tokens in CI), Speed (30s vs 3-5min), Control (manual gate)
   See: ADR-0027, docs/development/PUBLISHING.md
   ```

8. Remove semantic-release integration section (lines 158-174):
   - Delete `publishCmd` example
   - Delete `uv build` in prepareCmd example

9. Remove GitHub Actions integration section (lines 221-237):
   - Delete Doppler secrets-fetch-action workflow
   - Delete CI publishing steps

10. Add CI detection guard documentation:

    ```markdown
    ## CI Detection Enforcement

    The canonical publish script (`scripts/publish-to-pypi.sh`) includes CI detection guards:

    - Checks: `$CI`, `$GITHUB_ACTIONS`, `$GITLAB_CI`, `$JENKINS_URL`, `$CIRCLECI`
    - Behavior: Hard fail with error message if detected
    - Test: `CI=true ./scripts/publish-to-pypi.sh` (should fail)
    ```

11. Add canonical implementation reference:

    ````markdown
    ## Publishing Command (Local Machine Only)

    **CRITICAL**: This command must ONLY run on your local machine, NEVER in CI/CD.

    Use the canonical script with built-in CI detection:

    ```bash
    # After semantic-release creates GitHub release
    git pull origin main
    ./scripts/publish-to-pypi.sh
    ```
    ````

    ```

    ```

12. Add ADR-0027 cross-references:

    ```markdown
    ## Related Documentation

    - **ADR-0027**: Local-only PyPI publishing decision
    - **PUBLISHING.md**: Complete release workflow
    - **semantic-release Skill**: Versioning automation (NO publishing)
    - **Canonical Script**: `scripts/publish-to-pypi.sh` (with CI guards)
    ```

#### Phase 3: Delete Obsolete Configuration

13. Delete `docs/PYPI_PUBLISHING_CONFIGURATION.yaml`:
    - File describes OIDC Trusted Publishing (superseded by ADR-0027)
    - References wrong repository name
    - References non-existent workflow

#### Phase 4: Update COMMANDS.md

14. Delete lines 296-298 (Job 7: Publish):
    - CI pipeline does NOT publish to PyPI under ADR-0027

15. Delete lines 300-318 (Continuous Deployment section):
    - Describes non-existent `publish.yml` workflow
    - Old OIDC Trusted Publishing workflow

16. Replace lines 333-346 (Manual PyPI Publishing):

    ````markdown
    ### PyPI Publishing

    **Canonical Guide**: See [PUBLISHING.md] for complete workflow.

    **Quick Reference** (Local-Only Publishing):

    ```bash
    # After GitHub Actions completes versioning
    git pull origin main

    # Publish using Doppler-managed credentials
    ./scripts/publish-to-pypi.sh
    ```
    ````

    **Key Points**:
    - ✅ Uses Doppler for credential management (no plaintext tokens)
    - ✅ CI detection guards prevent accidental CI publishing
    - ✅ Repository verification prevents fork abuse
    - ✅ ~30 seconds locally vs 3-5 minutes in CI

    **Why Local-Only?** See ADR-0027 for architectural decision.

    ```

    ```

#### Phase 5: Validation

17. Validate all cross-references resolve correctly:
    - ADR-0027 links
    - PUBLISHING.md links
    - scripts/publish-to-pypi.sh references

18. Verify no remaining OIDC/CI-CD publishing references:
    - Search for "OIDC", "trusted publishing", "publish.yml"
    - Confirm only ADR-0027 compliant mentions remain

19. Check internal consistency score improvement:
    - Before: 6/10
    - After: 10/10

#### Phase 6: Commit

20. Create conventional commit:

    ```
    docs(publish): align all skills and docs with ADR-0027 local-only policy

    Complete workspace-wide alignment with local-only PyPI publishing:

    SKILLS:
    - REWRITE pypi-doppler: Remove ALL CI/CD examples, add workspace policy
    - DELETE forbidden patterns (publishCmd, GitHub Actions workflows)
    - ADD CI detection guard documentation
    - ADD ADR-0027 cross-references

    DOCUMENTATION:
    - DELETE PYPI_PUBLISHING_CONFIGURATION.yaml (obsolete OIDC config)
    - UPDATE COMMANDS.md: Remove phantom CI/CD workflows
    - REPLACE manual publishing section with canonical workflow

    VERIFICATION:
    - Full audit: 16 search patterns, only COMMANDS.md found
    - semantic-release skill already aligned
    - All project skills aligned (infrastructure only)

    This ensures AI agents and future maintainers cannot reintroduce
    forbidden CI/CD publishing patterns.

    Refs: ADR-0028, ADR-0027
    ```

21. Update plan.md with completion status

### Success Criteria

- [ ] pypi-doppler skill has NO CI/CD publishing examples
- [ ] pypi-doppler skill has workspace policy header
- [ ] pypi-doppler skill references `scripts/publish-to-pypi.sh` as canonical
- [ ] pypi-doppler skill documents CI detection guards
- [ ] pypi-doppler skill has ADR-0027 cross-references
- [ ] PYPI_PUBLISHING_CONFIGURATION.yaml deleted
- [ ] COMMANDS.md Job 7 deleted (lines 296-298)
- [ ] COMMANDS.md Continuous Deployment section deleted (lines 300-318)
- [ ] COMMANDS.md Manual Publishing section replaced with ADR-0027 workflow
- [ ] All cross-references resolve correctly
- [ ] No OIDC/CI-CD publishing references (except migration history in ADR-0027)
- [ ] Internal consistency score: 10/10
- [ ] pypi-doppler idiomatic alignment: 9-10/10

## Context

### Source Material

**Sub-Agent Reports** (5 parallel DCTL agents):

1. **Global User Skills Agent**:
   - Found 6 PyPI-related skills
   - semantic-release: Perfect alignment (local-first philosophy)
   - pypi-doppler: Critical misalignment (4/10 score)
   - Other 4 skills: Neutral or aligned

2. **Project Skills Agent**:
   - All 4 skills ClickHouse infrastructure-focused
   - Zero PyPI/publishing mentions
   - Perfect alignment by scope separation

3. **pypi-doppler Deep Analysis Agent**:
   - Idiomatic alignment: 4/10
   - Shows forbidden `publishCmd` configuration
   - Provides GitHub Actions publishing workflow
   - Zero enforcement mechanisms
   - Credential management: Excellent (8/10)

4. **semantic-release Agent**:
   - Already perfectly aligned
   - Promotes local-first, GitHub Actions as "optional backup only"
   - Production-validated with gapless-crypto-clickhouse

5. **Documentation Audit Agent**:
   - 16 comprehensive search patterns
   - Only COMMANDS.md found with issues
   - CLAUDE.md and PUBLISHING.md exemplary

**User Requirements** (from investigation loop):

1. **Complete rewrite of pypi-doppler**: Remove ALL CI/CD examples, add workspace policy header
2. **Delete PYPI_PUBLISHING_CONFIGURATION.yaml**: File is completely obsolete
3. **Replace COMMANDS.md sections**: With ADR-0027 workflow
4. **Full documentation audit**: Ensure no hidden OIDC/CI-CD references

### Critical Findings

**pypi-doppler Skill Misalignment** (Lines 158-174, 221-237):

```yaml
# FORBIDDEN PATTERN (to be removed)
plugins:
  - - "@semantic-release/exec"
    - prepareCmd: |
        uv build  # ❌ ADR-0027 removed this from CI
      publishCmd: | # ❌ ADR-0027 deleted this entirely
        UV_PUBLISH_TOKEN=$(doppler secrets get PYPI_TOKEN ...) uv publish
```

**Evidence of Contradiction**:

- ADR-0027 decision: "Delete `publishCmd` from `.releaserc.json` (cleanest approach)"
- pypi-doppler shows: Exact `publishCmd` configuration ADR-0027 forbids
- ADR-0027 decision: "Remove `uv build` from `prepareCmd`"
- pypi-doppler shows: `uv build` in prepareCmd

**PYPI_PUBLISHING_CONFIGURATION.yaml Issues**:

- Version 2.6.0 (2025-09-18) - before ADR-0027 (2025-11-22)
- Describes OIDC Trusted Publishing (superseded)
- References `gapless-crypto-data` (wrong repository)
- References `publish.yml` (workflow doesn't exist)

**COMMANDS.md Issues**:

- Lines 296-298: Describes phantom CI publishing job
- Lines 300-318: Describes non-existent `publish.yml` workflow
- Lines 333-346: Shows incomplete manual publishing (missing Doppler, CI guards, canonical script)

### Related Work

- **ADR-0027**: Local-Only PyPI Publishing Enforcement (parent decision)
- **ADR-0026**: ClickHouse Cloud Data Pipeline (hybrid workflow origin)
- **semantic-release Skill**: `~/.claude/skills/semantic-release/SKILL.md` (already aligned)
- **PUBLISHING.md**: `docs/development/PUBLISHING.md` (v2.0.0, canonical workflow)

### Constraints

- **SLO focus**: Availability, correctness, observability, maintainability (not speed/perf/security)
- **No backward compatibility needed**: pypi-doppler skill not created yet
- **Auto-validate outputs**: After each change, verify consistency
- **Raise+propagate errors**: No fallback/default/retry/silent failures

## Task List

**Status**: 9/9 tasks complete (100%) ✅

**Completed**:

- [x] Create ADR-0028
- [x] Create plan directory and plan.md
- [x] Initialize log file
- [x] Create pypi-doppler skill with workspace policy (from scratch, ADR-0027 aligned)
- [x] Delete PYPI_PUBLISHING_CONFIGURATION.yaml
- [x] Update COMMANDS.md with ADR-0027 workflow
- [x] Validate all cross-references
- [x] Create conventional commit (08bf588)
- [x] Update plan.md with completion status

**Final Commit**: 08bf588
**Total Changes**: 4 files changed, 656 insertions(+), 120 deletions(-)
**Files Modified**:

- Created: `docs/architecture/decisions/0028-skills-documentation-alignment.md`
- Created: `docs/development/plan/0028-skills-documentation-alignment/plan.md`
- Created: `~/.claude/skills/pypi-doppler/SKILL.md` (workspace skill, not in git)
- Deleted: `docs/PYPI_PUBLISHING_CONFIGURATION.yaml`
- Updated: `docs/development/COMMANDS.md`

## Risks and Mitigations

| Risk                                       | Impact | Mitigation                                                 |
| ------------------------------------------ | ------ | ---------------------------------------------------------- |
| pypi-doppler skill doesn't exist yet       | Low    | Create from scratch with ADR-0027 alignment from start     |
| AI agents might reference old examples     | High   | Complete rewrite removes all forbidden patterns            |
| Future maintainers might add CI publishing | High   | Workspace policy header + ADR-0027 references prevent this |
| Documentation becomes stale                | Medium | Add date + ADR reference to each section                   |
| Cross-reference links break                | Low    | Validate all links before committing                       |

## Timeline

**Start**: 2025-11-22
**Estimated Duration**: 45 minutes
**Log file**: `logs/0028-skills-documentation-alignment-YYYYMMDD_HHMMSS.log`

**Progress logging**: Status updates every 15-60s for operations >1min

## References

- **ADR-0028**: `docs/architecture/decisions/0028-skills-documentation-alignment.md`
- **ADR-0027**: `docs/architecture/decisions/0027-local-only-pypi-publishing.md`
- **PUBLISHING.md**: `docs/development/PUBLISHING.md` (v2.0.0)
- **Canonical Script**: `scripts/publish-to-pypi.sh`
- **semantic-release Skill**: `~/.claude/skills/semantic-release/SKILL.md`
- **Sub-Agent Reports**: Ephemeral (in-memory during investigation)
