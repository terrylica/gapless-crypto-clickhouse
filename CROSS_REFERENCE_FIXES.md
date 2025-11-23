# Cross-Reference Fixes

This document provides exact fixes for the 3 broken cross-references found in the audit.

## Fix #1: docs/README.md (Line 20)

**Current (Broken)**:

```markdown
- [`PYPI_PUBLISHING_CONFIGURATION.yaml`](PYPI_PUBLISHING_CONFIGURATION.yaml) - PyPI publishing configuration
```

**Fix Option A** (Remove reference - file doesn't exist):

```markdown
<!-- Removed: PYPI_PUBLISHING_CONFIGURATION.yaml no longer exists -->
```

**Fix Option B** (Update reference if file exists elsewhere):
Check if the file exists in the repo root or create it, then update path accordingly.

---

## Fix #2: docs/diagrams/README.md (Line 116)

**Current (Broken)**:

```markdown
See the complete flow in [01-collection-pipeline.mmd](./docs/diagrams/01-collection-pipeline.mmd)
```

**Fixed**:

```markdown
See the complete flow in [01-collection-pipeline.mmd](./01-collection-pipeline.mmd)
```

**Explanation**: The reference is already in `docs/diagrams/` directory, so it should be `./01-collection-pipeline.mmd` not `./docs/diagrams/01-collection-pipeline.mmd` (which creates a double-nested path).

---

## Fix #3: docs/diagrams/README.md (Line 146)

**Current (Broken)**:

```markdown
![Collection Pipeline](./assets/collection-pipeline.png)
```

**Fix Option A** (Remove example - assets don't exist):

```markdown
<!-- Example image embedding (requires exporting diagram to PNG first):
![Collection Pipeline](./assets/collection-pipeline.png)
-->
```

**Fix Option B** (Create assets directory):

1. Create `docs/diagrams/assets/` directory
2. Export Mermaid diagrams to PNG files
3. Keep the reference as-is

**Recommendation**: Use Fix Option A (comment out) since this appears to be example documentation showing how to embed exported images.

---

## Verification Commands

After applying fixes, verify with:

```bash
# Re-run the validation script
python3 validate_references.py

# Expected output: 0 broken references
```

---

## Summary

- **Total Fixes Required**: 3
- **Estimated Time**: 5 minutes
- **Files to Edit**: 2 (`docs/README.md`, `docs/diagrams/README.md`)
- **Risk Level**: Low (documentation only)
