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

    assert merged_tm.get_mainparser().last_status


if __name__ == '__main__':
    test_merge3_conflict_a()