# Scenario 1: seven deferred incidence-86 geometries excluded

The final additive ledger certifies all seven deferred priority keys. All 150 other
open keys were attempted and remain open. Global optimality remains open.

| Status | Before | After |
| --- | ---: | ---: |
| certified-no-improvement | 568 | 575 |
| open-resource-limit | 157 | 150 |
| total canonical geometries | 725 | 725 |

There are 157 attempted keys, seven newly certified keys, 150 still-open keys,
and zero unattempted keys. Of the secondary cases, 149 stopped in ordinary
bounding and one stopped in packed replay. None is certified on partial work.
No improving witness was found or claimed.

| Priority key, canonical order | Exact lower bound | Feasible combined totals |
| --- | ---: | ---: |
| `[[0,1],[0,5],[1,5],[2,5],[3,5],[4,5]]` | 6682432241664 | 44 |
| `[[0,1],[1,6],[2,6],[3,6],[4,6],[5,6]]` | 7207894646784 | 44 |
| `[[0,1],[2,7],[3,7],[4,7],[5,7],[6,7]]` | 7289431916544 | 44 |
| `[[0,1,5],[1,5],[2,5],[3,5],[4,5]]` | 8092121038848 | 44 |
| `[[0,1,6],[2,6],[3,6],[4,6],[5,6]]` | 8744872181760 | 44 |
| `[[0,5],[0,5],[1,5],[2,5],[3,5],[4,5]]` | 4855997399040 | 43 |
| `[[0,6],[1,6],[2,6],[3,6],[4,6],[5,6]]` | 5014542090240 | 43 |

Each lower bound exceeds Record A's 1099511627776. Both independent arithmetic
representations agree on the bound and feasible-total count. See the separate
[arithmetic replay](arithmetic-replay.json), [strict replay](strict-arithmetic-replay.json),
[final audit](audit.json), [attempt journal](attempts.txt), [key lists](keys.json),
and [ledger](ledger.json). Original source hashes and all three additive-ledger
hashes are retained in the ledger. The two independent geometry generators
reproduced exactly the original 725 canonical keys; all 568 inherited exclusions
are preserved. The initial census and each overlay were reconciled by exact key,
prior status, and source digest.

The new method uses rooted attachment signatures, multiset size allocations, and
conditional hit-count polynomial products reused across hub sizes. The
[mathematical explanation](method.md) describes exhaustive coverage and shared-number
counting. The frozen uniform 20-of-80 model, twenty distinct cards of sizes 2–10,
and Pay Table 4 remain unchanged. The paytable fingerprint is
`d12c1a7588b93d8e2fff3061d4c89b8b3a7c9fd6d9b386460952f2b05fe8cbe1`.

## Validation and correction

An extra structural check rejected the initial implementation's numerical-only
grouping, because equal conditional floors can hide different rooted attachments.
These initial results are diagnostic only. The strict implementation adds full
rooted signatures, including cut-card and cut-number restrictions. Every final
priority result was recomputed in ordinary and packed arithmetic using the strict
implementation. The original diagnostic journal, ledger, arithmetic, and validation
failure remain separate files. The finalized journal records strict results and
also records each diagnostic duration and disposition. The finalizer writes
atomically with fsync; the original execution journal was flushed after every
attempt, and every strict result was persisted immediately.

The final strict test passed six direct-allocation fixtures in one unittest:
an edge, two pair-edge stars, a triangle, a triangle with a pendant edge, and a
hyperedge tree. It checks every feasible size total and all polynomial coefficients
against direct size/shared-state enumeration, and matches packed arithmetic.
A preliminary test mistakenly required exact envelope equality on the hyperedge;
it was corrected to the lower-bound contract, with equality still required on
simple pair-edge stars. Final test output is retained in [grouped-tests.txt](grouped-tests.txt).
The isolated deterministic smoke passed all 16 core regressions, replayed all
595 legal layouts for each synthetic objective, checked SQLite integrity and
foreign keys, and removed its temporary database. See [smoke.json](smoke.json)
and [core-tests.txt](core-tests.txt). [Record A](record-a.json) reproduced both
legacy counters and the frozen paytable binding. Source syntax and import of the
strict production entry point were checked without starting another census run.

## Execution and limits

The trusted supervisor attested SynFart, public source commit
`90bcc1206db5a4ae77d75a4a013277fa910543e8`, issue 12 exact digest
`08413633fb2a01415425e1e16577765dd88f39444009b2d0829bcd0344198966`,
and owner approval comment 6805876841 in codex mode. This report relies on that
attestation; Git metadata is deliberately masked. No GitHub contact occurred.
The run stayed in the disposable public-source worktree. No applicable AGENTS.md
was found. Project governance, mathematical, publication, architecture and workspace
documentation were read; the available keno-start skill was applied.

The bounded census pass took 349.285 seconds, at 0.449 attempts/second. Its configured cap was 550 seconds; the initial priority cap was 315 seconds, with 45 seconds per priority key and 1.5 seconds per secondary key. Strict replay ran concurrently with the secondary phase, under a 180-second cap and 45 seconds per key. Actual priority work across diagnostic and strict computations was 204.747 seconds. Audit timing and the conservative aggregate are recorded in run-timing.json. The first separate audit reached its 100-second cap after five successful replays; the remaining two were replayed in a bounded continuation, preserving audit-partial.json. Final audit completeness is checked before accepting this report.

The main remaining bottleneck is ordinary component-profile/conditional-envelope
construction over size allocations; one case instead needs more packed replay
time. Larger budgets or further attachment-aware reductions can target those
150 keys. Resource deferrals do not imply mathematical exclusions.

All 103 inventoried pre-existing public files have unchanged SHA-256 hashes;
[preservation evidence](preservation.json) retains the baseline. Historical
outputs, paytables, local main and existing edits were not modified. Private
research was unavailable and not accessed. Private-fixture suites were not run.
The new evidence and source are for review only: nothing was pushed or merged.
Trusted-host verification of the persisted files must occur after isolated
execution; it cannot be performed from this namespace.

To reproduce the pass in a disposable checkout, use a new evidence directory.

```sh
PYTHONDONTWRITEBYTECODE=1 timeout 430 python3 tools/incidence86_run_strict.py --output-dir docs/incidence86-scenario1-rerun
PYTHONDONTWRITEBYTECODE=1 python3 tools/check_incidence86_scenario1.py --evidence-dir docs/incidence86-scenario1-rerun --replay-seconds 150
```

The runner caps computation at 400 seconds and refuses existing directories.
The checker has a separate replay budget and exits with failure if any accepted
exclusion remains unreplayed. The default evidence path still supports read-only
verification of the retained artifacts. The original runner, replay, and
finalizer preserve the diagnostic and correction path used for this session.
