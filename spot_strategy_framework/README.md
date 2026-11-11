# Spot Strategy Research Framework

For new game models and isolated fixture runs, see the [multi-game guide](../multi_keno/README.md). The commands below use the original Scenario 1 research workspace.

A working, separate research system for Scenario 1. It generates, deduplicates, evaluates, independently verifies, ranks and archives Keno layouts. It preserves the original research files.

From the Keno project directory, using Python 3.10 or later:

```bash
python3 spot_strategy_framework/keno.py validate --config spot_strategy_framework/examples/quick-search.json
python3 spot_strategy_framework/keno.py run --config spot_strategy_framework/examples/quick-search.json
python3 spot_strategy_framework/keno.py rank --objective profitability --limit 5
python3 spot_strategy_framework/keno.py records
python3 spot_strategy_framework/keno.py audit
```

No Python dependencies are required. The optional structured native evaluator requires `g++` with C++17 support; missing compilation support produces an explicit resource deferral, never a verified result. Exact evaluation of arbitrary large overlaps can exceed the configured limits.

## Selecting a research question

```bash
python3 spot_strategy_framework/keno.py generate --cards 15,20 --spots 2-10 --family mixed --limit 10 --out /tmp/candidates.json
python3 spot_strategy_framework/keno.py run --cards 20 --spot-counts 4,4,4,4,4,4,4,4,4,4,4,4,4,4,4,4,4,7,9,7 --family mixed --objective frequency --limit 3
python3 spot_strategy_framework/keno.py rank --objective jackpot --minimum-frequency 499999/500000 --require-jackpot
python3 spot_strategy_framework/keno.py pareto --axes frequency,jackpot --out /tmp/frontier.json
python3 spot_strategy_framework/keno.py export --format csv --out /tmp/strategies.csv
```

Frequency requirements are fractions, **not percentages**: 99.9998% is `499999/500000`. Jackpot awards mean a paytable entry of exactly 10,000 credits; eligibility is determined from the fixed table. The seven independent objectives are `frequency`, `jackpot`, `recovery`, `profitability`, `expected_return`, `volatility` and `paying_cards`. Volatility minimizes variance; other objectives maximize. No arbitrary combined score is used. `rank --cards 15` filters the active-card count. Ranking and Pareto commands expose only independently verified archive entries.

Generator families: `identical`, `disjoint`, `repeated_pairs`, `rotating`, `balanced`, `mixed`, `jackpot`, `frequency`, `recovery`, `mutations`, `exhaustive`. They are search proposals, not claims of optimal designs. General `mixed` generation permits arbitrary overlaps and repeats. `pool_size` restricts only the requested experiment; it never establishes an unrestricted bound. Exhaustive enumeration is limited to the explicitly configured finite card pool and raw candidate budget. Its 10,000-option guard prevents accidental expansion.

## Evaluating a chosen layout

Save a JSON array of active cards, or an object with `cards` containing that array. A–T dictionaries are also accepted; use `null` for inactive cards. Repeated cards are allowed; repeated numbers within a card are rejected.

```bash
python3 spot_strategy_framework/keno.py evaluate spot_strategy_framework/examples/manual-layout.json --full
python3 spot_strategy_framework/keno.py show STRATEGY_ID --full
```

Every accepted result contains complete A–T assignments, exact outcome counts, marginal paying-card and jackpot-count distributions, overlap information, all four denomination scales, provenance, source revision and verification evidence. Dollar thresholds are strictly greater than $100/$500/$1,000. Recovery includes break-even; profitability excludes it. Denominations scale money and variance but do not alter the underlying layout probabilities. Maximum gross means the largest payout with nonzero exact outcome count.

## Checkpoints, archives and limits

```bash
python3 spot_strategy_framework/keno.py resume RUN_ID
python3 spot_strategy_framework/keno.py --archive /tmp/independent-replay run --config spot_strategy_framework/examples/exhaustive-small.json
```

Global options such as `--archive` and `--project-root` precede the command. Default archive: `outputs/spot-strategy-framework/archive`. Run output supplies the run ID, counters and next candidate index. Generation is deterministic by seed and candidate index. Primary evaluation is saved before independent verification; interrupted verification can reuse it. Resumption requires the same source revision. Checkpoints are between candidates and between evaluators, not inside a long numerical kernel. Deferred candidates remain unverified; increasing a budget requires a new run or direct `evaluate` call. A configured run completing does not imply exhaustive coverage of all Keno portfolios.

Accepted JSON objects and source snapshots are immutable; a SQLite index tracks transactional promotion, append-only record history, run events and pending jobs. Do not edit accepted files. `audit` checks file hashes, source snapshots and orphan files. Back up the archive after closing running processes; SQLite WAL files are part of an active database. Canonicalization is exact within its permutation budget; beyond that, a declared literal fallback may miss duplicates but never merges layouts on an unproved equivalence.

## Historical reproduction and testing

```bash
python3 spot_strategy_framework/keno.py history
python3 spot_strategy_framework/keno.py history --reproduce
python3 spot_strategy_framework/tests/run_tests.py
PYTHONPATH=spot_strategy_framework python3 -m spot_strategy.benchmark --out /tmp/benchmark.json
```

`history` registers read-only references. `--reproduce` runs both new evaluators and checks old full gross distributions where supplied. `--include-expensive` also attempts the recovery-2 geometry with a larger native budget. References retain their historical labels; a new record is promoted only after exact reproduction. A source reference alone is not a new framework verification.

See [architecture and mathematics](docs/ARCHITECTURE.md), [governance and sources](docs/GOVERNANCE.md), and the [engineering report](../outputs/spot-strategy-framework/ENGINEERING-REPORT.md). No global optimum is asserted.
