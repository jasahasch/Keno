"""Bounded continuation of the frozen 86-incidence ledger; stdout is a new ledger.

No historical files or databases are written. Run with assertions enabled.
"""
import argparse
from collections import Counter
from hashlib import sha256
import json
from pathlib import Path
import signal
import time

import incidence86 as base


def key(row):
    return tuple(map(tuple, row['shape']))


def priority(row):
    return (row['largest_component'], max(row['component_cycle_ranks']), key(row))


def main():
    if not __debug__:
        raise SystemExit('Assertions must be enabled')
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument('--seconds', type=float, default=760)
    parser.add_argument('--retry-seconds', type=float, default=12)
    parser.add_argument('--unvisited-seconds', type=float, default=1)
    args = parser.parse_args()
    if not 0 < args.seconds <= 840 or min(args.retry_seconds, args.unvisited_seconds) <= 0:
        parser.error('positive budgets required; total must be at most 840 seconds')
    started = time.monotonic()
    deadline = started + args.seconds
    path = base.ROOT / 'docs/incidence86-coverage.json'
    raw = path.read_bytes()
    baseline = json.loads(raw)
    rows = baseline['geometries_ledger']
    original = {key(row): row for row in rows}
    assert len(original) == len(rows) == 725
    assert Counter(r['status'] for r in rows) == {
        'certified-no-improvement': 434, 'open-resource-limit': 38, 'open-unvisited': 253}
    table_hash = sha256((base.ROOT / 'outputs/keno-expanded-paytables.json').read_bytes()).hexdigest()
    assert table_hash == baseline['paytable_sha256'] == 'd12c1a7588b93d8e2fff3061d4c89b8b3a7c9fd6d9b386460952f2b05fe8cbe1'

    def expired(signum, frame):
        raise TimeoutError('bounded attempt expired')

    signal.signal(signal.SIGALRM, expired)
    signal.setitimer(signal.ITIMER_REAL, max(.001, deadline - time.monotonic()))
    try:
        source = {tuple(map(tuple, row['shape'])) for row in
                  json.loads((base.b.OUT / 'coverage-final.json').read_text())['geometries']}
        assert len(source) == 167 and source == set(base.b.shapes85())
        assert base.lift(source) == base.partition_enumeration() == set(original)
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
    attempts = []
    updated = dict(original)
    # Every first-group case receives its bounded attempt before the second group.
    targets = sorted((r for r in rows if r['status'] == 'open-resource-limit'), key=key)
    targets += sorted((r for r in rows if r['status'] == 'open-unvisited'), key=priority)
    for row in targets:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            break
        shape = key(row)
        allotted = min(remaining, args.retry_seconds if row['status'] == 'open-resource-limit'
                       else args.unvisited_seconds)
        messages = max(row['component_cycle_ranks']) <= 1
        attempt = dict(shape=shape, baseline_status=row['status'], budget_seconds=allotted,
                       method='conditional-tree-cycle' if messages else 'full-component-profiles',
                       replay='packed-integer', stage='initial', status='open-resource-limit')
        tick = time.monotonic()
        signal.setitimer(signal.ITIMER_REAL, allotted)
        try:
            lower, totals = base.bound(shape, False, messages)
            attempt['stage'] = 'packed-replay'
            assert (lower, totals) == base.bound(shape, True, messages)
            attempt.update(stage='finished', lower=lower, combined_totals=totals,
                           status='certified-no-improvement' if lower >= base.b.RECORD else 'open-envelope')
        except TimeoutError:
            pass
        finally:
            signal.setitimer(signal.ITIMER_REAL, 0)
        attempt['elapsed_seconds'] = time.monotonic() - tick
        attempts.append(attempt)
        updated[shape] = dict(row, status=attempt['status'], continuation_attempt=len(attempts))
        print(json.dumps(dict(attempt=len(attempts), **attempt)), file=base.sys.stderr, flush=True)
    after = Counter(r['status'] for r in updated.values())
    assert all(updated[key(r)] == r for r in rows if r['status'] == 'certified-no-improvement')
    report = dict(baseline_commit_requested='3a859fa', source_commit='unavailable: masked Git metadata',
                  host_identity='not independently attested', baseline_sha256=sha256(raw).hexdigest(),
                  paytable_sha256=table_hash, census_keys=725, enumeration_agreement=True,
                  configuration=vars(args), elapsed_seconds=time.monotonic()-started,
                  before=dict(Counter(r['status'] for r in rows)), after=dict(after),
                  accepted_baseline_preserved=434, attempts=attempts,
                  unattempted=[dict(shape=key(r), baseline_status=r['status']) for r in targets
                               if key(r) not in {tuple(map(tuple, a['shape'])) for a in attempts}])
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
