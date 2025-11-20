# Screenshot Baseline Management

**Version**: 1.0.0
**Last Updated**: 2025-11-19
**ADR**: [ADR-0013](../architecture/decisions/0013-autonomous-validation-framework.md)

---

## Overview

Screenshot baselines provide visual regression detection for ClickHouse web interfaces. This guide covers baseline creation, update procedures, and visual regression review workflows.

**Purpose**: Evidence-based validation - screenshots prove correct UI rendering across releases.

**SLOs**:

- **Correctness**: Visual regressions caught before production
- **Maintainability**: Clear baseline update process
- **Observability**: Screenshot diffs for all detected changes

---

## Baseline Concepts

### What Are Baselines?

**Baselines** are reference screenshots representing the expected (correct) visual state of the UI. E2E tests compare current screenshots against baselines to detect unintentional visual changes.

### When Are Baselines Used?

1. **Initial Test Run**: Baselines don't exist → Generated automatically
2. **Subsequent Runs**: Baselines exist → Current screenshot compared to baseline
3. **Visual Mismatch**: Difference detected → Test warning (not failure)

### Baseline Storage

```
tests/e2e/screenshots/          # Git-tracked baseline directory
├── ch-ui-landing.png           # CH-UI landing page baseline
├── ch-ui-simple-query.png      # CH-UI query execution baseline
├── clickhouse-play-landing.png # ClickHouse Play landing baseline
└── ...
```

**Git Tracking**: Baselines committed to version control for team consistency.

---

## Creating Initial Baselines

### First-Time Setup

When E2E tests run without existing baselines, screenshots are automatically captured to `tests/e2e/screenshots/`.

```bash
# Run E2E tests (generates baselines)
uv run scripts/run_validation.py --e2e-only

# Baselines saved to tests/e2e/screenshots/
# Review screenshots visually

# Commit baselines to git
git add tests/e2e/screenshots/
git commit -m "feat(e2e): add initial screenshot baselines"
```

### Baseline Naming Convention

```
{interface}-{scenario}.png

Examples:
- ch-ui-landing.png              # CH-UI landing page
- ch-ui-simple-query.png          # CH-UI after query execution
- ch-ui-error-invalid-query.png   # CH-UI error state
- clickhouse-play-landing.png     # ClickHouse Play landing
- clickhouse-play-large-results.png # ClickHouse Play with large dataset
```

---

## Updating Baselines

### When to Update

Update baselines when:

- ✅ **Intentional UI changes**: New features, redesigns, UX improvements
- ✅ **Dependency updates**: ClickHouse UI library updates changing appearance
- ✅ **Bug fixes**: Correcting visual defects

DO NOT update baselines for:

- ❌ **Test flakiness**: Random pixel differences (fix test instead)
- ❌ **Unintentional regressions**: Visual bugs (fix code instead)
- ❌ **CI vs local differences**: Environment-specific rendering (fix environment)

### Update Procedure

#### Step 1: Identify Changes

```bash
# Run E2E tests
uv run scripts/run_validation.py --e2e-only

# Review screenshots in tmp/validation-artifacts/screenshots/
# Compare against baselines in tests/e2e/screenshots/
```

#### Step 2: Visual Review

Open both screenshots side-by-side:

```bash
# Example: Compare CH-UI landing page
open tmp/validation-artifacts/screenshots/ch-ui-landing.png
open tests/e2e/screenshots/ch-ui-landing.png
```

**Review Checklist**:

- [ ] UI elements aligned correctly
- [ ] Text readable and properly formatted
- [ ] Colors/styles consistent with design
- [ ] No visual artifacts (clipping, overlap, misalignment)
- [ ] Responsive layout appropriate for viewport

#### Step 3: Update Baseline

If changes are intentional and correct:

```bash
# Copy new screenshot to baseline
cp tmp/validation-artifacts/screenshots/ch-ui-landing.png \
   tests/e2e/screenshots/ch-ui-landing.png

# Commit with clear message
git add tests/e2e/screenshots/ch-ui-landing.png
git commit -m "chore(e2e): update CH-UI landing baseline after redesign"
```

### Bulk Baseline Updates

When updating multiple baselines (e.g., UI library upgrade):

```bash
# Review all changes
diff -r tmp/validation-artifacts/screenshots/ tests/e2e/screenshots/

# Copy all updated screenshots
cp tmp/validation-artifacts/screenshots/*.png tests/e2e/screenshots/

# Commit with context
git add tests/e2e/screenshots/
git commit -m "chore(e2e): update all baselines after ClickHouse UI v2.0 upgrade"
```

---

## Visual Regression Detection

### Current Implementation

**Status**: Basic screenshot capture implemented.

**Behavior**: E2E tests capture screenshots for evidence, but **do not automatically compare** against baselines yet.

**Rationale**: Manual review provides:

- Context-aware decision making
- Flexibility for acceptable variations
- Clear audit trail via git commits

### Future Enhancement: Automated Comparison

**Planned** (future ADR):

- Playwright's `expect(page).to_have_screenshot()` for automated comparison
- Pixel difference thresholds (`maxDiffPixels`, `threshold`)
- Automatic diff image generation
- CI warnings (not failures) for visual changes

Example future implementation:

```python
# Future: Automated comparison
await expect(page).to_have_screenshot(
    "ch-ui-landing.png",
    max_diff_pixels=100,  # Allow 100 pixels difference
)
```

---

## Screenshot Quality

### Viewport Configuration

Consistent viewport ensures reproducible screenshots:

```python
# tests/e2e/conftest.py
@pytest.fixture(scope="session")
def browser_context_args(browser_context_args):
    return {
        **browser_context_args,
        "viewport": {"width": 1920, "height": 1080},  # Standard desktop
        "device_scale_factor": 1,  # No retina scaling
    }
```

### Screenshot Options

```python
# Full page screenshot (recommended for baselines)
await page.screenshot(path="full-page.png", full_page=True)

# Element screenshot (for focused comparisons)
element = page.locator(".result-table")
await element.screenshot(path="element.png")
```

### Handling Dynamic Content

#### Timestamps and Dates

**Problem**: Timestamps change on every test run, causing false positives.

**Solution**: Mask dynamic elements or use stable test data.

```python
# Option 1: Mask with CSS
await page.add_style_tag(content=".timestamp { visibility: hidden; }")

# Option 2: Use fixed date in query
await page.fill("input", "SELECT '2025-01-01' AS test_date")
```

#### Loading States

**Problem**: Loading spinners cause inconsistent screenshots.

**Solution**: Wait for loading to complete.

```python
# Wait for loading indicator to disappear
await page.locator(".loading-spinner").wait_for(state="hidden", timeout=5000)

# Wait for content to appear
await page.locator(".result-table").wait_for(state="visible")

# Then capture screenshot
await page.screenshot(path="stable.png")
```

---

## CI/CD Integration

### Baseline Consistency

**Challenge**: Screenshots may differ between local and CI environments due to:

- Font rendering differences (OS-specific)
- Browser version differences
- GPU/rendering engine variations

**Solution**: Always capture baselines in the same environment where tests will run (preferably CI).

### CI Baseline Generation

```bash
# Generate baselines in CI
# 1. Trigger workflow manually
# 2. Download artifacts after run
# 3. Review and commit to repository
```

### Handling CI Failures

When visual regressions detected in CI:

1. **Download artifacts**: `test-results/screenshots/`
2. **Review diff images**: Compare against baselines
3. **Determine action**:
   - **Intentional change**: Update baseline and push
   - **Regression**: Fix code and re-test
   - **Flake**: Investigate environment differences

---

## Best Practices

### DO

✅ Review every baseline update visually before committing
✅ Use descriptive commit messages explaining why baseline changed
✅ Capture baselines in consistent environment (CI recommended)
✅ Wait for loading states to complete before screenshot
✅ Mask or stabilize dynamic content (timestamps, animations)

### DON'T

❌ Update baselines without visual review
❌ Commit baseline updates without explanation
❌ Accept pixel-perfect matching (allow small tolerance)
❌ Mix local and CI-generated baselines
❌ Skip baseline updates when UI intentionally changes

---

## Troubleshooting

### Screenshots Look Different Locally vs CI

**Symptom**: Test passes locally but fails in CI (or vice versa).

**Causes**:

- Font rendering differences (macOS vs Linux)
- Browser version mismatch
- Viewport size mismatch

**Fix**:

```bash
# Regenerate baselines in CI
# Download CI artifacts
# Replace local baselines
```

### Screenshot Diff Too Sensitive

**Symptom**: Minor pixel differences causing false positives.

**Future Fix** (when automated comparison enabled):

```python
# Allow small pixel differences
await expect(page).to_have_screenshot(
    "baseline.png",
    max_diff_pixels=100,  # Tolerate 100 pixels difference
    threshold=0.2,  # 0-1 color difference threshold
)
```

### Baseline File Too Large

**Symptom**: Git repository growing due to large screenshots.

**Fix**:

- Use PNG optimization: `optipng tests/e2e/screenshots/*.png`
- Capture element screenshots instead of full page
- Use Git LFS for binary files (if needed)

---

## Workflow Summary

```
┌────────────────────────────────────────────┐
│ 1. Run E2E Tests                           │
│    uv run scripts/run_validation.py --e2e  │
└────────────┬───────────────────────────────┘
             │
             ▼
┌────────────────────────────────────────────┐
│ 2. Review Screenshots                      │
│    Compare: tmp/validation-artifacts/      │
│            vs tests/e2e/screenshots/       │
└────────────┬───────────────────────────────┘
             │
       ┌─────┴─────┐
       │           │
       ▼           ▼
┌──────────┐  ┌──────────┐
│ Match OK │  │ Mismatch │
└──────────┘  └────┬─────┘
                   │
            ┌──────┴──────┐
            │             │
            ▼             ▼
   ┌────────────────┐ ┌───────────────┐
   │ Intentional?   │ │ Regression?   │
   │ Yes → Update   │ │ No → Fix Code │
   │ Baseline       │ └───────────────┘
   └────────────────┘
```

---

## Related Documentation

- [E2E Testing Guide](./E2E_TESTING_GUIDE.md)
- [ADR-0013: Autonomous Validation Framework](../architecture/decisions/0013-autonomous-validation-framework.md)
- [Playwright Screenshot Testing Docs](https://playwright.dev/docs/test-snapshots)

---

**Questions?** See project CLAUDE.md or file an issue on GitHub.
