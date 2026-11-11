# Issue 14 source-only result

The priority exclusion reproduced exactly: **8,237,478,838,272 zero-payout draws
across 45 feasible combined incidence totals**. The canonical geometry is
`[[0,1],[0,1],[0,2],[1,3],[2,3],[4,5]]`; the repeated edge is preserved as two
distinct shared numbers. Initial ordinary and packed full-profile computations
agreed, taking 4.924 seconds together under a 30-second cap. A fresh Python
process independently rebuilt both paths and agreed in 4.923 seconds. The
priority reproduction was fsynced before replay, and its replay and disposition
were persisted before any secondary attempt. See [priority result](priority-result.json)
and [replay audit](replay-audit.json).

The original census and all four additive ledgers reconcile by exact canonical
key, prior status, and source digest. Before: **575 exclusions + 150 open = 725**.
After: **576 exclusions + 149 open = 725**. All 150 open keys were attempted;
there are zero unattempted keys. The other 149 keys timed out at ordinary
full-profile construction under deterministic 1.5-second budgets and remain
open. Secondary ordering is latest packed-replay stops first, then increasing
largest component size, maximum component cycle rank, and canonical key.
No incomplete computation was promoted. No improving legal witness was found;
global optimality remains open.

The [additive ledger](ledger.json), [key lists](keys.json), and
[reconciliation](reconciliation.json) retain exact inputs and outcomes.
[attempts.txt](attempts.txt) contains the original JSON Lines bytes under a publishable filename. The computation journal was append-only, flushed and fsynced;
its candidate status precedes separate replay. `attempts.json` and `ledger.json`
contain final dispositions after replay. Every timeout records its stage.
[Method](method.md) explains the unchanged full component-profile envelope and
carry-safe 81-bit packed arithmetic. The frozen model remains uniform 20-of-80,
20 distinct cards of sizes 2–10, arbitrary overlaps, and Spot Keno Pay Table 4.
The paytable SHA-256 is
`d12c1a7588b93d8e2fff3061d4c89b8b3a7c9fd6d9b386460952f2b05fe8cbe1`.

## Actual validation

The deterministic [smoke](smoke.json) passed all 16 core regressions and
independently replayed all 595 synthetic layouts under each objective, with
maxima 20/20 for any payout and 8/20 for net profit. SQLite integrity passed,
foreign-key errors were zero, and the temporary database was removed.
[Record A](record-a.json) was also verified separately with both legacy exact
counters: 1,099,511,627,776 zero draws of 3,535,316,142,212,174,320 total.
[Geometry validation](geometry-validation.json) reproduced all 725 canonical
keys using both independent generators, with the original 167-key partition.
[Final audit](audit.json) checks ordering, source hashes, reconciliation,
journal/final-record consistency, replay agreement, key lists and preservation.
The two new Python tools passed AST parsing. Private-fixture suites were not run.

## Execution, provenance and limits

The supervisor attested SynFart, public source HEAD
`6dc6ac5a7d60db0aa9948f1b3cc99b03d66052c0`, Issue 14 digest
`c7547512fbfb7e4f41faf326c6a9881bad0b17a3a8d1b81ba6a624ac2615f9f2`,
and exact owner codex approval comment `6806837001`. The namespace hostname
also returned SynFart. Git metadata is masked, so HEAD and approval rely on that
trusted attestation. No GitHub contact occurred. Python is 3.12.3; assertions
were enabled and computational Python processes disabled bytecode writes.
The ledger records source and tool SHA-256 hashes; the preservation baseline
also covers all pre-existing sources, including imported historical modules.

Applicable instructions, README files, mathematical, workspace, publication,
bridge, framework governance and architecture documents were read. No applicable
AGENTS.md was found. The available keno-start skill was read and applied.
`rg` was unavailable; standard filesystem tools provided the fallback.

The bounded pass took 253.054 seconds including separate arithmetic replay and
per-attempt persistence. Its local pass cap was 480 seconds; initial computation
was required to finish within 600 seconds, with a 900-second supervised outer
cap including audit and evidence. Priority and replay each received 30 seconds;
secondary initial attempts received 1.5 seconds, and a successful secondary
would have received a separate replay of up to 10 seconds. No secondary reached
that stage. Timing evidence distinguishes the first observable in-namespace
clock from the externally enforced launch deadline; no unobserved launch time
is invented. Audit time was not used for additional search.

All **137 pre-run inventoried files remain byte-identical**. Earlier accepted
files, historical outputs, paytables and existing edits were preserved. Private
research was inaccessible. No main change, push, merge or PR publication was
performed. New source and evidence are for review. The remaining mathematical
bottleneck is ordinary full-profile construction over card-size allocations.

Evidence persistence and hashes were checked inside isolation. The required
trusted-host verification after the run cannot be performed from this namespace
and remains a supervisor follow-up. This report makes no claim that it happened.

The source-review copy retains the execution tool hashes in the ledger. The review tool hashes cover the journal filename and checker updates. The original run artifacts remain available in the retained worktree.
