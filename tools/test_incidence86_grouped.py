"""Direct allocation oracle for the grouped tree and cycle lower envelopes."""
import unittest
import incidence86_grouped as grouped
import incidence86 as base

class GroupedTests(unittest.TestCase):
    def test_direct_allocations(self):
        for shape in [((0,1),), ((0,1),(0,2)), ((0,1),(0,2),(0,3)),
                      ((0,1),(1,2),(0,2))]:
            direct=dict(base.b.profile_envelope(shape,False))
            ordinary=dict(grouped.envelope(shape,False))
            packed=dict(grouped.envelope(shape,True))
            self.assertEqual(ordinary,packed)
            self.assertEqual(set(direct),set(ordinary))
            for total,p in ordinary.items():
                self.assertTrue(all(a<=b for a,b in zip(p,direct[total])))
            # Stars have no intervening conditional minimization.
            if len(shape)<=3 and all(0 in edge for edge in shape):
                self.assertEqual(ordinary,direct)

if __name__=='__main__': unittest.main()
