# Multi-game Keno research

This Python 3 module adds a versioned registry and project-scoped exact research to the existing SQLite continuation database. It uses only the standard library and the existing Scenario 1 modules. The existing worker, retention commands, tables, queue, backups and proof files stay usable.

## Quick start

Run from the repository root with Python assertions enabled. The following commands use the existing private research workspace. The isolated example below runs from the source release.

```bash
export PYTHONDONTWRITEBYTECODE=1
python3 -m multi_keno.platform init
python3 -m multi_keno.platform leaders scenario1-any-payout --limit 1
python3 -m multi_keno.platform fixture
python3 -m multi_keno.platform work fixture-any-payout 1400 1000 --enumerate
python3 -m multi_keno.platform work fixture-net-profit 1400 1000 --enumerate
python3 -m multi_keno.platform status fixture-any-payout
```

The fixture is an invented six-number universe drawing three numbers, with two distinct cards of size two or three. It demonstrates the engine and separate objectives. It is unrelated to any commercial game. A completed fixture cursor covers 595 unordered legal layouts. The ordering reduction holds because card permutation leaves the additive payout and legal overlap constraints unchanged. Original labeled slots are retained for manually entered patterns.


### Fresh checkout

The Record A check loads the frozen paytable and unchanged exact counters without opening a database. Use a new temporary file for the fixture.

```bash
python3 -m multi_keno.platform verify-record-a
fixture_db=$(mktemp)
python3 -m multi_keno.platform --db "$fixture_db" fixture
python3 -m multi_keno.platform --db "$fixture_db" work fixture-any-payout 1400 1000 --enumerate
python3 -m multi_keno.platform --db "$fixture_db" work fixture-net-profit 1400 1000 --enumerate
python3 -m multi_keno.platform --db "$fixture_db" leaders fixture-any-payout --limit 1
python3 -m multi_keno.platform --db "$fixture_db" leaders fixture-net-profit --limit 1
```

The synthetic version-one table yields exact maxima of **20/20** for any payout and **8/20** for net profit. The disjoint two-pair pattern `[[1,2],[3,4]]` pays on **8/20** draws under version one and **0/20** under version two. These results apply only to the synthetic fixture.

## Register a game

Use [the synthetic rule file](examples/fixture-rules.json) and [the first synthetic award table](examples/fixture-table-v1.json) as schema examples. Specify the full rule model, including the number universe, draw count, active cards, sorted allowed sizes, overlap and duplication rules, one-card wager in integer payout units, and supported objectives. Specify every award from zero through all hits. Record an identifiable source and version. Zero-hit awards and nonmonotone hit awards are supported in the generic engine. The existing 20-card table is imported from the immutable local Scenario 1 source.

```bash
python3 -m multi_keno.platform register RULES.json TABLE.json
python3 -m multi_keno.platform project PROJECT PAYTABLE_ID any-payout
python3 -m multi_keno.platform add PROJECT '[[1,2],[3,4]]'
python3 -m multi_keno.platform edit PROJECT PATTERN_ID '{"2":[2,4,5]}'
python3 -m multi_keno.platform work PROJECT 20 100000
python3 -m multi_keno.platform patterns PROJECT --number 2 --spots 3
python3 -m multi_keno.platform compare PROJECT PATTERN_ID OTHER_PATTERN_ID
python3 -m multi_keno.platform leaders PROJECT
python3 -m multi_keno.platform note PROJECT hypothesis "Describe the conjecture and its scope"
```

Replace IDs with those printed by registration and pattern creation. The example cards suit the fixture rules. The two objectives are any positive award and strictly positive net return after the equal per-card wager. Each is a separate project with its own jobs, checkpoint, verification evidence and ranking. Search additionally supports the unchanged Scenario 1 retention CLI for legacy result IDs and historical branches.

Register a changed paytable under a new identifier or version. The same game/rule/award version cannot be reused with different bytes after canonical JSON encoding. Create another project for the new table and run `python3 -m multi_keno.platform queue NEW_PROJECT PATTERN_ID` to reevaluate the existing labeled pattern. The new evaluation retains its paytable fingerprint. [Synthetic version two](examples/fixture-table-v2.json) demonstrates this operation.

The [Cleopatra proposal](cleopatra-proposal.json) is an inventory of unresolved rules. It is deliberately outside the registrable schema. The name suggests four cards. Official card count, universe, draw and award rules remain unverified. Mechanics other than uniform fixed-size draws and additive hit-count awards are rejected. Bonus draws, multiplier behavior and other stateful mechanics require an explicitly validated new evaluator before registration.

## Exact evaluators and coverage

The generic engine computes the complete integer gross distribution by two different methods. The first uses number-membership regions and binomial weights. The second enumerates physical support subsets and weights them by all compatible outside-number selections. Both condition on the fixed total draw count. A result is verified only after full coefficient agreement and exact draw-mass validation. Either method may defer under its work limit. The baseline Scenario 1 project routes any-payout jobs through the existing deletion and membership-frontier zero counters, after checking the exact rule and paytable binding. Its result is an exact zero polynomial. That adapter does not produce a gross payout distribution.

Run `work PROJECT STEPS BUDGET --enumerate` to traverse the exact sorted card-set universe, or multiset universe where duplicates are allowed. Cardinality, duplication and disjointness rules apply. The cursor includes any deterministically rejected overlap cases. Each cursor advance and its queued pattern commit together. Each job commits its result and verified state together. A larger budget makes deferred jobs eligible again. Reaching the cursor endpoint alone does not certify an optimum. All legal candidates also need exact evaluation. These generic enumerations grow combinatorially and are intended for small exhaustive studies or bounded work on large models.

## SQLite and preservation

Two additive migrations create the `mk_` namespace. Rules and paytables have immutable version keys and content fingerprints. A project binds the paytable, rules and objective. Patterns retain literal slot assignments and number-membership identity for fixed slots. Physical-number relabeling preserves the corresponding hit law by a draw bijection. The registry stores literal observations even when their membership identities are equal. Pattern versions store the parent, child and edited slots. Jobs, runs, verified evaluations and certificates are linked to their project. Rankings compare decimal integer text by length and then lexicographically, so they do not round counts or depend on SQLite's integer width.

The original Scenario 1 leaderboard is exposed by a rule- and paytable-bound adapter. The existing database retains its own unresolved continuation scopes and historical results. The [85-incidence proof](../docs/mathematics.md) is registered with its evidence hash and explicit assumptions. That proof is scoped to the baseline project. A differently configured game starts with its own cursor and without inherited exclusions.

Use SQLite's online backup API to copy the working database before migration or while taking a consistent checkpoint. Restore to a new location first, run SQLite integrity and foreign-key checks, and compare the relevant counts and fingerprints. The migration audit in this workspace uses the saved pre-migration snapshot to compare every legacy row and schema object. Run tests with `python3 -m unittest -v multi_keno.test_platform`. The audit command `python3 -m multi_keno.audit` also independently verifies the fixture demonstration and creates a checked post-migration backup.

For an isolated new research database, create an empty SQLite file and pass its path with `--db PATH` before the subcommand. Run `register` and `project` for new games, or `fixture` for the test game. Reserve `init` for the actual continuation database or a consistent copy of it.

See [workspace operations](../docs/workspace.md) for continuation and restoration.
