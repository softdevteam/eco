import pytest

from version_control.diff3_driver import Diff3ConflictRegion
from version_control.merge3 import merge3_with_change_regions


class Test_merge3:
    def test_empty(self):
        assert merge3_with_change_regions([], [], []) == ([], [])

    def test_same(self):
        assert merge3_with_change_regions(['a'], ['a'], ['a']) == (['a'], [])
        assert merge3_with_change_regions(['a', 'b'], ['a', 'b'], ['a', 'b']) == (['a', 'b'], [])
        assert merge3_with_change_regions(['a', 'b', 'c'], ['a', 'b', 'c'], ['a', 'b', 'c']) == (['a', 'b', 'c'], [])

    def test_replace(self):
        assert merge3_with_change_regions(['b'], ['a'], ['a']) == ([Diff3ConflictRegion(base=['b'], derived_main=['a'])], [('replace', 0,1,0,1)])
        assert merge3_with_change_regions(['b'], ['a'], ['a'], True) == (['a'], [])
        assert merge3_with_change_regions(['a'], ['b'], ['a']) == (['b'], [])
        assert merge3_with_change_regions(['a'], ['a'], ['b']) == (['b'], [('replace', 0,1,0,1)])
        assert merge3_with_change_regions(['a', 'b'], ['c', 'b'], ['c', 'b']) == ([Diff3ConflictRegion(base=['a'], derived_main=['c']), 'b'], [('replace', 0,1,0,1)])
        assert merge3_with_change_regions(['a', 'b'], ['c', 'b'], ['c', 'b'], True) == (['c', 'b'], [])
        assert merge3_with_change_regions(['c', 'b'], ['a', 'b'], ['c', 'b']) == (['a', 'b'], [])
        assert merge3_with_change_regions(['c', 'b'], ['c', 'b'], ['a', 'b']) == (['a', 'b'], [('replace', 0,1,0,1)])
        assert merge3_with_change_regions(['a'], ['b'], ['c']) == ([Diff3ConflictRegion(base=['a'], derived_local=['b'], derived_main=['c'])], [('replace', 0,1,0,1)])

        assert merge3_with_change_regions(['a', 'b', 'c'], ['a', 'b', 'c'], ['a', 'b', 'c']) == (['a', 'b', 'c'], [])
        assert merge3_with_change_regions(['a', 'b', 'c'], ['a', 'd', 'c'], ['a', 'b', 'c']) == (['a', 'd', 'c'], [])
        assert merge3_with_change_regions(['a', 'b', 'c'], ['a', 'b', 'c'], ['a', 'd', 'c']) == (['a', 'd', 'c'], [('replace', 1,2,1,2)])
        assert merge3_with_change_regions(['a', 'b', 'c'], ['a', 'e', 'c'], ['a', 'd', 'c']) == (['a', Diff3ConflictRegion(base=['b'], derived_local=['e'], derived_main=['d']), 'c'], [('replace', 1,2,1,2)])
        assert merge3_with_change_regions(['a', 'b', 'c'], ['a', 'b', 'e', 'c'], ['a', 'x', 'c']) == (['a', Diff3ConflictRegion(base=['b'], derived_local=['b', 'e'], derived_main=['x']), 'c'], [('replace', 1,3,1,2)])

    def test_insert(self):
        assert merge3_with_change_regions(['x', 'a', 'b'], ['a', 'b'], ['a', 'b']) == ([Diff3ConflictRegion(base=['x'], derived_main=[]), 'a', 'b'], [('insert', 0,0,0,1)])
        assert merge3_with_change_regions(['x', 'a', 'b'], ['a', 'b'], ['a', 'b'], True) == (['a', 'b'], [])
        assert merge3_with_change_regions(['a', 'b'], ['x', 'a', 'b'], ['a', 'b']) == (['x', 'a', 'b'], [])
        assert merge3_with_change_regions(['a', 'b'], ['a', 'b'], ['x', 'a', 'b']) == (['x', 'a', 'b'], [('insert', 0,0,0,1)])
        assert merge3_with_change_regions(['a', 'x', 'b'], ['a', 'b'], ['a', 'b']) == (['a', Diff3ConflictRegion(base=['x'], derived_main=[]), 'b'], [('insert', 1,1,1,2)])
        assert merge3_with_change_regions(['a', 'x', 'b'], ['a', 'b'], ['a', 'b'], True) == (['a', 'b'], [])
        assert merge3_with_change_regions(['a', 'b'], ['a', 'x', 'b'], ['a', 'b']) == (['a', 'x', 'b'], [])
        assert merge3_with_change_regions(['a', 'b'], ['a', 'b'], ['a', 'x', 'b']) == (['a', 'x', 'b'], [('insert', 1,1,1,2)])
        assert merge3_with_change_regions(['a', 'b', 'x'], ['a', 'b'], ['a', 'b']) == (['a', 'b', Diff3ConflictRegion(base=['x'], derived_main=[])], [('insert', 2,2,2,3)])
        assert merge3_with_change_regions(['a', 'b', 'x'], ['a', 'b'], ['a', 'b'], True) == (['a', 'b'], [])
        assert merge3_with_change_regions(['a', 'b'], ['a', 'b', 'x'], ['a', 'b']) == (['a', 'b', 'x'], [])
        assert merge3_with_change_regions(['a', 'b'], ['a', 'b'], ['a', 'b', 'x']) == (['a', 'b', 'x'], [('insert', 2,2,2,3)])
        assert merge3_with_change_regions(['a', 'b'], ['a', 'b', 'x'], ['a', 'b', 'c']) == (['a', 'b', Diff3ConflictRegion(base=[], derived_local=['x'], derived_main=['c'])], [('replace', 2,3,2,3)])

    def test_remove(self):
        assert merge3_with_change_regions(['a', 'b'], ['x', 'a', 'b'], ['x', 'a', 'b']) == ([Diff3ConflictRegion(base=[], derived_main=['x']), 'a', 'b'], [('replace', 0,1,0,1)])
        assert merge3_with_change_regions(['a', 'b'], ['x', 'a', 'b'], ['x', 'a', 'b'], True) == (['x', 'a', 'b'], [])
        assert merge3_with_change_regions(['x', 'a', 'b'], ['a', 'b'], ['x', 'a', 'b']) == (['a', 'b'], [])
        assert merge3_with_change_regions(['x', 'a', 'b'], ['x', 'a', 'b'], ['a', 'b']) == (['a', 'b'], [('delete', 0,1,0,0)])
        assert merge3_with_change_regions(['a', 'b'], ['a', 'x', 'b'], ['a', 'x', 'b']) == (['a', Diff3ConflictRegion(base=[], derived_main=['x']), 'b'], [('replace', 1,2,1,2)])
        assert merge3_with_change_regions(['a', 'b'], ['a', 'x', 'b'], ['a', 'x', 'b'], True) == (['a', 'x', 'b'], [])
        assert merge3_with_change_regions(['a', 'x', 'b'], ['a', 'b'], ['a', 'x', 'b']) == (['a', 'b'], [])
        assert merge3_with_change_regions(['a', 'x', 'b'], ['a', 'x', 'b'], ['a', 'b']) == (['a', 'b'], [('delete', 1,2,1,1)])
        assert merge3_with_change_regions(['a', 'b'], ['a', 'b', 'x'], ['a', 'b', 'x']) == (['a', 'b', Diff3ConflictRegion(base=[], derived_main=['x'])], [('replace', 2,3,2,3)])
        assert merge3_with_change_regions(['a', 'b'], ['a', 'b', 'x'], ['a', 'b', 'x'], True) == (['a', 'b', 'x'], [])
        assert merge3_with_change_regions(['a', 'b', 'x'], ['a', 'b'], ['a', 'b', 'x']) == (['a', 'b'], [])
        assert merge3_with_change_regions(['a', 'b', 'x'], ['a', 'b', 'x'], ['a', 'b']) == (['a', 'b'], [('delete', 2,3,2,2)])
        assert merge3_with_change_regions(['a', 'b', 'x'], ['a', 'b'], ['a', 'b', 'c']) == (['a', 'b', Diff3ConflictRegion(base=['x'], derived_main=['c'], derived_local=[])], [('insert', 2,2,2,3)])
        assert merge3_with_change_regions(['a', 'b', 'x'], ['a', 'b', 'c'], ['a', 'b']) == (['a', 'b', Diff3ConflictRegion(base=['x'], derived_main=[], derived_local=['c'])], [('replace', 2,3,2,3)])

