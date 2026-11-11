# Supervised 86-incidence continuation

The single bounded computation exited zero after **602.693 seconds**, within
the 900-second cap with time reserved for reconciliation and saving. It
attempted all 38 resource-limited keys first, then all 253 unvisited keys.
There are **63 new exclusions** and **228 explicitly open keys**. Global
optimality remains open. No improving witness was produced or claimed.

| Disposition | Baseline | After |
| --- | ---: | ---: |
| certified-no-improvement | 434 | 497 |
| open-resource-limit | 38 | 228 |
| open-unvisited | 253 | 0 |

The first group yielded 25 exclusions and 13 timeouts; the second yielded
38 exclusions and 215 timeouts. Of the 228 timeouts, 210 stopped during the
initial bound and 18 during packed replay. Neither accepts partial results.
All 434 original accepted entries are inherited without alteration.

## Evidence and provenance

The separate [continuation ledger](incidence86-continuation.json) records
each canonical key, prior disposition, method, allotted budget, elapsed time,
stopping stage, and result. It is a delta: overlay its attempts on the baseline
rows; keys without attempts inherit their baseline results. Baseline accepted
rows are never retried. Its baseline binding is SHA-256
`cab25cc2cf66a0b9b11b4592a28665ba8d4015e9dde46cd0c15b854ca4dab15b`.
The requested merged baseline is `3a859fa`; actual HEAD cannot be attested
because `/work/.git` is masked to an empty file (`git rev-parse HEAD` fails).
The namespace hostname reports `SynFart`; trusted host/supervisor provenance
and correspondence of these bytes to that commit require external review.
No GitHub access was attempted to resolve this limitation.

Both census generators independently regenerated exactly 725 keys and agreed
with the complete frozen ledger. The model remains exactly 20 distinct cards,
sizes 2–10, with a uniform 20-of-80 draw. Frozen Pay Table 4 SHA-256 is
`d12c1a7588b93d8e2fff3061d4c89b8b3a7c9fd6d9b386460952f2b05fe8cbe1`.

The [runner](../tools/incidence86_retry.py) reuses the existing bound code
and its successful in-memory component/tail caches. It uses conditional
tree/cycle messages for rank at most one and full component profile envelopes
otherwise. It does not narrow legal card-size allocations. Every new accepted
bound covers all feasible allocations and agrees in value and combined-total
count with packed-integer replay. The lowest new accepted bound is
4,776,003,633,152, above Record A. These are envelope exclusions, not explicit
layout evaluations. No strict improvement requiring witness reproduction arose.

Runner SHA-256:
`a70f7de60c00940c41c160310c87798076f3a444899fcfe3fdc086fb10e60097`.
Continuation ledger SHA-256:
`6544c9220b10e3c4315d7f201b1b18882125ab020840f251d3135c6d83661215`.

## Actual checks and reproduction

From the source root with Python assertions enabled:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m multi_keno.platform verify-record-a
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest -v multi_keno.test_platform unrestricted_resolution.test_resolution
PYTHONDONTWRITEBYTECODE=1 python3 tools/keno_bridge/smoke.py
PYTHONDONTWRITEBYTECODE=1 timeout 800 python3 tools/incidence86_retry.py --seconds 760 --retry-seconds 12 --unvisited-seconds 1 > /tmp/incidence86-continuation.json 2> /tmp/incidence86-attempts.jsonl
```

Record A reproduced **1,099,511,627,776** zero-payout draws out of
3,535,316,142,212,174,320, with both legacy counters agreeing and the table
hash matching. All **16 core tests passed**. The deterministic source smoke
passed its own 16-test execution, independently replayed all 595 layouts per
synthetic objective, checked expected maxima 20/20 and 8/20, checked SQLite
integrity and foreign keys, and removed its temporary database.
Disabled assertions, zero total budget, and a total budget above 840 seconds
were each refused before enumeration.

A separate post-run audit checked unique attempt keys, complete unresolved-key
coverage, first-group canonical ordering, second-group component-size/rank
ordering, per-case budgets, accepted floors/evidence, baseline hash, and exact
before/after disposition reconciliation. Timing-dependent results can vary on
reproduction. No second continuation computation was run.

All **90 pre-existing public files** matched the pre-computation SHA-256
manifest after the run. This manifest was captured after the initial read-only
checks; it is not a host-level preservation attestation. No applicable
`AGENTS.md` was found in the accessible project or ancestor locations.
The available `keno-start` skill was read and applied. Private research and
private-fixture suites were unavailable and were not accessed. Actual source
commit and trusted supervisor provenance remain unverified. No historical
outputs, frozen paytables, baseline ledger, permanent checkout, local main, or
existing source files were changed; only the three new reviewed-path files
constitute this delivery. No push, merge, publication, or GitHub action occurred.
