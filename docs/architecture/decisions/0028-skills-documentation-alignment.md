# ADR-0028: Skills and Documentation Alignment with Local-Only Publishing Policy

**Date**: 2025-11-22
**Status**: Accepted
**Deciders**: Terry Li
**Supersedes**: None
**Superseded By**: None

## Context and Problem Statement

After implementing ADR-0027 (local-only PyPI publishing enforcement), a comprehensive audit revealed **critical misalignment** between workspace skills and project documentation with the newly established workspace-wide policy. Three files actively contradict or undermine the local-only publishing requirement:

1. **`~/.claude/skills/pypi-doppler/`** - Shows forbidden `publishCmd` configuration and GitHub Actions publishing workflows
2. **`docs/PYPI_PUBLISHING_CONFIGURATION.yaml`** - Describes obsolete OIDC Trusted Publishing
3. **`docs/development/COMMANDS.md`** - References non-existent CI/CD workflows

**Problem**: AI assistants using these contradictory skills/docs could reintroduce the security vulnerabilities that ADR-0027 was written to prevent.

## Investigation Summary

**Multi-Agent Parallel Investigation** (DCTL methodology):
- 5 sub-agents investigated global skills, project skills, pypi-doppler, semantic-release, and full documentation
- **Global skills**: 5 of 6 aligned, 1 critical issue (pypi-doppler)
- **Project skills**: All 4 aligned (ClickHouse infrastructure only)
- **semantic-release skill**: Already perfectly aligned
- **Full documentation audit**: 16 search patterns, only COMMANDS.md found with issues

**Key Finding**: pypi-doppler skill (idiomatic alignment score: 4/10) actively promotes patterns forbidden by ADR-0027.

## Decision Drivers

### Workspace-Wide Requirement

**User Mandate**: "None of my workspace should be used CI/CD pipeline to publish ever again. Everything must not be used GitHub Actions to publish to PyPI but to use my publishing skill identified by pypi-doppler skill"

### Prevent Policy Violations

AI agents following contradictory guidance could:
- Recreate `publishCmd` in `.releaserc.json` (ADR-0027 explicitly deleted this)
- Add Doppler credentials to GitHub secrets
- Bypass CI detection guards
- Reintroduce attack surface (building in CI)

### Maintain Single Source of Truth

**Canonical Documentation**:
- Policy: ADR-0027
- Workflow: `docs/development/PUBLISHING.md`
- Implementation: `scripts/publish-to-pypi.sh`

All other documentation must align with these sources.

## Considered Options

### Option 1: Complete Rewrite of pypi-doppler Skill (SELECTED)

**Approach**:
- Remove ALL CI/CD publishing examples
- Add workspace policy header with FORBIDDEN patterns
- Reference canonical implementation (`scripts/publish-to-pypi.sh`)
- Document CI detection guards
- Add ADR-0027 cross-references

**Pros**:
- ✅ Prevents AI agents from reintroducing forbidden patterns
- ✅ Clear single source of truth
- ✅ Idiomatic alignment improves to 9-10/10
- ✅ Enforces workspace-wide policy

**Cons**:
- Requires significant rewrite (~150 lines)
- Removes "advanced" CI/CD options

### Option 2: Soft Update with Warnings

**Approach**:
- Keep CI/CD examples but add "⚠️ WORKSPACE POLICY VIOLATION" warnings
- Less disruptive

**Pros**:
- Faster to implement

**Cons**:
- ❌ Users might skip warnings
- ❌ Still shows forbidden patterns
- ❌ Contradictory information remains

**Rejected**: Insufficient enforcement

### Option 3: Archive and Replace

**Approach**:
- Move to `pypi-doppler-deprecated/`
- Create new `pypi-local-publishing` skill

**Pros**:
- Preserves history

**Cons**:
- ❌ Requires updating all references
- ❌ Adds complexity
- ❌ More files to maintain

**Rejected**: Over-engineered

## Decision Outcome

**Chosen option**: Complete rewrite of pypi-doppler skill + delete obsolete docs + update COMMANDS.md

### Implementation

#### 1. Rewrite pypi-doppler Skill

**Location**: `~/.claude/skills/pypi-doppler/SKILL.md`

**Changes**:
- Add workspace policy statement at top
- Delete semantic-release integration section (lines 158-174 showing `publishCmd`)
- Delete GitHub Actions integration section (lines 221-237)
- Add CI detection guard documentation
- Reference `scripts/publish-to-pypi.sh` as canonical implementation
- Add ADR-0027 cross-references
- Update description to emphasize LOCAL-ONLY constraint

**New Sections**:
```markdown
## ⚠️ WORKSPACE-WIDE POLICY: LOCAL-ONLY PUBLISHING

FORBIDDEN:
- Publishing from GitHub Actions
- Publishing from any CI/CD pipeline
- `publishCmd` in semantic-release configuration

REQUIRED:
- Use `scripts/publish-to-pypi.sh` on local machine
- CI detection guards in publish script
- Manual approval before each release

Rationale: Security, Speed, Control (see ADR-0027)
```

#### 2. Delete Obsolete Configuration

**File**: `docs/PYPI_PUBLISHING_CONFIGURATION.yaml`

**Action**: Delete entirely

**Rationale**:
- Describes OIDC Trusted Publishing (superseded by ADR-0027 on 2025-11-22)
- References wrong repository (`gapless-crypto-data` vs `gapless-crypto-clickhouse`)
- References non-existent workflow (`publish.yml`)
- Canonical configuration now in `docs/development/PUBLISHING.md`

#### 3. Update COMMANDS.md

**File**: `docs/development/COMMANDS.md`

**Changes**:
- Delete lines 296-298 (Job 7: Publish to PyPI - phantom job)
- Delete lines 300-318 (Continuous Deployment section - non-existent workflow)
- Replace lines 333-346 (Manual Publishing) with ADR-0027 compliant workflow

**New Content**:
- Reference to `PUBLISHING.md` for complete workflow
- Quick reference to `./scripts/publish-to-pypi.sh`
- Key points: Doppler credentials, CI guards, local-only policy
- ADR-0027 rationale summary

### Safety Mechanisms

**Defense-in-Depth** (extends ADR-0027's 4 layers):

| Layer | ADR-0027 Implementation | ADR-0028 Extension |
|-------|------------------------|-------------------|
| **1. Configuration Prevention** | No `publishCmd` in `.releaserc.json` | pypi-doppler shows no `publishCmd` examples |
| **2. Script Guards** | CI detection in `publish-to-pypi.sh` | pypi-doppler documents CI guards |
| **3. Repository Verification** | Prevent fork abuse | pypi-doppler references canonical script |
| **4. Documentation** | PUBLISHING.md | COMMANDS.md aligned |
| **5. Skills Alignment** | (New) | pypi-doppler enforces workspace policy |

### Validation

**Consistency Verification**:
- All ADR-0027 references resolve correctly
- No remaining OIDC/CI-CD publishing references (16 search patterns validated)
- semantic-release skill already aligned (no changes needed)
- All project skills aligned (infrastructure only, no publishing concerns)

**Expected Outcome**:
- Internal consistency score: 6/10 → 10/10
- pypi-doppler idiomatic alignment: 4/10 → 9-10/10
- Files modified: 3 (skill + 2 docs)

## Consequences

### Positive

✅ **Prevents Policy Violations**: AI agents cannot follow contradictory guidance
✅ **Single Source of Truth**: All documentation points to ADR-0027 and PUBLISHING.md
✅ **Idiomatic Alignment**: pypi-doppler skill becomes exemplary local-only implementation
✅ **Workspace Consistency**: Global skills align with project documentation
✅ **Future-Proof**: Clear policy prevents maintainers from re-adding CI/CD publishing

### Neutral

⚙️ **Removes Advanced Options**: No more "advanced" CI/CD publishing examples in pypi-doppler
⚙️ **Documentation Cleanup**: Deletes historical OIDC configuration (migration history preserved in ADR-0027)

### Negative

❌ **Skill Rewrite Effort**: ~150 lines changed in pypi-doppler skill
❌ **No Backward Compatibility**: Skills written before ADR-0028 might reference old examples

**Mitigation**: The skill hasn't been created yet (only referenced in CLAUDE.md), so there's no backward compatibility concern.

## Related Decisions

- **ADR-0027**: Local-Only PyPI Publishing Enforcement (parent decision)
- **ADR-0026**: ClickHouse Cloud Data Pipeline (origin of hybrid workflow)

## References

- **Investigation Reports**: 5 parallel sub-agent reports (DCTL methodology)
- **Canonical Documentation**:
  - `docs/development/PUBLISHING.md` (v2.0.0)
  - `scripts/publish-to-pypi.sh` (with CI guards)
  - `.releaserc.json` (no publishCmd)
- **Workspace Skills**:
  - `~/.claude/skills/semantic-release/` (already aligned)
  - `~/.claude/skills/pypi-doppler/` (to be rewritten)

---

**Last Updated**: 2025-11-22
**Implementation**: ADR-0028 plan in `docs/development/plan/0028-skills-documentation-alignment/plan.md`
