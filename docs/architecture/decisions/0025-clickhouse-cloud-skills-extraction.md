# ADR-0025: Extract ClickHouse Cloud Setup Workflows into Atomic Skills

**Status**: Accepted

**Date**: 2025-11-21

**ADR ID**: 0025

**Related Plans**: [`docs/development/plan/0025-clickhouse-cloud-skills/plan.md`](/Users/terryli/eon/gapless-crypto-clickhouse/docs/development/plan/0025-clickhouse-cloud-skills/plan.md)

## Context

During ClickHouse Cloud migration (2025-11-20), we established production workflows for:
- Fetching service details from ClickHouse Cloud API
- Storing credentials in Doppler + 1Password
- Testing connection to ClickHouse Cloud services

Source: `/tmp/clickhouse_setup_final_summary.md` (validated production setup, 100% successful)

These workflows are **prescriptive, stepwise, and task-like**—ideal candidates for codification as Claude Code skills using Link Farm + Hub-and-Spoke progressive disclosure pattern from project CLAUDE.md.

### Problem

Validated ClickHouse Cloud workflows exist only as ephemeral documentation (`/tmp/*.md`). Without codification:
- **Not repeatable**: Future service setup requires rediscovery
- **Not discoverable**: Claude cannot proactively suggest these workflows
- **Not maintainable**: No canonical source for updates

### User Requirements

1. **Multiple atomic skills** (not single comprehensive skill)
2. **Project-specific** (gapless-crypto-clickhouse context, not generic)
3. **Prescriptive setup workflow** (step-by-step NEW service onboarding)
4. **Credential store references** (Doppler/1Password key names, no secrets)
5. **Documentation only** (no scripts/, SKILL.md + references/ pattern)
6. **Project-local location** (`./skills/` in repo)
7. **Hub-and-Spoke CLAUDE.md update** (new ClickHouse Cloud Setup section)

Source: Iterative clarification loop (2025-11-21 12:35-12:38 PST)

## Decision

Create **3 project-local atomic skills** extracting validated workflows from production ClickHouse Cloud setup:

### Skill 1: `clickhouse-cloud-service-setup`
**Intent**: Automate service metadata discovery via ClickHouse Cloud API

**Abstractions**:
- Organization ID resolution (API → Doppler)
- Service endpoint extraction (HTTPS 8443 recommended, Native 9440 available)
- Configuration discovery (idle scaling, memory tier, IP access)

**When to use**: Initial service provisioning, service discovery, endpoint resolution

### Skill 2: `clickhouse-cloud-credentials`
**Intent**: Establish dual credential storage pattern (Doppler + 1Password)

**Abstractions**:
- Credential storage contract (8 Doppler secrets, 8 1Password fields)
- Project-specific paths (`aws-credentials/prd`, Engineering vault)
- Secret naming convention (`CLICKHOUSE_CLOUD_*`, `CLICKHOUSE_*`)

**When to use**: New service credential storage, credential rotation, backup verification

### Skill 3: `clickhouse-cloud-connection`
**Intent**: Validate ClickHouse Cloud connectivity and troubleshoot issues

**Abstractions**:
- clickhouse-connect client configuration (secure=True for Cloud)
- Doppler environment integration pattern
- Connection test queries (version, user, table count)

**When to use**: Connection validation, troubleshooting, environment verification

### Integration Pattern

**CLAUDE.md Update**: New "ClickHouse Cloud Setup" section after "Validated Workflows" (line 49)
- Link Farm: Absolute paths to 3 skills
- Progressive Disclosure: "When to use" + "Key principle"
- Follows existing pattern from semantic-release, multi-agent-* skills

## Consequences

### Positive

- ✅ **Repeatability**: Future ClickHouse Cloud services follow validated pattern
- ✅ **Discoverability**: Claude proactively suggests skills when user mentions "ClickHouse Cloud", "credentials", "connection test"
- ✅ **Maintainability**: Single source of truth in version control
- ✅ **Security**: No secrets in skills, only credential store references
- ✅ **Observability**: Skills explicitly document API endpoints, required secrets, test procedures

### Negative

- ⚠️ **Maintenance burden**: 3 skills require sync when ClickHouse Cloud API changes
- ⚠️ **Project coupling**: Skills are gapless-crypto-clickhouse-specific (intentional per requirements)

### Neutral

- Skills are documentation-only (no scripts/), Claude executes workflows
- Skills stored in project repo (`./skills/`), not global (`~/.claude/skills/`)

## Alternatives Considered

### Alternative 1: Single comprehensive skill
**Rejected**: User explicitly requested "multiple atomic skills" for modularity

### Alternative 2: Generic ClickHouse Cloud skill
**Rejected**: User requested project-specific with gapless-crypto-clickhouse context

### Alternative 3: Include executable scripts/
**Rejected**: User requested "documentation only" for flexibility

### Alternative 4: Store in ~/.claude/skills/
**Rejected**: User requested project-local for version control integration

## Implementation

See: [`docs/development/plan/0025-clickhouse-cloud-skills/plan.md`](/Users/terryli/eon/gapless-crypto-clickhouse/docs/development/plan/0025-clickhouse-cloud-skills/plan.md)

**ADR-Task Sync**: Plan contains (a) plan, (b) context, (c) task list maintained via TodoWrite tool

## Validation

- [ ] All 3 skills pass marketplace validation (`quick_validate.py`)
- [ ] CLAUDE.md updated with Link Farm + Hub-and-Spoke pattern
- [ ] No secrets exposed in skill files
- [ ] Build succeeds (no validation errors)
- [ ] Conventional commit created
- [ ] Logged to `logs/0025-clickhouse-cloud-skills-20251121_124019.log`

## References

- Source: `/tmp/clickhouse_setup_final_summary.md` (validated production setup)
- Skill Architecture: [`~/.claude/skills/skill-architecture/SKILL.md`](/Users/terryli/.claude/skills/skill-architecture/SKILL.md)
- Marketplace Validator: `/Users/terryli/.claude/plugins/marketplaces/anthropic-agent-skills/skill-creator/scripts/quick_validate.py`
- Project Memory: [`CLAUDE.md`](/Users/terryli/eon/gapless-crypto-clickhouse/CLAUDE.md) (Link Farm pattern)
