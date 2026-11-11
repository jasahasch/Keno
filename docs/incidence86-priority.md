# Priority 86-incidence continuation

One bounded public-source pass completed in **590.807 seconds**, under the 900-second cap with validation and saving time reserved. All 13 twice-resource-limited keys were attempted first in canonical order with 35 seconds each (previous continuation budget: 12 seconds). All 215 remaining keys then received one second each, ordered by largest component size, maximum cycle rank, and canonical key. No keys were left unattempted.

| Disposition | Before | After |
| --- | ---: | ---: |
| certified-no-improvement | 497 | 503 |
| open-resource-limit | 228 | 222 |

All 497 inherited exclusions are unchanged. Six priority keys gained exclusions; seven remain open. All 215 secondary keys remain open. Of the current resource limits, 211 stopped during initial bounding and 11 during packed replay. No strict improvement or explicit improving witness was found or claimed. Global optimality remains open.

## Priority results

Every priority key used conditional tree/cycle envelopes, shared successful in-memory component/tail caches, and packed-integer replay. The same source bound retains every feasible size allocation, sizes 2–10, exactly twenty distinct cards, uniform 20-of-80 draws, and the existing support-splitting scope. Higher-rank secondary keys use full component profiles. Every accepted floor covers all feasible allocations and agrees with packed replay in both value and combined feasible incidence-total count. A partial initial bound or incomplete replay is never accepted. The minimum new floor is **5,638,755,188,736**, above Record A.

The earlier stage column comes from the merged continuation. Its 13 priority entries record 12 initial-bound limits and one packed-replay limit. The original first-pass ledger has empty evidence for resource limits and does not record their stopping stage; that historical distinction cannot be reconstructed from these inputs.

| Order | Canonical key | Earlier stage | New verified floor / open | Feasible totals |
| --- | --- | --- | ---: | ---: |
| 1 | `[[0,1],[0,1],[1,5],[2,5],[3,5],[4,5]]` | packed-replay | 5638755188736 | 44 |
| 2 | `[[0,1],[0,3],[1,3],[2,3],[3,5],[4,5]]` | initial | 7304934064128 | 45 |
| 3 | `[[0,1],[0,5],[1,5],[2,3,5],[4,5]]` | initial | 8559601385472 | 45 |
| 4 | `[[0,1],[0,5],[1,5],[2,5],[3,5],[4,5]]` | initial | open | — |
| 5 | `[[0,1],[1,6],[2,6],[3,6],[4,6],[5,6]]` | initial | open | — |
| 6 | `[[0,1],[2,7],[3,7],[4,7],[5,7],[6,7]]` | initial | open | — |
| 7 | `[[0,1,5],[1,2],[2,5],[3,5],[4,5]]` | initial | 8601477316608 | 45 |
| 8 | `[[0,1,5],[1,5],[2,3,5],[4,5]]` | initial | 10488712790016 | 45 |
| 9 | `[[0,1,5],[1,5],[2,5],[3,5],[4,5]]` | initial | open | — |
| 10 | `[[0,1,6],[2,6],[3,6],[4,6],[5,6]]` | initial | open | — |
| 11 | `[[0,2,5],[1,2,5],[3,5],[4,5]]` | initial | 9644349063168 | 45 |
| 12 | `[[0,5],[0,5],[1,5],[2,5],[3,5],[4,5]]` | initial | open | — |
| 13 | `[[0,6],[1,6],[2,6],[3,6],[4,6],[5,6]]` | initial | open | — |

## Inputs and deliverables

The separate [delta ledger](incidence86-priority.json) overlays its attempts on the previous continuation, which overlays the original 725-row ledger. Untouched entries inherit their previous disposition. Every attempted key, method, budget, stage, elapsed time and accepted floor is retained. The `unattempted` list is empty. A scratch JSONL journal was flushed after every attempt and compared exactly with the final ledger.

Original ledger SHA-256: `cab25cc2cf66a0b9b11b4592a28665ba8d4015e9dde46cd0c15b854ca4dab15b`.
Previous continuation SHA-256: `6544c9220b10e3c4315d7f201b1b18882125ab020840f251d3135c6d83661215`.
New ledger SHA-256: `07e84bccf4ac12772ad455c5512c105e8f43ab92226d437c17762f12110c7efc`.
Runner SHA-256: `ada8b82b75cf8e95d63dfff3c5e17e24ff3daa9e24291aedb6d93742ab7f71dc`.

New source is [tools/incidence86_priority.py](../tools/incidence86_priority.py). The three new project files are the runner, this report and the separate ledger. No publication allowlist or historical artifact was changed.

## Actual validation

- Record A reproduced 1,099,511,627,776 zero-payout draws out of 3,535,316,142,212,174,320. Legacy deletion and frontier polynomials agreed. Frozen Pay Table 4 SHA-256 matched `d12c1a7588b93d8e2fff3061d4c89b8b3a7c9fd6d9b386460952f2b05fe8cbe1`.
- All 16 core regression tests passed. The deterministic smoke independently passed the same 16 tests, replayed all 595 legal layouts per synthetic objective, and checked SQLite integrity and foreign keys with temporary fixture cleanup.
- Both geometry generators independently regenerated exactly the original 725 canonical keys. Applying all 291 previous continuation entries reconciled the requested 497/228 merged checkpoint before attempting any key.
- A separate post-run audit checked input digests, unique attempt keys, exact first/second group ordering, all budgets, prior stopping stages, acceptance floors/evidence, exact before/after counts, unchanged inherited exclusions, empty unattempted list and journal equality.
- Disabled assertions, zero total budget and a total budget above 840 seconds were refused before enumeration. Only one continuation computation was run.
- All 93 pre-existing public files matched their pre-computation content hashes after execution. Git status and commit cannot be checked because `/work/.git` is a masked empty file. This content comparison is not a trusted host attestation.

## Provenance limits and reproduction

No applicable AGENTS.md was found in accessible project/ancestor locations. Required project documentation and the available `keno-start` skill were read and applied. The namespace hostname is `SynFart`; trusted physical host identity, supervisor provenance and correspondence to requested commit `07571ac` remain unverified because Git metadata is masked. These limits did not prevent substantive public-source computation. Private research and private-fixture suites were unavailable and not accessed. No GitHub operation, push, merge, permanent-checkout change, local-main change or historical paytable/output change was performed.

```bash
PYTHONDONTWRITEBYTECODE=1 timeout 740 python3 tools/incidence86_priority.py --seconds 700 --retry-seconds 35 --unvisited-seconds 1 > /tmp/incidence86-priority.json 2> /tmp/incidence86-priority-attempts.jsonl
```

Timing-dependent outcomes may vary. Publication requires separate owner review.
