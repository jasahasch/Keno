"""Deterministic harmless smoke; run inside the sandbox with cwd=/work."""
from collections import Counter
from fractions import Fraction
from itertools import combinations
import json
from pathlib import Path
import sys
import tempfile
import unittest


def main():
    sys.path.insert(0, str(Path.cwd()))
    from multi_keno import platform as p
    record = p.verify_record_a()
    assert record['zero'] == 1099511627776
    suite = unittest.defaultTestLoader.loadTestsFromNames(
        ['multi_keno.test_platform', 'unrestricted_resolution.test_resolution'])
    count = suite.countTestCases()
    result = unittest.TextTestRunner(verbosity=1).run(suite)
    assert count == 16 and result.wasSuccessful()
    checked = {}
    with tempfile.TemporaryDirectory(prefix='keno-bridge-fixture-') as directory:
        db = p.connect(Path(directory) / 'fixture.sqlite')
        try:
            p.migrate(db)
            spec, table = p.fixture()
            _, pid = p.register(db, spec, table)
            valid = list(combinations([c for s in (2, 3) for c in combinations(range(1, 7), s)], 2))
            assert len(valid) == 595
            for objective, best in (('any-payout', 20), ('net-profit', 8)):
                name = 'fixture-' + objective
                p.project(db, name, pid, objective)
                work = p.work(db, name, 1400, 1000, True)
                assert work == dict(exact=595, deferred=0, generated=595, rejected=0)
                project = p.context(db, name)[0]
                assert project['cursor'] == project['stop'] == '595'
                expected = {}
                for cards in valid:
                    law = Counter(sum(table['payouts'][str(len(c))][len(set(c) & set(draw))]
                                      for c in cards) for draw in combinations(range(1, 7), 3))
                    threshold = 0 if objective == 'any-payout' else 2
                    expected[p.dump(cards)] = (sum(v for gross, v in law.items() if gross > threshold), dict(law))
                rows = db.execute('SELECT q.cards,e.* FROM mk_evaluation e JOIN mk_job j ON j.id=e.job '
                                  'JOIN mk_pattern q ON q.id=j.pattern WHERE e.project=?', (project['id'],)).fetchall()
                assert len(rows) == 595
                for row in rows:
                    wins, law = expected.pop(row['cards'])
                    assert (int(row['wins']), int(row['total'])) == (wins, 20)
                    assert row['probability'] == str(Fraction(wins, 20))
                    assert {int(k): v for k, v in json.loads(row['law'])['gross_counts'].items()} == law
                    assert row['rule_sha'] == project['rule_sha'] and row['paytable_sha'] == project['table_sha']
                assert not expected and int(p.leaders(db, name, 1)[0]['wins']) == best
                checked[objective] = 595
            assert db.execute('PRAGMA integrity_check').fetchone()[0] == 'ok'
            assert not db.execute('PRAGMA foreign_key_check').fetchall()
        finally:
            db.close()
    print(json.dumps(dict(record_a_zero=record['zero'], core_tests=count, layouts=checked,
                          integrity='ok', foreign_key_errors=0, temporary_fixture_removed=True)))

if __name__ == '__main__':
    main()
