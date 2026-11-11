"""Read-only 86-incidence enumeration and optional exact envelope replay.

Print the complete ledger to stdout; never write historical checkpoints.
"""
import argparse
from collections import Counter
from hashlib import sha256
from itertools import combinations
import json
from pathlib import Path
import sys
import signal
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / 'outputs/phase4-discovery')]
import bound85 as b
import cycle85


def lift(source):
    result = set()
    for shape in source:
        n = 1 + max(map(max, shape))
        for a, c in combinations(range(n + 2), 2):
            if c == n + 1 and a < n:
                continue
            result.add(b.code(shape + ((a, c),)))
        for j, edge in enumerate(shape):
            for card in set(range(n + 1)) - set(edge):
                result.add(b.code(shape[:j] + (edge + (card,),) + shape[j + 1:]))
    return result


def partition_enumeration():
    result = set()
    for parts in b.ex.partitions(6):
        level = {()}
        for excess in parts:
            following = set()
            for shape in level:
                n = 1 + max(map(max, shape), default=-1)
                for take in range(min(n, excess + 1) + 1):
                    for old in combinations(range(n), take):
                        edge = old + tuple(range(n, n + excess + 1 - take))
                        following.add(b.code(shape + (edge,)))
            level = following
        result.update(level)
    return result


def bound(shape, packed, messages=False):
    """Phase 4 envelopes, with incidence budget explicitly changed to 86."""
    n = 1 + max(map(max, shape))
    envelopes = {0: (1,) + (0,) * 20}
    for group in b.groups(shape):
        following = {}
        for s, p in envelopes.items():
            rank = sum(map(len, group)) - (1 + max(map(max, group))) - len(group) + 1
            profiles = (cycle85.envelope(group, packed) if messages and rank <= 1
                        else b.profile_envelope(group, packed))
            for t, q in profiles:
                if s + t > 86 - 2 * (20 - n):
                    continue
                if packed:
                    def pack(poly):
                        return sum(v << (b.WIDTH * j) for j, v in enumerate(poly))
                    f = b.unpack(pack(p) * pack(q))[:21]
                else:
                    f = b.multiply(p, q)
                f += (0,) * (21 - len(f))
                if s + t in following:
                    f = tuple(map(min, zip(following[s + t], f)))
                following[s + t] = f
        envelopes = following
    minimum, count = b.D, 0
    for s, law in envelopes.items():
        remaining = 86 - s
        if not 2 * (20 - n) <= remaining <= 10 * (20 - n):
            continue
        tail = b.tail(20 - n, remaining, packed)
        minimum = min(minimum, sum(v * tail[20 - j] for j, v in enumerate(law)))
        count += 1
    assert count
    return minimum, count


def main():
    if not __debug__:
        raise SystemExit('Assertions must be enabled for certification')
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument('--width', type=int, default=0,
                        help='replay envelopes only up to this component card count')
    parser.add_argument('--messages-width', type=int, default=0,
                        help='also cover tree/single-cycle components up to this width')
    parser.add_argument('--seconds', type=float, default=600,
                        help='total work budget, including enumeration')
    parser.add_argument('--branch-seconds', type=float, default=5,
                        help='per-bound budget including packed replay')
    args = parser.parse_args()
    if args.seconds <= 0 or args.branch_seconds <= 0:
        parser.error('time budgets must be positive')
    deadline = time.monotonic() + args.seconds

    def expired(signum, frame):
        raise TimeoutError('bound resource limit')

    signal.signal(signal.SIGALRM, expired)
    table_hash = sha256((ROOT / 'outputs/keno-expanded-paytables.json').read_bytes()).hexdigest()
    assert table_hash == 'd12c1a7588b93d8e2fff3061d4c89b8b3a7c9fd6d9b386460952f2b05fe8cbe1'
    archived = json.loads((b.OUT / 'coverage-final.json').read_text())
    source = {tuple(map(tuple, row['shape'])) for row in archived['geometries']}
    assert len(source) == 167 and source == set(b.shapes85())
    keys = lift(source)
    independent = partition_enumeration()
    assert keys == independent
    rows = []

    def priority(shape):
        groups = b.groups(shape)
        width = max(1 + max(map(max, g)) for g in groups)
        ranks = [sum(map(len, g)) - (1 + max(map(max, g))) - len(g) + 1
                 for g in groups]
        return (width > args.width, max(ranks), width, shape)

    for shape in sorted(keys, key=priority):
        groups = b.groups(shape)
        ranks = [sum(map(len, g)) - (1 + max(map(max, g))) - len(g) + 1
                 for g in groups]
        width = max(1 + max(map(max, g)) for g in groups)
        row = dict(shape=shape, component_cycle_ranks=ranks, largest_component=width,
                   status='open-unvisited', evidence=[])
        messages = width <= args.messages_width and max(ranks) <= 1
        if width <= args.width or messages:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                row['status'] = 'open-budget'
            else:
                signal.setitimer(signal.ITIMER_REAL, min(args.branch_seconds, remaining))
                try:
                    lower, count = bound(shape, False, messages)
                    assert (lower, count) == bound(shape, True, messages)
                    row.update(lower=lower, combined_totals=count,
                               status='certified-no-improvement' if lower >= b.RECORD else 'open-envelope',
                               evidence=['coefficientwise profiles and residual disjoint-card envelope',
                                         'independent packed-integer profile and convolution replay'])
                    if messages:
                        row['evidence'].append('Phase 4 conditional tree/cycle messages')
                except TimeoutError:
                    row['status'] = 'open-resource-limit'
                finally:
                    signal.setitimer(signal.ITIMER_REAL, 0)
        rows.append(row)
    rows.sort(key=lambda row: row['shape'])
    assert len(rows) == len(keys) and {row['shape'] for row in rows} == keys
    assert all(sum(len(edge) - 1 for edge in row['shape']) == 6 for row in rows)
    assert all(row['lower'] >= b.RECORD and row['combined_totals'] > 0 and row['evidence']
               for row in rows if row['status'] == 'certified-no-improvement')
    print(json.dumps(dict(incidences=86, full_support=80, excess=6,
                         source_commit='unavailable: supervisor masks Git metadata',
                         configuration=vars(args),
                         paytable_sha256=table_hash, geometries=len(keys),
                         enumeration_agreement=True, dispositions=dict(Counter(r['status'] for r in rows)),
                         geometries_ledger=rows), indent=2))


if __name__ == '__main__':
    main()
