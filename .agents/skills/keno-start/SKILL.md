---
name: keno-start
description: Verify the source-only Keno workflow when onboarding a checkout or running a local or Cloud smoke test.
---

# Keno startup

Run from the repository root. Use Python 3.10 or later with standard-library
SQLite. The source-only checks require no dependency installation or running
service.

```bash
export PYTHONDONTWRITEBYTECODE=1
python3 -m multi_keno.platform verify-record-a
python3 -m unittest -v multi_keno.test_platform unrestricted_resolution.test_resolution
```

Record A should reproduce exactly 1,099,511,627,776 zero-payout draws. The
validated baseline has 16 passing core regression tests.

For the synthetic checks, follow the isolated fixture commands in
[multi_keno/README.md](../../../multi_keno/README.md). Use a fresh temporary
SQLite file and pass its path with `--db` before every fixture subcommand.
Verify 595 layouts per objective with maxima of 20/20 for any payout and
8/20 for strict net profit. The C++ evaluator is optional.

Keep validation artifacts temporary. Historical research requires private
backups, which the source-only checks do not need. Preserve the research
source and databases. Report the checkout, observed results, and any blockers.
