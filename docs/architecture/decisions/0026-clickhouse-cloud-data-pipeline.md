# ADR-0026: ClickHouse Cloud Data Pipeline for Company Employees

**Status**: Accepted

**Date**: 2025-11-21

**ADR ID**: 0026

**Related Plans**: [`docs/development/plan/0026-clickhouse-cloud-data-pipeline/plan.md`](/Users/terryli/eon/gapless-crypto-clickhouse/docs/development/plan/0026-clickhouse-cloud-data-pipeline/plan.md)

## Context

Following ADR-0025 (ClickHouse Cloud skills extraction), we identified gaps in enabling company-wide usage of `gapless-crypto-clickhouse` package with ClickHouse Cloud credentials. Four parallel investigation agents (Infrastructure, Package Architecture, User Experience, Security) revealed:

**Critical Blocker**:
- Package cannot connect to ClickHouse Cloud (missing `secure=True` parameter for TLS/SSL)
- Code fix required in `connection.py:93` and `config.py`

**User Experience Gaps**:
- No onboarding documentation for company employees using Claude Code CLI
- No Cloud-specific `.env` template (current template is Docker localhost-only)
- Skills are infrastructure-focused, not SDK end-user focused

**Target Audience**:
- 3-10 company employees (Claude Code CLI users)
- All have admin access to ClickHouse Cloud (binary access model)
- Non-admin employees use file-based API only (no ClickHouse features)

**Design Constraints** (from user clarification):
- Doppler + local `.env` fallback for credential access
- No RBAC needed (all authorized users are trusted admins)
- Documentation optimized for Claude Code CLI agent consumption
- No IP allowlist changes (keep `0.0.0.0/0`)

## Decision

Implement robust data pipeline for company-wide ClickHouse Cloud access via:

### 1. Fix Critical Bug: Add `secure=True` Parameter Support

**Intent**: Enable TLS/SSL connections to ClickHouse Cloud

**Abstractions**:
- Add `secure` field to `ClickHouseConfig` dataclass
- Load from `CLICKHOUSE_SECURE` environment variable (default: `false`)
- Pass to `clickhouse_connect.get_client(secure=...)` parameter

**Files**:
- `src/gapless_crypto_clickhouse/clickhouse/config.py` (config layer)
- `src/gapless_crypto_clickhouse/clickhouse/connection.py` (client layer)
- `.env.example` (documentation)

### 2. Create Onboarding Skill (Claude Code CLI Optimized)

**Name**: `gapless-crypto-clickhouse-onboarding`

**Intent**: Step-by-step workflow for Claude Code CLI agents to onboard company employees

**Pattern**: Workflow Pattern (prescriptive multi-step procedure)

**Bundled Resources**:
- `scripts/test_connection_cloud.py` - Connection validator with diagnostics
- `references/troubleshooting.md` - Common errors + actionable fixes
- `references/doppler-setup.md` - Doppler CLI configuration workflow
- `references/env-setup.md` - Local `.env` file configuration (fallback)

**Progressive Disclosure**:
- **Level 1** (metadata): Name + description with trigger phrases ("onboarding", "company employees", "ClickHouse Cloud")
- **Level 2** (SKILL.md): Step-by-step workflow (5-minute onboarding path)
- **Level 3** (resources): Detailed troubleshooting, test scripts, Doppler setup

### 3. Cloud Configuration Template

**File**: `.env.cloud`

**Intent**: ClickHouse Cloud-specific environment variable template

**Content**:
- Service hostname pattern (`*.aws.clickhouse.cloud`)
- Port 8443 (HTTPS, not 8123)
- `CLICKHOUSE_SECURE=true` (required for Cloud)
- Doppler integration notes
- No actual credentials (template only)

### 4. Project Memory Integration

**CLAUDE.md Update**: New "Company Employee Onboarding" section

**Pattern**: Link Farm + Hub-and-Spoke progressive disclosure

**Content**:
- Absolute path to onboarding skill
- "When to use" trigger guidance
- Key principle statement (Claude Code CLI optimized)

## Consequences

### Positive

- ✅ **Package works with ClickHouse Cloud**: `secure=True` enables TLS connections
- ✅ **<15 minute onboarding**: Claude Code CLI agents guide employees through complete setup
- ✅ **Flexible credential access**: Doppler (recommended) + local `.env` (fallback)
- ✅ **AI agent discoverable**: Skill metadata includes trigger phrases for automatic activation
- ✅ **Binary access model**: Clear distinction (admins use Cloud, non-admins use file-based API)
- ✅ **Zero breaking changes**: `secure` defaults to `false` (backward compatible)

### Negative

- ⚠️ **Project-local skill overhead**: Skill specific to gapless-crypto-clickhouse (intentional)
- ⚠️ **Dual credential paths**: Must maintain Doppler + `.env` documentation (added flexibility)

### Neutral

- Skills stored in project repo (`./skills/`), not global (`~/.claude/skills/`)
- Shared credentials acceptable for 3-10 trusted admin team

## Alternatives Considered

### Alternative 1: Document `secure=True` workaround only

**Rejected**: Requires users to manually create `clickhouse_connect.get_client()` bypassing package abstraction. Poor SDK experience.

### Alternative 2: Individual credentials per user (RBAC)

**Rejected**: User clarified all authorized employees are trusted admins (binary access model). RBAC overhead unnecessary for 3-10 users.

### Alternative 3: Generic ClickHouse onboarding skill (global)

**Rejected**: User requested project-specific skill optimized for `gapless-crypto-clickhouse` package + Claude Code CLI.

### Alternative 4: IP allowlist restriction

**Rejected**: User confirmed keep `0.0.0.0/0` (rely on password authentication).

## Implementation

See: [`docs/development/plan/0026-clickhouse-cloud-data-pipeline/plan.md`](/Users/terryli/eon/gapless-crypto-clickhouse/docs/development/plan/0026-clickhouse-cloud-data-pipeline/plan.md)

**ADR-Task Sync**: Plan contains (a) plan, (b) context, (c) task list maintained via TodoWrite tool

## Validation

- [ ] `secure` parameter added to `ClickHouseConfig`
- [ ] Package connects to ClickHouse Cloud with `secure=True`
- [ ] `.env.cloud` template created
- [ ] Onboarding skill passes marketplace validation
- [ ] CLAUDE.md updated with Link Farm pattern
- [ ] Tests pass with Cloud configuration
- [ ] Conventional commit created
- [ ] Logged to `logs/0026-clickhouse-cloud-data-pipeline-20251121_234121.log`

## References

- **ADR-0025**: ClickHouse Cloud skills extraction (infrastructure workflows)
- **Sub-agent Reports**: Infrastructure, Package Architecture, User Experience, Security agents
- **Skill Architecture**: [`~/.claude/skills/skill-architecture/SKILL.md`](/Users/terryli/.claude/skills/skill-architecture/SKILL.md)
- **Marketplace Validator**: `/Users/terryli/.claude/plugins/marketplaces/anthropic-agent-skills/skill-creator/scripts/quick_validate.py`
- **Project Memory**: [`CLAUDE.md`](/Users/terryli/eon/gapless-crypto-clickhouse/CLAUDE.md)
