import pytest

from ext_tools import diff3_driver


class Test_diff3:
    def test_empty(self):
        assert diff3_driver.diff3([], [], []) == []

    def test_same(self):
        assert diff3_driver.diff3(['a'], ['a'], ['a']) == ['a']
        assert diff3_driver.diff3(['a', 'b'], ['a', 'b'], ['a', 'b']) == ['a', 'b']
        assert diff3_driver.diff3(['a', 'b', 'c'], ['a', 'b', 'c'], ['a', 'b', 'c']) == ['a', 'b', 'c']

    def test_replace(self):
        assert diff3_driver.diff3(['b'], ['a'], ['a']) == [{'base': ['b'], 'derived2': ['a']}]
        assert diff3_driver.diff3(['a'], ['b'], ['a']) == ['b']
        assert diff3_driver.diff3(['a'], ['a'], ['b']) == ['b']
        assert diff3_driver.diff3(['a', 'b'], ['c', 'b'], ['c', 'b']) == [{'base': ['a'], 'derived2': ['c']}, 'b']
        assert diff3_driver.diff3(['c', 'b'], ['a', 'b'], ['c', 'b']) == ['a', 'b']
        assert diff3_driver.diff3(['c', 'b'], ['c', 'b'], ['a', 'b']) == ['a', 'b']

    def test_insert(self):
        assert diff3_driver.diff3(['x', 'a', 'b'], ['a', 'b'], ['a', 'b']) == [{'base': ['x'], 'derived2': []}, 'a', 'b']
        assert diff3_driver.diff3(['a', 'b'], ['x', 'a', 'b'], ['a', 'b']) == ['x', 'a', 'b']
        assert diff3_driver.diff3(['a', 'b'], ['a', 'b'], ['x', 'a', 'b']) == ['x', 'a', 'b']
        assert diff3_driver.diff3(['a', 'x', 'b'], ['a', 'b'], ['a', 'b']) == ['a', {'base': ['x'], 'derived2': []}, 'b']
        assert diff3_driver.diff3(['a', 'b'], ['a', 'x', 'b'], ['a', 'b']) == ['a', 'x', 'b']
        assert diff3_driver.diff3(['a', 'b'], ['a', 'b'], ['a', 'x', 'b']) == ['a', 'x', 'b']
        assert diff3_driver.diff3(['a', 'b', 'x'], ['a', 'b'], ['a', 'b']) == ['a', 'b', {'base': ['x'], 'derived2': []}]
        assert diff3_driver.diff3(['a', 'b'], ['a', 'b', 'x'], ['a', 'b']) == ['a', 'b', 'x']
        assert diff3_driver.diff3(['a', 'b'], ['a', 'b'], ['a', 'b', 'x']) == ['a', 'b', 'x']

    def test_remove(self):
        assert diff3_driver.diff3(['a', 'b'], ['x', 'a', 'b'], ['x', 'a', 'b']) == [{'base': [], 'derived2': ['x']}, 'a', 'b']
        assert diff3_driver.diff3(['x', 'a', 'b'], ['a', 'b'], ['x', 'a', 'b']) == ['a', 'b']
        assert diff3_driver.diff3(['x', 'a', 'b'], ['x', 'a', 'b'], ['a', 'b']) == ['a', 'b']
        assert diff3_driver.diff3(['a', 'b'], ['a', 'x', 'b'], ['a', 'x', 'b']) == ['a', {'base': [], 'derived2': ['x']}, 'b']
        assert diff3_driver.diff3(['a', 'x', 'b'], ['a', 'b'], ['a', 'x', 'b']) == ['a', 'b']
        assert diff3_driver.diff3(['a', 'x', 'b'], ['a', 'x', 'b'], ['a', 'b']) == ['a', 'b']
        assert diff3_driver.diff3(['a', 'b'], ['a', 'b', 'x'], ['a', 'b', 'x']) == ['a', 'b', {'base': [], 'derived2': ['x']}]
        assert diff3_driver.diff3(['a', 'b', 'x'], ['a', 'b'], ['a', 'b', 'x']) == ['a', 'b']
        assert diff3_driver.diff3(['a', 'b', 'x'], ['a', 'b', 'x'], ['a', 'b']) == ['a', 'b']

