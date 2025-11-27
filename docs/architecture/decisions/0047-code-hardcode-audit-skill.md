# ADR-0047: Code Hardcode Audit Skill

## Status

Accepted

## Context

After implementing ADR-0046 (Semantic Constants Abstraction), a need emerged for automated detection of:

- Magic numbers in code
- Duplicate constant definitions across files
- Hardcoded URLs, ports, file paths
- DRY violations

Manual discovery of these patterns is error-prone and incomplete. A systematic approach using multiple complementary tools provides comprehensive coverage.

## Decision

Create a global Claude Code skill `code-hardcode-audit` at `~/.claude/skills/` that combines three tools:

| Tool             | Detection Focus                          | Language Support |
| ---------------- | ---------------------------------------- | ---------------- |
| **Ruff PLR2004** | Magic value comparisons                  | Python           |
| **Semgrep**      | Pattern-based (URLs, ports, credentials) | Multi-language   |
| **jscpd**        | Copy-paste duplicate blocks              | Multi-language   |

### Key Design Decisions

1. **jscpd via npx**: On-demand execution using `npx jscpd` avoids installing Homebrew's duplicate Node.js (17 dependencies)

2. **Parallel execution**: All tools run concurrently via `concurrent.futures` for performance

3. **Dual output format**: JSON (programmatic) + compiler-like text (human-readable)

4. **Separate from code-clone-assistant**: Different focus (hardcodes vs DRY); cross-reference in docs

5. **7 custom Semgrep rules**: URLs, ports, timeframes, paths, credentials, retry config

## Consequences

### Positive

- Systematic detection of hardcoded values
- Unified output enables automated refactoring planning
- Complementary tools cover detection gaps
- Global skill callable from any project

### Negative

- Requires Node.js for jscpd (available via mise)
- Initial Semgrep rule tuning may produce false positives

## References

- ADR-0046: Semantic Constants Abstraction
- [Ruff PLR2004 docs](https://docs.astral.sh/ruff/rules/magic-value-comparison/)
- [jscpd GitHub](https://github.com/kucherenko/jscpd)
- [Semgrep custom rules](https://semgrep.dev/docs/writing-rules/overview)
