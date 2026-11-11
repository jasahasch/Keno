---
name: keno-start
description: Start source-only work in the Keno mathematical research environment, verify Record A, and smoke-test the core regressions and synthetic objectives without modifying research data.
---

# Keno source-only startup

Use this workflow when starting work in the Keno Cloud environment or running a source-only smoke test.

## Inspect before running

1. Locate the Keno checkout; the published environment used `/workspace/Keno`. Do not assume a local desktop path exists in Cloud.
2. Read applicable `AGENTS.md` instructions and the repository's `README.md`, `multi_keno/README.md`, and `docs/workspace.md`.
3. Record the Git commit and working-tree status. Preserve existing changes.
4. Set `PYTHONDONTWRITEBYTECODE=1` and keep Python assertions enabled.
5. Keep test scripts, logs, caches, and SQLite files in a temporary directory outside the checkout. Never use the default continuation database for a source-only test.

## Record A and core regressions

Run from the checkout root:

```bash
export PYTHONDONTWRITEBYTECODE=1
python3 -m multi_keno.platform verify-record-a
python3 -m unittest -v multi_keno.test_platform unrestricted_resolution.test_resolution
```

The documented baseline has 16 core regression tests. Report the actual count and any failures.

Record A should reproduce:

- Zero-payout draws: `4**20 = 1099511627776`.
- Total draws: `3535316142212174320`.
- Any-payout probability: `220957190168784159/220957258888260895`.
- Agreement between the deletion and membership-frontier zero polynomials.

Record A is an achievable record; global optimality remains open.

## Exhaustive synthetic fixture

Create an empty SQLite file in a new temporary directory. Supply `--db PATH` before every database subcommand:

```bash
python3 -m multi_keno.platform --db "$fixture_db" fixture
python3 -m multi_keno.platform --db "$fixture_db" work fixture-any-payout 1400 1000 --enumerate
python3 -m multi_keno.platform --db "$fixture_db" work fixture-net-profit 1400 1000 --enumerate
python3 -m multi_keno.platform --db "$fixture_db" status fixture-any-payout
python3 -m multi_keno.platform --db "$fixture_db" status fixture-net-profit
python3 -m multi_keno.platform --db "$fixture_db" leaders fixture-any-payout --limit 1
python3 -m multi_keno.platform --db "$fixture_db" leaders fixture-net-profit --limit 1
```

Here `fixture_db` must name the empty temporary file, not a research database.

For each objective require cursor and stop both equal to 595, 595 verified jobs/evaluations, zero rejected layouts, and no pending or deferred jobs. Cursor completion alone does not certify exhaustive evaluation.

Independently replay every stored evaluation:

1. Construct all 35 cards: combinations of sizes two and three from numbers 1–6.
2. Construct all 595 unordered pairs of distinct cards.
3. Enumerate all 20 three-number draws from numbers 1–6.
4. For each layout and draw, compute additive awards directly from the registered paytable and literal card/draw intersections.
5. Compare each full gross-count distribution with its stored evaluation. Check total draw mass 20, exact winning count, reduced probability, rule/paytable fingerprints, and the evidence for both membership-region and literal-subset evaluation.
6. For any payout, count gross awards greater than zero. For net profit, count gross awards greater than the two-credit total wager.
7. Require each legal layout exactly once per objective, with no missing or additional evaluations.

Expected version-one maxima are 20/20 for any payout and 8/20 for net profit. These are results for the invented fixture, not a commercial Keno game.

Run SQLite integrity and foreign-key checks on the temporary database. Require `integrity_check` to return `ok` and `foreign_key_check` to return no rows. Close connections and remove the temporary database, including sidecar files, afterward.

## Preservation and reporting

Compare file hashes or equivalent content evidence before and after the run for the checkout and any research directories in scope. Confirm Git status is unchanged. Do not modify the checkout to fix a smoke-test failure unless the user separately requests fixes.

Do not run the default `init`, legacy worker, migration audit, restoration, or backup-writing commands against research data during a source-only smoke test. In particular, `python3 -m multi_keno.audit` targets historical workspace data and writes artifacts; use an isolated read-only replay of the temporary fixture instead.

Report:

- Whether this skill was available, read, and applied.
- Environment identity and tested source commit when available.
- Record A verification and actual regression count/results.
- Layout and evaluation counts for both synthetic objectives, independent replay results, and maxima.
- SQLite integrity, preservation evidence, and temporary-file cleanup.
- Specific blockers and unfinished checks, without claiming missing checks passed.

## Installation note

This document is skill content, not proof of installation. For standard skill discovery, install a copy named `SKILL.md` inside a `keno-start` skill directory supported by the environment. A standalone `skills.md` file does not establish that the skill is discoverable or included in a published Cloud snapshot. Verify discovery in a fresh environment after publishing through the supported environment setup flow.
