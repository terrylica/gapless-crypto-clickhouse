# Plan: Extract ClickHouse Cloud Setup Workflows into Atomic Skills

**ADR ID**: 0025
**Date**: 2025-11-21
**Status**: In Progress
**Owner**: Terry Li

## Objective

Extract validated ClickHouse Cloud setup workflows from production session (`/tmp/clickhouse_setup_final_summary.md`) into 3 atomic project-local skills following Link Farm + Hub-and-Spoke progressive disclosure pattern.

## Background

### Context

During ClickHouse Cloud migration (2025-11-20 22:49 PST):

- Successfully provisioned ClickHouse Cloud service (service ID: `a3163f31-21f4-4e22-844e-ef3fbc26ace2`)
- Stored credentials in Doppler (`aws-credentials/prd` project) + 1Password (Engineering vault)
- Validated connection to ClickHouse Cloud (version: 25.8.1.8702)
- Total setup time: 15 minutes, 100% success rate, $0 cost (using $300 free credits)

Workflows are **prescriptive and repeatable**—ideal for codification as skills.

### Goals

1. **Repeatability**: Enable future ClickHouse Cloud service setup without rediscovery
2. **Discoverability**: Claude proactively suggests workflows when relevant keywords detected
3. **Maintainability**: Single source of truth in version control
4. **Security**: No secrets in skills, only credential store references (Doppler key names, 1Password vault names)
5. **Observability**: Explicit documentation of API endpoints, required secrets, test procedures

### Non-Goals

- Generic ClickHouse Cloud skill (project-specific intentionally)
- Executable scripts (documentation-only per user request)
- Global skill installation (project-local in `./skills/`)
- Backward compatibility (fresh start, no legacy)

## Plan

### Architecture

**Pattern**: 3 atomic skills (modular, independently reusable)

```
./skills/
├── clickhouse-cloud-service-setup/
│   ├── SKILL.md                 # API-driven service discovery
│   └── references/
│       └── api-endpoints.md     # ClickHouse Cloud API reference
├── clickhouse-cloud-credentials/
│   ├── SKILL.md                 # Dual credential storage (Doppler + 1Password)
│   └── references/
│       ├── doppler-schema.md    # Required Doppler secrets
│       └── onepassword-schema.md # Required 1Password fields
└── clickhouse-cloud-connection/
    ├── SKILL.md                 # Connection validation
    └── references/
        └── connection-test.py   # Example test script (reference only)
```

**CLAUDE.md Integration**: New "ClickHouse Cloud Setup" section (after line 49, after "Validated Workflows")

### Implementation Steps

#### Phase 1: Documentation Structure (ADR + Plan)

1. ✅ Create ADR-0025 (MADR format)
2. ✅ Create plan directory: `docs/development/plan/0025-clickhouse-cloud-skills/`
3. ✅ Create plan.md (this file, Google Design Doc format)
4. ✅ Initialize TodoWrite task list
5. ✅ Initialize log file: `logs/0025-clickhouse-cloud-skills-20251121_124019.log`

#### Phase 2: Skill Initialization

6. Create project-local skills directory: `./skills/`
7. Initialize 3 skills using marketplace script:
   - `clickhouse-cloud-service-setup`
   - `clickhouse-cloud-credentials`
   - `clickhouse-cloud-connection`

#### Phase 3: Skill Content Creation

8. Write `clickhouse-cloud-service-setup/SKILL.md`:
   - Extract API-driven service discovery workflow
   - Document authentication (API Key ID + Secret from Doppler)
   - Document organization resolution (`GET /v1/organizations`)
   - Document service details fetch (`GET /v1/organizations/{org_id}/services/{service_id}`)
   - Document endpoint extraction (HTTPS 8443, Native 9440)

9. Write `clickhouse-cloud-service-setup/references/api-endpoints.md`:
   - ClickHouse Cloud API base URL
   - Authentication scheme (HTTP Basic Auth)
   - Organization and service endpoints
   - Response schema examples

10. Write `clickhouse-cloud-credentials/SKILL.md`:
    - Extract dual credential storage workflow
    - Document 8 Doppler secrets (project: `aws-credentials/prd`)
    - Document 8 1Password fields (vault: Engineering `fnzrqcsl3pl3bcdojrxf46whnu`, item: "ClickHouse Cloud - gapless-crypto-cli")
    - Credential naming convention

11. Write `clickhouse-cloud-credentials/references/doppler-schema.md`:
    - Required Doppler project structure
    - 8 required secrets with descriptions
    - No actual secret values

12. Write `clickhouse-cloud-credentials/references/onepassword-schema.md`:
    - Required 1Password vault and item structure
    - 8 required fields with types
    - No actual secret values

13. Write `clickhouse-cloud-connection/SKILL.md`:
    - Extract connection validation workflow
    - Document clickhouse-connect client configuration (`secure=True`)
    - Document Doppler environment loading
    - Document test queries (version, user, table count)

14. Write `clickhouse-cloud-connection/references/connection-test.py`:
    - Example Python test script (reference, not executed)
    - Shows clickhouse-connect usage pattern
    - Shows Doppler integration pattern

#### Phase 4: Validation

15. Validate each skill with marketplace validator:

    ```bash
    quick_validate.py skills/clickhouse-cloud-service-setup/
    quick_validate.py skills/clickhouse-cloud-credentials/
    quick_validate.py skills/clickhouse-cloud-connection/
    ```

16. Verify no secrets exposed (grep for actual values)

#### Phase 5: Integration

17. Update `CLAUDE.md`:
    - Add "ClickHouse Cloud Setup" section after line 49
    - Use Link Farm pattern (absolute paths)
    - Follow Hub-and-Spoke progressive disclosure
    - Include "When to use" and "Key principle"

18. Run build validation (if applicable)

#### Phase 6: Commit

19. Create conventional commit:

    ```
    docs(skills): extract ClickHouse Cloud setup workflows into atomic skills

    - Add clickhouse-cloud-service-setup skill (API-driven service discovery)
    - Add clickhouse-cloud-credentials skill (Doppler + 1Password storage)
    - Add clickhouse-cloud-connection skill (connection validation)
    - Update CLAUDE.md with ClickHouse Cloud Setup section
    - Add ADR-0025 for skills extraction decision

    Refs: ADR-0025, /tmp/clickhouse_setup_final_summary.md (validated production setup)
    ```

20. Log completion to `logs/0025-clickhouse-cloud-skills-20251121_124019.log`

### Success Criteria

- [ ] All 3 skills pass marketplace validation (YAML frontmatter, structure, naming)
- [ ] No secrets exposed (grep verification)
- [ ] CLAUDE.md updated with proper Link Farm + Hub-and-Spoke pattern
- [ ] Skills are discoverable via Claude's skill system
- [ ] Build succeeds with no validation errors
- [ ] Conventional commit created
- [ ] Logged to `logs/0025-clickhouse-cloud-skills-20251121_124019.log`

## Context

### Source Material

**Primary**: `/tmp/clickhouse_setup_final_summary.md`

- Validated production setup (2025-11-20 22:49 PST)
- 100% success rate
- Contains complete workflows with actual (sanitized) examples

### User Requirements (from clarification loop)

1. **Skill Scope**: Multiple atomic skills (not single comprehensive)
2. **Generalization**: Project-specific (gapless-crypto-clickhouse)
3. **Workflow Type**: Prescriptive setup workflow
4. **Credentials**: Reference to credential store (Doppler/1Password names, no secrets)
5. **Automation**: Documentation only (no scripts/)
6. **Location**: Project-local (`./skills/`)
7. **CLAUDE.md Update**: New "ClickHouse Cloud Setup" section

### Related Work

- **skill-architecture**: [`~/.claude/skills/skill-architecture/SKILL.md`](/Users/terryli/.claude/skills/skill-architecture/SKILL.md)
- **Marketplace validator**: `/Users/terryli/.claude/plugins/marketplaces/anthropic-agent-skills/skill-creator/scripts/quick_validate.py`
- **semantic-release**: [`~/.claude/skills/semantic-release/SKILL.md`](/Users/terryli/.claude/skills/semantic-release/SKILL.md)

### Constraints

- **No secrets**: Skills must not contain actual API keys, passwords, service IDs
- **No scripts**: Documentation-only per user request
- **Project-specific**: Skills reference gapless-crypto-clickhouse context
- **SLO focus**: Availability, correctness, observability, maintainability (not speed/perf/security)

## Task List

**Status**: 2/19 tasks complete (11%)

**In Progress**:

- [x] Create ADR-0025
- [x] Create plan directory and plan.md
- [ ] ⏳ Initialize 3 atomic skills

**Pending**:

- [ ] Write clickhouse-cloud-service-setup/SKILL.md
- [ ] Write clickhouse-cloud-service-setup/references/api-endpoints.md
- [ ] Write clickhouse-cloud-credentials/SKILL.md
- [ ] Write clickhouse-cloud-credentials/references/doppler-schema.md
- [ ] Write clickhouse-cloud-credentials/references/onepassword-schema.md
- [ ] Write clickhouse-cloud-connection/SKILL.md
- [ ] Write clickhouse-cloud-connection/references/connection-test.py
- [ ] Validate clickhouse-cloud-service-setup
- [ ] Validate clickhouse-cloud-credentials
- [ ] Validate clickhouse-cloud-connection
- [ ] Verify no secrets exposed
- [ ] Update CLAUDE.md
- [ ] Run build validation
- [ ] Create conventional commit
- [ ] Log completion

**Sync with TodoWrite**: This task list mirrors TodoWrite tool state (11 todos tracked)

## Risks and Mitigations

| Risk                                 | Impact | Mitigation                                                             |
| ------------------------------------ | ------ | ---------------------------------------------------------------------- |
| Secrets accidentally exposed         | High   | grep verification before commit, credential store references only      |
| Marketplace validation failure       | Medium | Use quick_validate.py iteratively during development                   |
| CLAUDE.md Link Farm pattern mismatch | Low    | Follow existing semantic-release, multi-agent-\* pattern exactly       |
| Skills not discoverable              | Medium | Test with relevant trigger phrases ("ClickHouse Cloud", "credentials") |

## Timeline

**Start**: 2025-11-21 12:40 PST
**Estimated Duration**: 30-45 minutes
**Log file**: `logs/0025-clickhouse-cloud-skills-20251121_124019.log`

**Progress logging**: Status updates every 15-60s for operations >1min

## References

- **ADR-0025**: [`docs/architecture/decisions/0025-clickhouse-cloud-skills-extraction.md`](/Users/terryli/eon/gapless-crypto-clickhouse/docs/architecture/decisions/0025-clickhouse-cloud-skills-extraction.md)
- **Source**: `/tmp/clickhouse_setup_final_summary.md`
- **Project Memory**: [`CLAUDE.md`](/Users/terryli/eon/gapless-crypto-clickhouse/CLAUDE.md)
- **skill-architecture**: [`~/.claude/skills/skill-architecture/SKILL.md`](/Users/terryli/.claude/skills/skill-architecture/SKILL.md)
