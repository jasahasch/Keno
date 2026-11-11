# 86-incidence supervised source pass

This source pass enumerates full-support Scenario 1 geometries, and applies
bounded extensions of the published Phase 4 coefficient floors. It does not
claim complete 86-incidence certification or global optimality.

## Observed results (2026-11-11 UTC)

The supervised source work finished within the requested 900-second cap.
The final bound command used a 420-second internal budget, a four-second
per-geometry budget and a 460-second external timeout; it exited zero before
the internal budget expired. The retained [ledger](incidence86-coverage.json)
contains all **725** canonical keys:

| Disposition | Keys |
| --- | ---: |
| Certified no improvement, with packed replay | 434 |
| Open: branch resource limit | 38 |
| Open: outside selected width/rank scope | 253 |

The minimum accepted floor is **2,841,120,866,304** zero-payout draws, above
Record A's **1,099,511,627,776**. Of the 434 accepted bounds, 375 use conditional
tree/cycle messages. No strict improvement was found or claimed; no new legal
witness is claimed. There are **291 unresolved geometry keys**, each explicitly
listed in the ledger with an `open-` status. The 38 timed branches may have
stopped during initial computation or replay; neither case accepts a bound.

Actual checks:

- `verify-record-a`: both independent legacy counters agree on
  `1099511627776 / 3535316142212174320` zero draws, and the frozen table SHA-256
  matches `d12c1a7588b93d8e2fff3061d4c89b8b3a7c9fd6d9b386460952f2b05fe8cbe1`.
- `tools/check_phase4.py`: 167 geometries, 41 inherited and 126 new branches;
  the independently evaluated witness has zero count `5325759447040`. This is
  historical geometry/link reconciliation, not historical bound arithmetic replay.
- `python3 -m unittest -v multi_keno.test_platform unrestricted_resolution.test_resolution`:
  all 16 tests passed.
- `tools/keno_bridge/smoke.py`: all 16 core tests passed again; 595 layouts per
  synthetic objective independently replayed, maxima 20/20 and 8/20, database
  integrity `ok`, no foreign-key errors, temporary fixture removed.
- Additional direct checks: all 24 card relabelings of a four-card test key
  agree; small tree and single-cycle message floors lie below directly
  enumerated profile floors in both arithmetic representations; disabled
  assertions and nonpositive time budgets are refused before enumeration.
- The final source version independently regenerated the 725-key census. A
  separate ledger reconciliation checked unique keys, exact census agreement,
  excess six, feasible size ranges, dispositions and accepted evidence. All 179
  bounds from the earlier narrower pass retain exactly the same values.

A preservation hash comparison found all 89 baseline files unchanged. That
comparison baseline was captured after the initial read-only baseline checks;
it is not a host-level pre-run attestation. The only new files are
`tools/incidence86.py`, this report and `docs/incidence86-coverage.json`.
No historical outputs or paytables were edited. No GitHub operation, push,
merge, issue closure, or publication was performed. `keno-start` was available,
read and applied. Private historical fixtures were unavailable and not used.

Host prerequisites remain outside the agent's evidence: actual source commit,
SynFart identity, exact-digest approval and supervisor provenance must be
checked in the trusted host report. Masked Git metadata prevents an in-sandbox
commit attestation; it did not prevent substantive public-source enumeration.

## Reproduction

Run with Python assertions enabled and bytecode disabled, from the source root:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m multi_keno.platform verify-record-a
PYTHONDONTWRITEBYTECODE=1 python3 tools/check_phase4.py
PYTHONDONTWRITEBYTECODE=1 python3 tools/keno_bridge/smoke.py
PYTHONDONTWRITEBYTECODE=1 timeout 460 python3 tools/incidence86.py --width 3 --messages-width 7 --seconds 420 --branch-seconds 4 > /tmp/incidence86.json
```

The last command recomputes both enumerations and all requested bounds; it
does not trust an existing coverage file. Redirect scratch output outside the
checkout. The ledger records every canonical shape, its component incidence
graph cycle ranks, its disposition, and the evidence for each accepted bound.
Open shapes are exactly the rows whose status starts with `open-`.
Timing-dependent dispositions can differ on another machine. A branch timer
covers both the initial bound and its replay; expiration discards any partial
result and records `open-resource-limit`. Exhaustion of the total budget leaves
eligible unattempted rows `open-budget`; width/rank exclusions stay
`open-unvisited`. The external timeout also caps enumeration, which must finish
before a ledger can be emitted.

The source commit cannot be read inside this sandbox: the bridge deliberately
masks `.git`. The requested public base is `5d38348` and the requested external
supervisor revision is `4fc699f`; neither is independently attested by the
agent. The trusted host's retained report must supply the actual source commit,
host identity, approval digest and supervisor revision. No GitHub request or
host approval operation is performed by this source tool.

## Enumeration and smaller supports

A shared physical number is represented by the set of cards containing it.
Singleton memberships are implicit. At support 80, incidence 86 leaves excess
six, so the sum of shared-number degrees minus one is six. Keys identify
multihypergraphs under card permutation and shared-number permutation; repeated
edges represent distinct numbers with the same owners.

The first enumeration lifts the verified 167-key 85-incidence set: add a
degree-two number on every pair of old or new cards, or add an old or new card
to an existing shared number. The inverse operation removes a degree-two
number or removes one owner of a higher-degree number, so every excess-six
geometry has a predecessor. The second enumeration starts from every integer
partition of six and attaches each number of degree one more than its part
to every possible subset of existing cards plus new cards. Both routes use
the historical canonicalizer, and their complete key sets must agree exactly.
The routes agree on **725** keys.

For support below 80, choose a shared number `v`, one containing card `C`, and
an unused number `x`; replace `v` by `x` only in `C`. Sizes and incidences stay
fixed, support increases by one, and `C` stays distinct because only it contains
`x`. Conditional on the draw outside `{v,x}`, only the case of selecting exactly
one of these two numbers changes the zero count. Let `F,G` indicate that all
other cards fail to pay without/with `v`, and `c0,c1` indicate that `C` fails
without/with its replaced number. The frozen table's zero-hit sets are initial
intervals, hence `F >= G` and `c0 >= c1`. The old zero indicators sum to
`F*c0 + G*c1`, whereas the split sum is `F*c1 + G*c0`. Their difference is
`(F-G)*(c0-c1) >= 0`. Neither/both-selected cases are unchanged. Uniform fixed
draws give equal weight to the two single-selection cases. Repeating gives
support 80 with no larger zero count. Thus a full-support lower bound also
covers smaller supports mapping into its geometry. Open target geometries
prevent a complete smaller-support exclusion.

## Bounds and limitations

For each connected component, profiles range over every card size from
`max(2,shared_degree)` through 10. At each component incidence total, take
coefficientwise minima of zero-subset polynomials, then convolve floors and
minimize again at each combined incidence total. Residual disjoint cards range
over every nondecreasing size allocation from 2 through 10 with the required
remaining incidence total `86 - component_total`. This includes all feasible
legal allocations; relaxing distinctness can only weaken a lower bound.

Small trees and single-cycle components use the existing Phase 4 conditional
messages: cycle rank is measured in the bipartite card/number incidence graph.
Every accepted bound is recomputed using packed-integer polynomial arithmetic;
the residual tails also use the independent packed computation. These replays
share the frozen model and structural decomposition. They do not constitute
independent proofs of historical certificates. Bounds below Record A remain
open; no candidate witness is inferred from an envelope floor.

Only new files under reviewed `tools/` and `docs/` paths are used. Historical
outputs, paytables, certificates, checkpoints and private databases are not
written. Publication is a separate owner review.
