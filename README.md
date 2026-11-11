# Keno Mathematical Research Platform

Exact, reproducible Keno research with versioned game rules, paytables, and project-specific objectives. The project includes the original Scenario 1 analysis and a synthetic game that can be exhaustively verified in a fresh checkout.

| Model | Status |
|---|---|
| Scenario 1, twenty distinct cards | Record A verified at 1,099,511,627,776 zero-payout draws. Global optimality is open. |
| Six-number synthetic fixture | All 595 legal layouts verified under both objectives. |
| 4 Card Cleopatra Keno | Proposed. Official rules, paytables, and bonus mechanics remain unverified. |

## Start with the public examples

Python 3.10 or later and SQLite support in the Python standard library are required. Run from the project root.

```bash
export PYTHONDONTWRITEBYTECODE=1
python3 -m multi_keno.platform verify-record-a
python3 -m unittest -v multi_keno.test_platform unrestricted_resolution.test_resolution
```

[Multi-game guide](multi_keno/README.md) covers an isolated fixture database, adding models, editing patterns and reevaluating under another paytable. [Mathematical specification](docs/mathematics.md) covers exact evaluation and Phase 4. [Workspace operations](docs/workspace.md) covers private research databases, the original worker, checkpoints, and restoration. [Publication checklist](docs/publication.md) describes the source release and its boundaries.
