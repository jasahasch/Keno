"""Audit a scratch post-PR9 ledger and its flushed attempt journal, read-only.

Usage: python3 tools/check_incidence86_post_pr9.py LEDGER JOURNAL
The optional --replay recomputes every accepted bound in both representations.
"""
import argparse
from collections import Counter
from hashlib import sha256
import json
from pathlib import Path

import incidence86 as base


def key(row):
    return tuple(map(tuple, row['shape']))


def main():
    if not __debug__:
        raise SystemExit('Assertions must be enabled')
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument('ledger', type=Path)
    parser.add_argument('journal', type=Path)
    parser.add_argument('--replay', action='store_true')
    args = parser.parse_args()
    report = json.loads(args.ledger.read_text())
    paths = ['incidence86-coverage.json', 'incidence86-continuation.json',
             'incidence86-priority.json']
    data = []
    for name, field in zip(paths, ['baseline_sha256', 'continuation_sha256', 'priority_sha256']):
        raw = (base.ROOT / 'docs' / name).read_bytes()
        assert sha256(raw).hexdigest() == report[field]
        data.append(json.loads(raw))
    rows = data[0]['geometries_ledger']
    live = {key(r): r for r in rows}
    assert len(live) == len(rows) == 725
    histories = {k: [r] for k, r in live.items()}
    for delta in data[1:]:
        attempts = delta['attempts']
        assert len({key(a) for a in attempts}) == len(attempts)
        for a in attempts:
            k = key(a)
            assert live[k]['status'] == a['baseline_status']
            assert live[k]['status'].startswith('open-')
            live[k] = a
            histories[k].append(a)
    assert Counter(r['status'] for r in live.values()) == report['before'] == {
        'certified-no-improvement': 503, 'open-resource-limit': 222}
    old = dict(live)
    journal = [json.loads(line) for line in args.journal.read_text().splitlines()]
    assert journal == [dict(attempt=i, **a) for i, a in enumerate(report['attempts'], 1)]
    seen = set()
    excluded = {key(a) for a in data[2]['attempts'] if a['priority_group'] == 1}
    replayed = 0
    for a in report['attempts']:
        k = key(a)
        assert k in live and k not in seen and k not in excluded
        assert a['baseline_status'] == live[k]['status'] == 'open-resource-limit'
        assert a['previous_stopping_stage'] == live[k]['stage']
        assert 0 < a['budget_seconds'] <= report['configuration']['unvisited_seconds']
        assert a['elapsed_seconds'] >= 0
        if a['status'] == 'certified-no-improvement':
            assert a['stage'] == 'finished' and a['lower'] >= base.b.RECORD
            assert a['combined_totals'] > 0 and a['replay'] == 'packed-integer'
            if args.replay:
                messages = a['method'] == 'conditional-tree-cycle'
                expected = (a['lower'], a['combined_totals'])
                assert base.bound(k, False, messages) == expected
                assert base.bound(k, True, messages) == expected
                replayed += 1
        else:
            assert a['status'] in ('open-resource-limit', 'open-envelope')
            assert a['stage'] in ('initial', 'packed-replay', 'finished')
        seen.add(k)
        live[k] = a
        histories[k].append(a)
    assert Counter(r['status'] for r in live.values()) == report['after']
    assert all(live[k] == r for k, r in old.items() if r['status'] == 'certified-no-improvement')
    remaining = {k for k, r in live.items() if r['status'].startswith('open-')}
    assert {tuple(map(tuple, k)) for k in report['deferred_priority_keys']} == remaining & excluded
    assert {key(r) for r in report['unattempted']} == {
        k for k, r in old.items() if r['status'].startswith('open-') and k not in excluded and k not in seen}
    print(json.dumps(dict(before=report['before'], after=report['after'], attempts=len(seen),
                          replayed=replayed, newly_certified=[k for k in seen if live[k]['status']=='certified-no-improvement'],
                          still_open=sorted(remaining), histories=[dict(shape=k, history=histories[k]) for k in sorted(remaining)]), indent=2))


if __name__ == '__main__':
    main()
