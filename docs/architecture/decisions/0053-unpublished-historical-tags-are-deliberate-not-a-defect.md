<!--
# SSoT-OK

version-guard escape, deliberate. This ADR's entire subject is WHICH historical versions were published and which were not, and its evidence is the specific tag identities and their timestamps. The version strings here are historical FACTS about the git tag record, not a declaration of the current version -- that remains solely pyproject.toml. Replacing them with placeholders would delete the evidence and leave an unfalsifiable assertion.
-->

# ADR-0053: The 63 unpublished historical tags are deliberate, not a defect

## Status

Accepted

## Context

An audit on 2026-08-25 found that **63 of 105** git tags have no artifact on PyPI. The package name is `gapless-crypto-clickhouse` at every tag checked, so this is not a rename boundary. The current `17.x` line is complete.

Read naively — "63 tags shipped no artifact" — this looks like 63 missed publishes, and it is a natural conclusion under ADR-0027, which makes publishing a deliberate **local** step that a human can forget. That framing was assumed at first, and it was wrong.

### The measurement that settles it

The discriminating question is not _how many_ tags lack an artifact, but **how long each tag was the newest tag** — i.e. how long a user could have installed it as the current version. Computing that for every tag separates the two populations cleanly:

| population            | n   | median lifetime     | max lifetime       | stood > 24 h |
| --------------------- | --- | ------------------- | ------------------ | ------------ |
| **missing** from PyPI | 63  | **0.12 h** (~7 min) | **21.85 h**        | **0**        |
| **present** on PyPI   | 41  | 1.18 h              | 3066 h (~128 days) | 7            |

Every one of the 63 missing versions was superseded within **22 hours**, and 48 of them within **one hour**. Not a single one was ever the newest tag for a full day. The published set contains long-lived releases; the unpublished set contains none at all.

That comparison is what makes the conclusion safe. Had both populations looked alike, the explanation would have been dead — the check could have failed and did not.

### The gap shape corroborates it

The 63 fall into **9 contiguous runs**, tracking release bursts rather than scattering randomly. The largest run spans thirty consecutive versions cut across roughly 2.5 days. Independent `git log` spot-checks confirm the timestamps: three sampled unpublished tags were superseded after 31 minutes, the same day, and under two hours respectively.

**These are rapid-iteration tags where only the final tag of each burst was published.** That is correct practice, not an omission.

## Decision

**Do not backfill the 63 historical versions. The question is closed.**

Concretely:

1. A git tag with no PyPI artifact is **not** by itself a defect in this repository, and must not be reported as one.
2. Publishing remains local-only per ADR-0027, and the **current** line must stay complete — the `17.x` line is, and that is the standard to hold.
3. Anyone re-raising this should first re-run the lifetime comparison below. If some future unpublished version has stood as newest for **days**, that one _is_ a missed publish and should be investigated on its own merits.

## Consequences

**Positive**

- Avoids adding 63 permanent, never-current versions to a namespace where **a version can never be re-uploaded or corrected**. The risk is one-directional: leaving them out is reversible, publishing them is not.
- Avoids building 63 old tags whose reproducibility is unknown — an old build that silently embeds today's dependency versions would be permanently wrong on PyPI.
- Stops the finding being rediscovered as a defect on every future audit.

**Negative**

- Installing one of the 63 pinned exactly will always fail. Acceptable: none was ever installable as the current release for more than a day, so no user can have depended on one.
- The tag count and the PyPI version count will permanently disagree. That is now documented rather than surprising.

**Explicitly not done**

Sample-building old tags was planned and then **skipped deliberately**. Once the supersession measurement removed any reason to upload, whether those tags still build became moot. Recorded so a future reader does not mistake the omission for an oversight.

## How to re-derive this

The check is cheap and negative-controllable. For each tag, compute the interval to the next tag; compare the distribution for tags present on PyPI against those absent.

PyPI truth must come from the **simple index**, polled with a retry — never the JSON API, which lags at both the top-level and per-version endpoints and has been observed disagreeing with reality in both directions:

```bash
curl -s -H 'Cache-Control: no-cache' https://pypi.org/simple/gapless-crypto-clickhouse/
```

Negative-control the presence check against a version that cannot exist; a check that never says no is not a check.

## The general lesson

**"Tag exists but no artifact" is not evidence of a missed publish.** A count of gaps is not a finding — a _discriminating comparison_ is. Here the naive count said 63 defects and the measurement said zero, and the difference was one column: how long each version was actually current.

## Related

- ADR-0027 — local-only PyPI publishing. This ADR bounds how its known consequence (skipped publishes) should be interpreted: real for the current line, not retroactively for superseded tags.
- ADR-0052 — pinned semantic-release toolchain, which restored the repo's ability to release at all.
