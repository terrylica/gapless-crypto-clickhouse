# Code Hardcode Audit Skill

**ADR**: [0047](docs/architecture/decisions/0047-code-hardcode-audit-skill.md)
**adr-id**: 0047
**Status**: Completed
**Last Updated**: 2025-11-26

## Context

### Problem Statement

After ADR-0046 (Semantic Constants Abstraction), manual discovery of hardcoded values is:

- Error-prone and incomplete
- Time-consuming for large codebases
- Inconsistent across team members

### Investigation Summary (9 Sub-Agents)

| Batch | Agent               | Finding                                      |
| ----- | ------------------- | -------------------------------------------- |
| 1     | Tool Inventory      | semgrep ✅, ruff ✅, jscpd ❌ (only missing) |
| 1     | Skills Architecture | 26 skills, 4 patterns, standard SKILL.md     |
| 1     | Skill-Architecture  | YAML frontmatter, progressive disclosure     |
| 2     | jscpd Installation  | `npx jscpd` (on-demand, mise Node.js)        |
| 2     | Skill Design        | Orchestrator + 3 wrappers, parallel          |
| 2     | Output Format       | Dual: JSON + compiler-like text              |
| 3     | Semgrep Rules       | 7 rules for URLs, ports, timeframes          |
| 3     | Existing Overlap    | `code-clone-assistant` uses PMD CPD          |
| 3     | Validation          | `quick_validate.py` + /tmp/ fixtures         |

### User Decisions (Confirmed)

| Decision       | Choice                         |
| -------------- | ------------------------------ |
| Skill Name     | `code-hardcode-audit`          |
| Location       | `~/.claude/skills/`            |
| jscpd Install  | `npx jscpd` (on-demand)        |
| Default Output | `both` (JSON + text)           |
| Semgrep Rules  | Full 7 rules                   |
| Existing Skill | Keep separate, cross-reference |
| Fix Existing   | Yes (Vulture → PMD CPD)        |

## Plan

### Skill Architecture

```
~/.claude/skills/code-hardcode-audit/
├── SKILL.md                           # Main instructions
├── scripts/
│   ├── audit_hardcodes.py             # Orchestrator
│   ├── run_jscpd.py                   # jscpd wrapper
│   ├── run_semgrep.py                 # Semgrep wrapper
│   └── run_ruff_plr.py                # Ruff wrapper
├── references/
│   ├── tool-comparison.md
│   ├── output-schema.md
│   └── troubleshooting.md
└── assets/
    └── semgrep-hardcode-rules.yaml    # 7 custom rules
```

### Tool Configuration

| Tool    | Command                                            | Output |
| ------- | -------------------------------------------------- | ------ |
| Ruff    | `ruff check --select PLR2004 --output-format json` | JSON   |
| Semgrep | `semgrep --config assets/*.yaml --json`            | JSON   |
| jscpd   | `npx jscpd --reporters json`                       | JSON   |

### Output Schema

```json
{
  "summary": { "total_findings": N, "by_tool": {...}, "by_severity": {...} },
  "findings": [{ "id": "MAGIC-001", "tool": "ruff", "file": "...", "line": N, ... }],
  "refactoring_plan": [{ "priority": 1, "action": "...", "finding_ids": [...] }]
}
```

## Task List

| #   | Task                      | Status | Notes                           |
| --- | ------------------------- | ------ | ------------------------------- |
| 1   | Create ADR-0047           | Done   | MADR format                     |
| 2   | Move plan to docs/        | Done   | adr-id=0047                     |
| 3   | Create skill directories  | Done   | scripts/, references/, assets/  |
| 4   | Create SKILL.md           | Done   | YAML frontmatter + triggers     |
| 5   | Create Semgrep rules      | Done   | 7 rules in assets/              |
| 6   | Create audit_hardcodes.py | Done   | Orchestrator with parallel exec |
| 7   | Create run_jscpd.py       | Done   | npx-based wrapper               |
| 8   | Create run_semgrep.py     | Done   | Semgrep wrapper                 |
| 9   | Create run_ruff_plr.py    | Done   | Ruff PLR2004 wrapper            |
| 10  | Create references         | Done   | 3 reference docs                |
| 11  | Validate skill            | Done   | Tested on /tmp/hardcode-test/   |
| 12  | Test on fixtures          | Done   | 4 findings detected             |
| 13  | Fix code-clone-assistant  | Done   | Vulture → PMD CPD               |

## Success Criteria

1. Skill passes `quick_validate.py`
2. All scripts run without errors
3. Output matches JSON schema
4. Semgrep rules validate
5. Triggers on relevant keywords
6. Actionable for Claude Code refactoring
