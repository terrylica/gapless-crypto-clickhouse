# ADR-0052: Pin the semantic-release toolchain versions in CI

## Status

Accepted

## Context

`.github/workflows/release.yml` installed its release tooling with an unpinned `npm install --global`:

```yaml
npm install --global \
semantic-release \
@semantic-release/changelog \
... \
conventional-changelog-conventionalcommits
```

Every release therefore resolved whatever npm had published that day. On 2026-08-25 that broke the repository's ability to release at all:

- `conventional-changelog-conventionalcommits` resolved to **10.4.0**, a major that refuses to render unless `conventional-changelog-writer@9+` is loaded.
- `@semantic-release/release-notes-generator@14.1.1` nests `conventional-changelog-writer@8.4.0`.
- `.releaserc.json` requires `"preset": "conventionalcommits"` in **both** `commit-analyzer` and `release-notes-generator`, so the preset is always loaded.

Every push to `main` died with:

```
Missing helper: "conventional-changelog-conventionalcommits requires
conventional-changelog-writer@9 or newer (conventional-changelog@8 or newer). ..."
```

### Why this was invisible locally

The failure lives in GitHub Actions. The local `npm run release:dry` script resolves a _different_ dependency tree (a local/bun-global install that still had a compatible preset), so it kept reporting a correct `17.5.0` render while CI was failing. **A local green gate over a different dependency tree is not evidence about CI.** This is the same shape as the "green signal is a proxy that holds only under unstated assumptions" class of defect.

### SLO Focus

- **Correctness**: a release either happens or fails loudly; it must not depend on the publication schedule of a transitive package.
- **Reproducibility**: the same commit must produce the same release tooling next month.
- **Observability**: the rationale must live where the next person edits the list.

## Decision

1. **Pin every package** in the CI install list to an exact version.
2. **Pin the preset to `conventional-changelog-conventionalcommits@9.3.1`** — the newest major that renders against the `conventional-changelog-writer@8.x` that `@semantic-release/release-notes-generator@14.1.1` nests.
3. **Do NOT pin `conventional-changelog-writer` at the top level.** This was tested and deliberately omitted — see below.
4. **Record the rationale inline in the workflow**, including the replay command used to verify it, so a future bump is verifiable without rediscovering this ADR.

## How this was verified

Diagnosed by reproduction, not by reading version ranges. The install list was replayed with `npm install --global --prefix <tmp>` — flat resolution, exactly how CI resolves, as opposed to `--prefix` alone which nests and gives different answers — and run against this repo's real `.releaserc.json`:

| Case                                  | Preset | Result                                  |
| ------------------------------------- | ------ | --------------------------------------- |
| Current workflow, verbatim (unpinned) | 10.4.0 | ❌ reproduced the CI error verbatim     |
| Pinned list (this ADR)                | 9.3.1  | ✅ `The next release version is 17.5.0` |

**Negative control that changed the decision.** A top-level `conventional-changelog-writer@7.0.1` pin was forced alongside preset 9.3.1 — and the run _still succeeded_, because the generator's **nested** copy is what actually resolves. Pinning the writer at the top level would therefore have been a pin that looks protective and does nothing. It was dropped on that evidence.

**A note on how the diagnosis nearly went wrong.** An early pass grepped the workflow with a pattern that did not match the `conventional-changelog-conventionalcommits` line, concluded the preset was _undeclared_, and "reproduced" a `Cannot find module` failure — a real error, but of a straw-man configuration that never existed in this repo. `git log -S` showed the preset line had been present since the initial release commit. **Confirm the input you are reproducing is the real one before trusting the reproduction.**

## Consequences

**Positive**

- Releases are reproducible and no longer break from third-party publishing activity.
- The failure mode, the replay command, and the rejected writer pin are documented at the point of edit.

**Negative**

- Pins go stale; security and feature updates now require a deliberate bump.
- A bump must move `@semantic-release/release-notes-generator` and the preset **together**, since their compatibility runs through `conventional-changelog-writer`.

**Verification for any future bump**

```bash
npm install --global --prefix /tmp/sr-check <the new pinned list>
GH_TOKEN=<token> /tmp/sr-check/bin/semantic-release --dry-run --no-ci
```

Expect a `The next release version is …` line. Anything else means the set is incompatible.

## Related

- ADR-0027 — local-only PyPI publishing. CI cuts the tag and GitHub Release; the PyPI upload is a separate local step. Both halves must succeed for a version to exist for users, and this ADR restores the first half.
