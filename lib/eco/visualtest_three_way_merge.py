import sys
from grammars.grammars import python
from treemanager import TreeManager
from PyQt4 import QtCore

from version_control import gumtree_three_way_merge



visualise = '--visualise' in sys.argv


settings = QtCore.QSettings("softdev", "Eco")
lspace_root = str(settings.value("env_lspaceroot").toString())
lspace_root = lspace_root if lspace_root != "" else None





def _new_tm(language):
    t1 = TreeManager()
    parser, lexer = language.load()
    t1.add_parser(parser, lexer, language.name)
    return t1

def _merge3(base_tm, d_local_tm, d_main_tm):
    return gumtree_three_way_merge.merge3_tree_managers(base_tm, d_local_tm, d_main_tm,
                                                        lspace_root=lspace_root,
                                                        visualise=visualise)

def _diff2(tm_a, tm_b):
    return gumtree_three_way_merge.diff2_tree_managers(tm_a, tm_b)


def test_indent_diff():
    tm_a = _new_tm(python)
    tm_b = _new_tm(python)
    tm_a.import_file(
"""class MyClass (object):
    def __init__(self):
        pass
class Inner (object):
    def __init__(self):
        pass
    def q(self):
        return None
""")
    tm_b.import_file(
"""class MyClass (object):
    class Inner (object):
        def __init__(self):
            pass
        def q(self):
            return None
    def __init__(self):
        pass
""")
    assert tm_a.get_mainparser().last_status
    assert tm_b.get_mainparser().last_status

    diffs = _diff2(tm_a, tm_b)

    for diff in diffs:
        print diff


def test_merge3_simple_a():
    base_tm = _new_tm(python)
    d_local_tm = _new_tm(python)
    d_main_tm = _new_tm(python)
    base_tm.import_file(
"""def aaa(xxx):
    return xxx**2

def bbb(yyy):
    return yyy + 1

def ccc(zzz):
    return zzz / 2
""")
    d_local_tm.import_file(
"""def aaa(xxx):
    return xxx**2

def ddd(qqq):
    return qqq + 1

def ccc(zzz):
    return zzz / 2
""")
    d_main_tm.import_file(
"""def aaa(xxx):
    return xxx**2

def bbb(yyy):
    return yyy + 1

def eee(rrr):
    return rrr / 2
""")
    assert base_tm.get_mainparser().last_status
    assert d_local_tm.get_mainparser().last_status
    assert d_main_tm.get_mainparser().last_status
    for i in range(7):
        d_main_tm.key_cursors("down")
    for i in range(17):
        d_main_tm.key_cursors("right")
    d_main_tm.key_normal('/')

    merged_tm = _merge3(base_tm, d_local_tm, d_main_tm)

    text = merged_tm.export_as_text(None)

    assert text == \
"""def aaa(xxx):
    return xxx**2

def ddd(qqq):
    return qqq + 1

def eee(rrr):
    return rrr / /2
"""


def test_merge3_simple_b():
    base_tm = _new_tm(python)
    d_local_tm = _new_tm(python)
    d_main_tm = _new_tm(python)
    base_tm.import_file(
"""def aaa(xxx):
    return xxx**2

def bbb(yyy):
    return yyy + 1

def ccc(zzz):
    return zzz / 2
""")
    d_local_tm.import_file(
"""def aaa(xxx):
    return xxx**2

def ddd(qqq, ggg):
    ggg += 42
    return qqq**ggg + 7

def ccc(zzz):
    return zzz / 2
""")
    d_main_tm.import_file(
"""def aaa(xxx):
    return xxx**2

def bbb(yyy):
    return yyy + 1

def eee(rrr, mmm):
    mmm -= 3
    return mmm, rrr * 2/7
""")
    assert base_tm.get_mainparser().last_status
    assert d_local_tm.get_mainparser().last_status
    assert d_main_tm.get_mainparser().last_status
    # for i in range(8):
    #     d_main_tm.key_cursors("down")
    # for i in range(22):
    #     d_main_tm.key_cursors("right")
    # d_main_tm.key_normal('/')

    merged_tm = _merge3(base_tm, d_local_tm, d_main_tm)

    text = merged_tm.export_as_text(None)

    assert text == \
"""def aaa(xxx):
    return xxx**2

def ddd(qqq, ggg):
    ggg += 42
    return qqq**ggg + 7

def eee(rrr, mmm):
    mmm -= 3
    return mmm, rrr * 2/7
"""

    assert merged_tm.get_mainparser().last_status


def test_merge3_arithmetic():
    base_tm = _new_tm(python)
    d_local_tm = _new_tm(python)
    d_main_tm = _new_tm(python)
    base_tm.import_file(
"""def aaa(x, y, z, w):
    return x + y
""")
    d_local_tm.import_file(
"""def aaa(x, y, z, w):
    return x*w + y
""")
    d_main_tm.import_file(
"""def aaa(x, y, z, w):
    return x + y*z
""")
    assert base_tm.get_mainparser().last_status
    assert d_local_tm.get_mainparser().last_status
    assert d_main_tm.get_mainparser().last_status

    merged_tm = _merge3(base_tm, d_local_tm, d_main_tm)

    text = merged_tm.export_as_text(None)

    assert text == \
"""def aaa(x, y, z, w):
    return x*w + y*z
"""

    assert merged_tm.get_mainparser().last_status


def test_merge3_list_literal():
    base_tm = _new_tm(python)
    d_local_tm = _new_tm(python)
    d_main_tm = _new_tm(python)
    base_tm.import_file(
"""def aaa(x, y, z, w):
    return [x, y]
""")
    d_local_tm.import_file(
"""def aaa(x, y, z, w):
    return [x, w, y]
""")
    d_main_tm.import_file(
"""def aaa(x, y, z, w):
    return [x, y, z]
""")
    assert base_tm.get_mainparser().last_status
    assert d_local_tm.get_mainparser().last_status
    assert d_main_tm.get_mainparser().last_status

    merged_tm = _merge3(base_tm, d_local_tm, d_main_tm)

    text = merged_tm.export_as_text(None)

    assert text == \
"""def aaa(x, y, z, w):
    return [x, w, y, z]
"""

    assert merged_tm.get_mainparser().last_status


def test_merge3_list_literal2():
    base_tm = _new_tm(python)
    d_local_tm = _new_tm(python)
    d_main_tm = _new_tm(python)
    base_tm.import_file(
"""def aaa(x, y, z, w):
    return [x, y, h]
""")
    d_local_tm.import_file(
"""def aaa(x, y, z, w):
    return [x, w, y, h]
""")
    d_main_tm.import_file(
"""def aaa(x, y, z, w):
    return [x, y, z, h]
""")
    assert base_tm.get_mainparser().last_status
    assert d_local_tm.get_mainparser().last_status
    assert d_main_tm.get_mainparser().last_status

    merged_tm = _merge3(base_tm, d_local_tm, d_main_tm)

    text = merged_tm.export_as_text(None)

    assert text == \
"""def aaa(x, y, z, w):
    return [x, w, y, z, h]
"""

    assert merged_tm.get_mainparser().last_status


def test_merge3_list_literal3():
    base_tm = _new_tm(python)
    d_local_tm = _new_tm(python)
    d_main_tm = _new_tm(python)
    base_tm.import_file(
"""def aaa(a, b, c, d, x, y, z, w):
    return [a, b, c, d]
""")
    d_local_tm.import_file(
"""def aaa(a, b, c, d, x, y, z, w):
    return [a, b, x, y, c, d]
""")
    d_main_tm.import_file(
"""def aaa(a, b, c, d, x, y, z, w):
    return [a, b, c, z, w, d]
""")
    assert base_tm.get_mainparser().last_status
    assert d_local_tm.get_mainparser().last_status
    assert d_main_tm.get_mainparser().last_status

    merged_tm = _merge3(base_tm, d_local_tm, d_main_tm)

    text = merged_tm.export_as_text(None)

    assert text == \
"""def aaa(a, b, c, d, x, y, z, w):
        return [a, b, x, y, c, z, w, d]
"""

    assert merged_tm.get_mainparser().last_status


def test_merge3_conflict_a():
    base_tm = _new_tm(python)
    d_local_tm = _new_tm(python)
    d_main_tm = _new_tm(python)
    base_tm.import_file(
"""def aaa(xxx):
    return xxx**2

def bbb(yyy):
    return yyy + 1

def ccc(zzz):
    return zzz / 2
""")
    d_local_tm.import_file(
"""def aaa(xxx):
    return xxx**2

def bbb(fff):
    return fff + 1

def ccc(zzz):
    return zzz / 2
""")
    d_main_tm.import_file(
"""def aaa(xxx):
    return xxx**2

def ddd(qqq, ggg):
    ggg += 42
    return qqq**ggg + 7

def eee(rrr, mmm):
    mmm -= 3
    return mmm, rrr * 2/7
""")
    assert base_tm.get_mainparser().last_status
    assert d_local_tm.get_mainparser().last_status
    assert d_main_tm.get_mainparser().last_status
    # for i in range(8):
    #     d_main_tm.key_cursors("down")
    # for i in range(22):
    #     d_main_tm.key_cursors("right")
    # d_main_tm.key_normal('/')

    merged_tm = _merge3(base_tm, d_local_tm, d_main_tm)

    text = merged_tm.export_as_text(None)

    assert text == \
"""def aaa(xxx):
    return xxx**2

def ddd(qqq, gggyyy):
    ggg += 42
    return qqq**yyy + 7

def eee(rrr, mmm):
    mmm -= 3
    return mmm, rrr * 2/7
"""

    # assert merged_tm.get_mainparser().last_status


if __name__ == '__main__':
    test_merge3_list_literal3()
    # test_indent_diff()