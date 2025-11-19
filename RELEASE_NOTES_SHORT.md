## 2.16.0 - 2025-10-01

### ✨ New Features

- Implement SOTA pre-flight version validation with Commitizen - Replace custom validation hook with industry-standard Commitizen - Add mandatory version bump enforcement via pre-commit hooks - Configure conventional commits with commit-msg validation - Add pre-push branch validation with origin/main comparison - Remove legacy custom validation hook in favor of elegant solution This implements unanimous 8/8 research agent consensus for pre-commit version control. (by @terrylica)

### 🔒 Security Fixes

- Prevent path traversal attacks in BinancePublicDataCollector Implement comprehensive input validation to address security vulnerabilities reported by ML Feature Experiments Team (SEC-01 through SEC-04): - SEC-01 (HIGH): Prevent path traversal via symbol parameter (CWE-22) _ Reject directory navigation characters (/, \, ., ..) _ Enforce alphanumeric-only symbols with regex validation _ CVSS 7.5 vulnerability now mitigated - SEC-02 (MEDIUM): Reject empty symbol strings _ Validate non-empty and non-whitespace inputs _ Clear error messages for users - SEC-03 (MEDIUM): Reject None symbol values _ Explicit None checks prevent AttributeError downstream _ Early validation with clear error messages - SEC-04 (LOW): Validate date range logic _ Ensure end_date >= start_date \* Enhanced date format error handling Security improvements: - Added \_validate_symbol() method with whitelist validation - Symbol normalization to uppercase - Comprehensive docstring updates with security notes - 17 new security-focused unit tests (100% pass rate) - Backwards compatible with all valid usage Testing: - 42 tests passed, 1 skipped - All ruff checks passed - No regressions in existing functionality Addresses security audit findings from ml-feature-experiments team (by @terrylica)

---

**Full Changelog**: https://github.com/terrylica/rangebar/compare/v2.15.3...v2.16.0

---

_Full changelog: [CHANGELOG.md](https://github.com/terrylica/gapless-crypto-data/blob/v3.0.0/CHANGELOG.md)_
