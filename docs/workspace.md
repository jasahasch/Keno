# Research workspace operations

The existing continuation worker owns the private research queue. The multi-game registry adds versioned `mk_` tables to the same working database. It leaves legacy tables, proof artifacts, and checkpoint semantics intact. Each game/rule/paytable/objective combination can use a separate project with its own enumeration cursor, queue, leaderboard, evaluations, notes, and proof references. The two migrations introduce the registry and then project notes.

The working database is `outputs/continuation-correction/continuity.sqlite`. The original read-only source is `outputs/persistent-progressive/search.sqlite`. The source-only release includes the worker code and frozen mathematical inputs. It does not contain private database snapshots or the historical run archives required to resume this workspace.

## Resume the original search

From the workspace root:

```bash
export PYTHONDONTWRITEBYTECODE=1
python3 outputs/continuation-correction/continuity.py work 24 24000 .35 --batch 4
python3 outputs/continuation-correction/retention.py search --zero 1099511627776
```

The task, state and time budgets limit each invocation. The worker retains complete results, cursors and deferred scopes. A changed resource signature can make a deferral eligible again. Optional queue filters narrow one invocation's work; they leave other branches open. The multi-game project's `work` command has its own checkpoints. A larger work budget makes its deferred jobs eligible again.

## Preservation and recovery

Before schema changes, take a consistent snapshot with SQLite's online backup API. Keep prior proofs and backups immutable. Restore into a new path and run SQLite integrity and foreign-key checks before using it. Do not copy the live main file without its WAL state. The workspace audit compares historical schemas and all legacy rows with the pre-migration snapshot. The historical baseline was 2,791 results, 38,471 scopes, 1,407 attempts and 126 Phase 4 certificates. Those counts are checkpoint values and can increase as research continues.

```bash
python3 -m multi_keno.audit
```

That command is workspace-only. It uses the existing pre-migration snapshot and updates a post-migration audit backup. Use a separate audit copy when preserving a previous backup verbatim. The existing retention helper can restore a changed-page backup to a new path when the matching base and delta are available. Continue from a restored copy only after comparing hashes, counts, and evidence.

Workspace regression tests use the historical evidence tree. Run the core suite with `python3 -m unittest -v multi_keno.test_platform unrestricted_resolution.test_resolution`. In the full workspace, also run `PYTHONPATH=spot_strategy_framework python3 -m unittest discover -s spot_strategy_framework/tests -p 'test_*.py'` and run `python3 -m unittest test_continuity test_retention test_expansion` from the continuation worker directory. These additional suites require private workspace fixtures and are outside the source-only release.

### Restore a full SQLite snapshot into an unused path

Set `snapshot_db` to a verified, complete backup file and `restored_db` to a new destination. Keep the snapshot and working research databases in their original locations.

```bash
python3 - "$snapshot_db" "$restored_db" <<'PY'
from pathlib import Path
import sqlite3
import sys

snapshot, target = map(Path, sys.argv[1:])
if not snapshot.is_file():
    raise SystemExit("Snapshot is missing")
with target.open("xb"):
    pass
with sqlite3.connect(snapshot.resolve().as_uri() + "?mode=ro", uri=True) as source:
    with sqlite3.connect(target) as copy:
        source.backup(copy)
        assert copy.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
        assert not copy.execute("PRAGMA foreign_key_check").fetchall()
PY
```

A fresh research database for the synthetic example is separate from this restore process. See the [fresh-checkout commands](../multi_keno/README.md#fresh-checkout).
