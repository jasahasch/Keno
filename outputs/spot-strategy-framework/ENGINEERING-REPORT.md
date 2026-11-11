# Spot Strategy Research Framework — engineering report

## Current status

Implemented a modular working framework in `spot_strategy_framework/`. New archives and evidence are isolated in `outputs/spot-strategy-framework/`. No prior research files were changed.

Implemented configuration, eleven generator families, exact incidence canonicalization with safe fallback, two exact evaluators, optional two-mode C++ acceleration, graph-certificate pruning, separate objective rankings, Pareto frontiers, immutable accepted results, append-only record promotion, source snapshots, deterministic generation, resumable execution, historical adapters and a command-line interface.

Supported configuration covers 2–20 cards, 2–10 spots, selections 1–80, arbitrary overlaps and repeated cards, exact spot lists or ranges, and all four denominations. Machine-profile assumptions are separate from mathematical draw assumptions. The authoritative Scenario 1 file and zero-hit entries remain unchanged; its SHA-256 is `d12c1a7588b93d8e2fff3061d4c89b8b3a7c9fd6d9b386460952f2b05fe8cbe1`.

## Executed verification

All **36 automated tests passed**, without skips. The suite includes 171 closed-form cases spanning every active-card count and spot size, both exact evaluators, all generator families, repeated jackpots, outside-number counting, strict versus inclusive thresholds, graph-pruning soundness, archive corruption detection, failed-verifier protection, interrupted verification recovery, deterministic replay and CLI export. Native region and actual-subset calculations were both executed and agreed with Python on all three complete marginal laws. The test report contains the actual executed test names.

Seven historical layouts were independently reproduced using the new framework. Full gross laws were compared with historical archives where available; the two new evaluators also agreed on complete paying-card and jackpot-count distributions. Independent hypergeometric checks confirmed mean payout, paying frequency and overlap-sensitive variance. Every law totals exactly C(80,20) = 3535316142212174320.

| Historical layout | New framework status |
|---|---|
| Record A, twenty disjoint four-spots | Independently reproduced |
| Older Record B, pair-1 | Independently reproduced and retained |
| blocks-28 | Independently reproduced |
| Newer jackpot-capable record, new-0 | Independently reproduced |
| Balanced six-eight geometry, new-11 | Independently reproduced |
| Fifteen-card profitability benchmark | Independently reproduced |
| Twenty-card profitability benchmark | Independently reproduced |
| Twelve-number recovery geometry, recovery-2 | Evidence-backed historical reference; not freshly evaluated in this default-budget delivery |

The newer B has payout frequency `44191383058175443/44191451777652179` = 99.999844495996%. The older B remains in historical records. Record A remains `220957190168784159/220957258888260895` = 99.999968899199%. The profitability benchmark remains `1689904500136472161/3535316142212174320` = 47.800661444638%. These are achievable records, not proven unrestricted optima. Complete reproduced A–T assignments and exact metrics are in `reproduced-layouts.json` and immutable accepted objects.

A bounded demonstration generated and independently verified 12 mixed overlapping candidates across 2, 3 and 4 active cards, using an explicitly restricted eight-number proposal pool. Its run checkpoint records all seeds, limits and events. This demonstrates the workflow; it is not an unrestricted optimization search and establishes no new scientific record.

## Findings and performance

The reusable improvement is research infrastructure: exact integer distributions, dependency-preserving evaluation, safe result reuse, automatic independent acceptance, objective-specific pruning, persistent provenance and record histories.

Before implementation, the accepted Python payout-only evaluator was benchmarked for three trials per case. The new evaluator was then measured against the identical historical full gross distributions:

| Case | Legacy gross-only median | New three-marginal primary median | Independent verification |
|---|---:|---:|---:|
| Record A | 0.015925 s | 0.028336 s | 0.046402 s |
| Newer B | 0.125481 s | 0.300900 s | 0.383668 s |

The new cold evaluator is slower. It calculates paying-card and jackpot-count laws as well as gross payouts, applies resource accounting, and retains more state. No throughput speedup is claimed. These timings are local measurements, not universal performance guarantees. Exact symmetry elimination and persistent accepted-result caching avoid redundant evaluations; interruption tests verify that completed primary calculations are reused. Larger shared-overlap components remain the main exponential bottleneck. Native structured acceleration is available when its explicit scope and budgets permit it. Benchmark JSON preserves all individual trials and exact verification evidence.

Graph pruning reuses the accepted independent-set/clique certificate. The framework checks every card's pointwise payout implication, reconstructs actual union-graph cost and verifies the rational bound independently. It can eliminate a frequency candidate or one unable to meet a jackpot frequency constraint. It does not use frequency bounds to discard profitability portfolios. The historical theorem remains a mathematical dependency. This delivery does not tighten the open graph-cost >120 families or prove a global frequency ceiling below 100%.

## Documentation compliance and external sources

The attached implementation directive was followed. No applicable AGENTS.md was found. The workspace is not a usable Git checkout; accepted mathematical code is stored in content-addressed source ZIP snapshots with revision manifests. Existing untracked files were treated as protected. An inventory records 40 historical reports/provenance documents; historical evaluators, paytable, accepted checkpoints and certificate evidence were reviewed. This is not a claim that every historical proof/search was rerun.

The initial manifest and final audit agree on all **8,027 pre-existing work/output files**, with zero changes and zero missing files. The archive audit passed for all 19 accepted strategy objects and both source revisions present after reproduction and the demonstration run; there were no uncommitted orphan results. Tests use temporary archives and do not modify the scientific archive.

External sources were retrieved and recorded with dates, publishers, authority and summaries: the official Python sqlite3 documentation and Christian Reiher's primary Annals of Mathematics paper, *The clique density theorem*. Their limited implementation/theorem-context roles are documented in `external-source-register.json` and `docs/SOURCES.md`. No external IGT paytable replaced Scenario 1. Manufacturer validation of the user-specified machine profile remains outside the supplied evidence.

## Reproduction

Run from the Keno project directory:

```bash
python3 spot_strategy_framework/tests/run_tests.py
python3 spot_strategy_framework/keno.py --archive /tmp/keno-fresh-replay history --reproduce
python3 spot_strategy_framework/keno.py run --config spot_strategy_framework/examples/quick-search.json
python3 spot_strategy_framework/keno.py rank --objective jackpot --minimum-frequency 499999/500000 --require-jackpot
python3 spot_strategy_framework/keno.py show STRATEGY_ID --full
python3 spot_strategy_framework/keno.py audit
PYTHONPATH=spot_strategy_framework python3 -m spot_strategy.benchmark --out /tmp/keno-benchmark.json
```

Python 3.10+ and the standard library suffice for the general engine; optional acceleration requires a C++17 compiler. No packages or network access are needed for probability evaluation. The README documents additional configurations, exports, resource controls and resumption.

## Next action and remaining limitations

The requested initial framework is implemented and tested. Future research should prioritize structured overlap search at the jackpot thresholds and rigorous certificates for unresolved expensive graph families. Recovery-2 can be freshly reproduced with `history --reproduce --include-expensive`; it remains clearly separated from default-budget fresh verification.

General arbitrary overlaps are accepted as configurations but cannot all be evaluated within finite default budgets. Such jobs are deferred, never promoted. Checkpoints occur between candidates and evaluators, not inside every long enumeration. A run whose source revision changes must be forked rather than resumed. Exact canonicalization falls back to literal deduplication if its permutation budget is exceeded. The exposed gross/paying/jackpot laws are separate marginals; no joint conditional-query API or independence assertion is provided. The current branch pruning is not a completed exhaustive composition-level global proof. No GUI is included, but the interface layer is separate from the mathematical engine.

## Project direction

The framework turns previously separate evaluators and archives into one repeatable research workflow. It supplies the machinery to search, verify, compare, preserve and resume future strategies without changing objectives or mistaking numerical experiments for mathematical proof. No new global optimum or improved Keno record is claimed in this engineering delivery.
