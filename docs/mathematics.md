# Mathematical scope and verification

The legacy model uses a uniform 20-number subset of 1–80, exactly twenty distinct cards, allowed sizes 2–10, arbitrary cross-card overlap, and additive hit-count awards. Its frozen input is [Wizard of Odds Spot Keno Pay Table 4](../outputs/keno-expanded-paytables.json), SHA-256 `d12c1a7588b93d8e2fff3061d4c89b8b3a7c9fd6d9b386460952f2b05fe8cbe1`. The published web source is listed in the registry. The table is a research model.

For zero count (Z), the objective is (1-Z/\binom{80}{20}). Record A partitions 1–80 into twenty consecutive quartets. Each pays when at least two numbers hit. Zero payout requires one drawn number per quartet, giving (Z=4^{20}=1,099,511,627,776). Independent deletion–contraction and membership-frontier zero polynomials agree. Run `python3 -m multi_keno.platform verify-record-a`. The exact probability is (220957190168784159/220957258888260895).

The generic engine counts the full gross payout distribution with a membership-region DP and a literal support-subset counter. Both include outside numbers and enforce the common draw size. Each verified evaluation binds the game, rules version, paytable fingerprint, and objective. Any-positive compares gross to zero. Net-profit compares gross strictly to the total wager. Bonus or multiplier mechanics are unsupported.

## Phase 4

The inherited and Phase 4 proofs exclude strict improvement through **85 total card-number incidences**. At 85 incidences and full support, the five excess memberships give **167** shared-number geometries. There are **41** inherited and **126** newly certified branches. The exact minimum is **5,325,759,447,040**, attained by a six-spot and seven-spot sharing five numbers, plus eighteen disjoint quartets. Support splitting maps a lower-support layout to full support without increasing its zero count, and preserves card distinctness. Full-support families with 86–200 incidences outside earlier certified exclusions remain open.

The [coverage ledger](../outputs/phase4-discovery/coverage-final.json) links each geometry to its evidence. For a fixed component incidence total, take the coefficientwise minimum of nonnegative zero-subset polynomials. Convolution preserves the lower bound. Tree messages condition on shared-number hits, while a single cycle can be cut by conditioning on a shared number. A separate packed-integer computation checks the arithmetic. The final lower bounds apply to every legal spot assignment in their branch. Candidate counts and resource deferrals do not certify exclusions.

Run `python3 tools/check_phase4.py` to independently reconstruct the geometry partition, reconcile certificate references, and verify the exact minimizing witness. This checks the archived ledger. To recompute the new certificate arithmetic, use a disposable source copy, keep the inherited inputs, and remove only the copied Phase 4 output checkpoints `certificates85.json`, `tree-certificates85.json`, and `cycle-certificates85.json` before running:

```bash
python3 outputs/phase4-discovery/bound85.py 4
python3 outputs/phase4-discovery/tree85.py
python3 outputs/phase4-discovery/cycle85.py
python3 outputs/phase4-discovery/refine85.py
```

The recomputed files can differ from the archived ledger because the archived pass also retained redundant wider-component bounds. Reconcile new outputs separately. The workspace-only database reconciliation is `python3 outputs/phase4-discovery/audit_phase4.py` and needs the original pre-phase snapshot. No Scenario 1 proof is inherited by a newly registered game.
