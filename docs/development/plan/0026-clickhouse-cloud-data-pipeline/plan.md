# Plan: ClickHouse Cloud Data Pipeline for Company Employees

**ADR ID**: 0026
**Date**: 2025-11-21
**Status**: In Progress
**Owner**: Terry Li

## Objective

Enable 3-10 company employees (Claude Code CLI users) to seamlessly use `gapless-crypto-clickhouse` package with ClickHouse Cloud credentials via Doppler or local `.env` files.

## Background

### Context

**Investigation Phase** (2025-11-21 23:40 UTC):

Spawned 4 parallel sub-agents using DCTL (Dynamic Todo List Creation) pattern to investigate data pipeline design:

1. **Infrastructure Agent**: Discovered critical `secure=True` bug blocking ClickHouse Cloud connections
2. **Package Architecture Agent**: Identified environment-driven config strengths + Cloud documentation gaps
3. **User Experience Agent**: Found no onboarding workflow for company employees (Claude Code CLI users)
4. **Security Agent**: Confirmed shared credentials acceptable for 3-10 trusted admin team

**User Clarifications** (iterative loop):

- **Access Model**: Binary (admins have full Cloud access, non-admins use file-based API only)
- **User Count**: 3-10 users (small trusted team)
- **RBAC**: Not needed (all authorized users are admins)
- **Credential Access**: Doppler + local `.env` fallback
- **Documentation**: Optimize for Claude Code CLI agent consumption (create skill)
- **IP Security**: Keep `0.0.0.0/0` (no IP allowlist changes)

### Goals

1. **Fix critical bug**: Add `secure=True` parameter support for ClickHouse Cloud TLS connections
2. **<15 minute onboarding**: Claude Code CLI agents guide employees through complete setup
3. **Flexible credentials**: Support Doppler (recommended) + `.env` (fallback)
4. **AI discoverability**: Skill with trigger phrases for automatic activation
5. **Observability**: Connection test script with diagnostics

### Non-Goals

- RBAC or per-user credentials (all admins share credentials)
- IP allowlist configuration (keep current `0.0.0.0/0`)
- Generic ClickHouse skill (project-specific intentionally)
- Backward compatibility (fresh start, `secure` defaults to `false` is sufficient)

## Plan

### Architecture

**Pattern**: 3-component solution

```
1. Code Fix (secure parameter)
   └── src/gapless_crypto_clickhouse/clickhouse/
       ├── config.py (add secure field)
       └── connection.py (pass to client)

2. Cloud Configuration Template
   └── .env.cloud (ClickHouse Cloud env vars)

3. Onboarding Skill (Claude Code CLI optimized)
   └── ./skills/gapless-crypto-clickhouse-onboarding/
       ├── SKILL.md (workflow pattern)
       ├── scripts/test_connection_cloud.py
       └── references/
           ├── troubleshooting.md
           ├── doppler-setup.md
           └── env-setup.md
```

**CLAUDE.md Integration**: New "Company Employee Onboarding" section (Link Farm pattern)

### Implementation Steps

#### Phase 1: Documentation Structure (ADR + Plan)

1. ✅ Create ADR-0026 (MADR format)
2. ✅ Create plan directory: `docs/development/plan/0026-clickhouse-cloud-data-pipeline/`
3. ✅ Create plan.md (this file, Google Design Doc format)
4. ✅ Initialize TodoWrite task list
5. ✅ Initialize log file: `logs/0026-clickhouse-cloud-data-pipeline-20251121_234121.log`

#### Phase 2: Code Fix (secure Parameter)

6. Add `secure` field to `ClickHouseConfig`:
   - Add `secure: bool = False` to dataclass
   - Load from `CLICKHOUSE_SECURE` environment variable in `from_env()`
   - Document in docstring

7. Pass `secure` to clickhouse-connect client:
   - Modify `connection.py` line 93 to include `secure=self.config.secure`
   - Update connection error messages with Cloud troubleshooting

8. Create `.env.cloud` template:
   - ClickHouse Cloud-specific configuration
   - Service hostname pattern
   - Port 8443 (HTTPS)
   - `CLICKHOUSE_SECURE=true`
   - Doppler integration notes

#### Phase 3: Onboarding Skill Creation

9. Initialize skill using marketplace script:
   ```bash
   /Users/terryli/.claude/plugins/marketplaces/anthropic-agent-skills/skill-creator/scripts/init_skill.py gapless-crypto-clickhouse-onboarding --path ./skills/
   ```

10. Write `SKILL.md` (Workflow Pattern):
    - YAML frontmatter with trigger phrases
    - Step-by-step onboarding workflow (<5 minutes)
    - When to use this skill
    - How Claude should use bundled resources

11. Create `scripts/test_connection_cloud.py`:
    - Connection validator with diagnostics
    - Doppler environment check
    - Test queries (version, user, table count)
    - Actionable error messages

12. Create `references/troubleshooting.md`:
    - Common errors (connection refused, SSL/TLS, auth failed, timeout)
    - Actionable fixes for each error
    - ClickHouse Cloud-specific guidance

13. Create `references/doppler-setup.md`:
    - Doppler CLI installation
    - Access verification (`doppler secrets --project aws-credentials --config prd`)
    - Running scripts with Doppler (`doppler run --`)

14. Create `references/env-setup.md`:
    - Local `.env` file creation (fallback)
    - `.env.cloud` template usage
    - Security warnings (never commit credentials)

#### Phase 4: Validation

15. Validate skill with marketplace validator:
    ```bash
    /Users/terryli/.claude/plugins/marketplaces/anthropic-agent-skills/skill-creator/scripts/quick_validate.py ./skills/gapless-crypto-clickhouse-onboarding/
    ```

16. Test `secure` parameter with local Docker:
    - Set `CLICKHOUSE_SECURE=false`
    - Verify connection works as before
    - Confirm backward compatibility

17. Update CLAUDE.md:
    - Add "Company Employee Onboarding" section after "ClickHouse Cloud Setup"
    - Use Link Farm pattern (absolute path to skill)
    - Include "When to use" and "Key principle"

#### Phase 5: Testing

18. Run tests with Cloud configuration:
    ```bash
    uv run pytest tests/ -v
    ```

19. Verify build succeeds:
    ```bash
    uv build
    ```

#### Phase 6: Commit

20. Create conventional commit:
    ```
    feat(cloud): add secure parameter + onboarding skill for company ClickHouse Cloud access

    - Add CLICKHOUSE_SECURE env var support for TLS/SSL connections
    - Create gapless-crypto-clickhouse-onboarding skill (Claude Code CLI optimized)
    - Add .env.cloud template for ClickHouse Cloud configuration
    - Update CLAUDE.md with Company Employee Onboarding section

    Fixes critical bug preventing ClickHouse Cloud connections (missing secure=True).
    Enables <15 minute onboarding for 3-10 company employees via Doppler or .env.

    Refs: ADR-0026
    ```

21. Log completion to `logs/0026-clickhouse-cloud-data-pipeline-20251121_234121.log`

### Success Criteria

- [ ] `secure` parameter added to `ClickHouseConfig` and `ClickHouseConnection`
- [ ] Package connects to ClickHouse Cloud with `secure=True`
- [ ] `.env.cloud` template created with Cloud-specific configuration
- [ ] Onboarding skill passes marketplace validation
- [ ] CLAUDE.md updated with Link Farm + Hub-and-Spoke pattern
- [ ] Tests pass with both `secure=false` (local) and `secure=true` (Cloud)
- [ ] Build succeeds with no validation errors
- [ ] Conventional commit created
- [ ] Logged to `logs/0026-clickhouse-cloud-data-pipeline-20251121_234121.log`

## Context

### Source Material

**Sub-Agent Reports** (tmp/data-pipeline-design/):

- **Infrastructure Agent**: Found `secure=True` bug, documented current connection architecture
- **Package Architecture Agent**: Analyzed configuration entry points, identified Cloud documentation gaps
- **User Experience Agent**: Identified onboarding workflow gaps, drafted Day 1 checklist
- **Security Agent**: Confirmed shared credentials acceptable for small team, documented access control

**Existing Skills** (recently created):

- `clickhouse-cloud-service-setup` - Infrastructure-focused (API-driven service discovery)
- `clickhouse-cloud-credentials` - Infrastructure-focused (Doppler + 1Password storage)
- `clickhouse-cloud-connection` - Infrastructure-focused (connection validation)

**Gap**: No SDK end-user onboarding skill for company employees using Claude Code CLI

### User Requirements (from clarification loop)

1. **Fix critical bug**: Add `secure=True` parameter (code change required)
2. **Doppler + .env fallback**: Support both credential access methods
3. **Claude Code CLI optimized**: Create skill for AI agent consumption
4. **Small team (3-10 users)**: Shared credentials acceptable
5. **Binary access model**: Admins have full Cloud access, non-admins use file-based API
6. **No IP allowlist**: Keep `0.0.0.0/0`

### Related Work

- **ADR-0025**: ClickHouse Cloud skills extraction (infrastructure workflows)
- **skill-architecture**: [`~/.claude/skills/skill-architecture/SKILL.md`](/Users/terryli/.claude/skills/skill-architecture/SKILL.md)
- **Marketplace validator**: `/Users/terryli/.claude/plugins/marketplaces/anthropic-agent-skills/skill-creator/scripts/quick_validate.py`

### Constraints

- **No backward compatibility needed**: `secure` defaults to `false` (existing behavior)
- **SLO focus**: Availability, correctness, observability, maintainability (not speed/perf/security)
- **Project-local skill**: Specific to gapless-crypto-clickhouse (intentional)

## Task List

**Status**: 21/21 tasks complete (100%) ✅

**All Tasks Completed**:

- [x] Create ADR-0026
- [x] Create plan directory and plan.md
- [x] Initialize TodoWrite task list
- [x] Initialize log file
- [x] Add secure parameter to ClickHouseConfig
- [x] Pass secure to clickhouse-connect client
- [x] Create .env.cloud template
- [x] Initialize onboarding skill
- [x] Write SKILL.md
- [x] Create scripts/test_connection_cloud.py
- [x] Create references/troubleshooting.md
- [x] Create references/doppler-setup.md
- [x] Create references/env-setup.md
- [x] Validate skill (passed marketplace validator)
- [x] Test secure parameter with local Docker
- [x] Update CLAUDE.md
- [x] Run tests with Cloud configuration
- [x] Verify build succeeds
- [x] Create conventional commit
- [x] Publish v7.0.0 to PyPI (semantic-release local-first workflow)
- [x] Create GitHub v7.0.0 release

**Release Method**: Local-first semantic-release workflow (recommended by semantic-release skill)
- GitHub Actions failed (doppler not installed, 403 PyPI auth)
- Successfully completed via local `uv build` + `uv publish` with Doppler credentials
- Total time: ~25 minutes (vs 2-5 min estimated for GitHub Actions if working)

## Risks and Mitigations

| Risk                                      | Impact | Mitigation                                                      |
| ----------------------------------------- | ------ | --------------------------------------------------------------- |
| Tests fail with `secure=True` locally     | Medium | Test only validates parameter passing, Cloud test manual        |
| Skill validation fails                    | Medium | Use quick_validate.py iteratively during development            |
| CLAUDE.md Link Farm pattern inconsistent  | Low    | Follow existing ADR-0025 pattern exactly                        |
| Doppler access not documented clearly     | High   | Create dedicated reference doc with step-by-step verification   |
| .env fallback creates credential leakage  | High   | Add security warnings, confirm .env in .gitignore               |

## Timeline

**Start**: 2025-11-21 23:41 UTC
**Estimated Duration**: 2-3 hours
**Log file**: `logs/0026-clickhouse-cloud-data-pipeline-20251121_234121.log`

**Progress logging**: Status updates every 15-60s for operations >1min

## References

- **ADR-0026**: [`docs/architecture/decisions/0026-clickhouse-cloud-data-pipeline.md`](/Users/terryli/eon/gapless-crypto-clickhouse/docs/architecture/decisions/0026-clickhouse-cloud-data-pipeline.md)
- **Project Memory**: [`CLAUDE.md`](/Users/terryli/eon/gapless-crypto-clickhouse/CLAUDE.md)
- **skill-architecture**: [`~/.claude/skills/skill-architecture/SKILL.md`](/Users/terryli/.claude/skills/skill-architecture/SKILL.md)
- **Sub-Agent Reports**: tmp/data-pipeline-design/ (ephemeral)
