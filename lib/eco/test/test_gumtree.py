import ast
import pytest

from version_control.gumtree_driver import *


def _dupdate(node, value):
    return GumtreeDiffUpdate(None, node, value)
    
def _ddelete(node):
    return GumtreeDiffDelete(None, node)
    
def _dinsert(node, parent, index):
    return GumtreeDiffInsert(None, node, parent, index)
    
def _dmove(node, parent, index):
    return GumtreeDiffMove(None, node, parent, index)

def _diff3(base, derived1, derived2):
    merged, ops, conflict_ops, conflicts = gumtree_diff3(base, derived1, derived2)
    return merged, conflicts

class ASTConverter (object):
    """
    Python AST to Gumtree tree converter.
    """
    def __init__(self):
        self._node_classes = {}

    def _get_node_class(self, ast_node):
        t = type(ast_node)
        try:
            return self._node_classes[t]
        except KeyError:
            cls = GumtreeNodeClass(len(self._node_classes), t.__name__)
            self._node_classes[t] = cls
            return cls

    def _handle_ast_value(self, children, values, x):
        if isinstance(x, ast.AST):
            children.append(self._ast_to_tree(x))
        elif isinstance(x, (list, tuple)):
            for v in x:
                self._handle_ast_value(children, values, v)
        else:
            values.append(x)


    def _ast_to_tree(self, ast_node):
        children = []
        values = []
        for field_name in ast_node._fields:
            field_val = getattr(ast_node, field_name)
            self._handle_ast_value(children, values, field_val)
        node_class = self._get_node_class(ast_node)
        value = '_'.join([str(x) for x in values])
        return node_class.node(value, children)

    def parse(self, code):
        a = ast.parse(code)
        return self._ast_to_tree(a)


class Test_gumtree_diff:
    def test_diff_same(self):
        conv = ASTConverter()
        T0 = conv.parse('a')
        T1 = conv.parse('a')
        assert gumtree_diff(T0, T1) == []

        T0 = conv.parse('a+b')
        T1 = conv.parse('a+b')
        assert gumtree_diff(T0, T1) == []

        T0 = conv.parse('[a, b]')
        T1 = conv.parse('[a, b]')
        assert gumtree_diff(T0, T1) == []


    def test_diff_update(self):
        conv = ASTConverter()
        T0 = conv.parse('a+b')
        T1 = conv.parse('a+x')
        assert gumtree_diff(T0, T1) == [_dupdate(T0[0][0][2], 'x')]

        T0 = conv.parse('[a, b]')
        T1 = conv.parse('[x, y]')
        assert gumtree_diff(T0, T1) == [_dupdate(T0[0][0][0], 'x'),
                                        _dupdate(T0[0][0][1], 'y')]

        T0 = conv.parse('[a, b+c]')
        T1 = conv.parse('[a, x+y]')
        assert gumtree_diff(T0, T1) == [_dupdate(T0[0][0][1][0], 'x'),
                                        _dupdate(T0[0][0][1][2], 'y')]


    def test_diff_insert(self):
        conv = ASTConverter()
        T0 = conv.parse('[a, b]')
        T1 = conv.parse('[a, c, b]')
        assert gumtree_diff(T0, T1) == [_dinsert(T1[0][0][1], T0[0][0], 1),
                                        _dinsert(T1[0][0][1][0], T1[0][0][1], 0)]

        T0 = conv.parse('[a, b]')
        T1 = conv.parse('[a, c+d, b]')
        assert gumtree_diff(T0, T1) == [_dinsert(T1[0][0][1], T0[0][0], 1),
                                        _dinsert(T1[0][0][1][0], T1[0][0][1], 0),
                                        _dinsert(T1[0][0][1][1], T1[0][0][1], 1),
                                        _dinsert(T1[0][0][1][2], T1[0][0][1], 2),
                                        _dinsert(T1[0][0][1][0][0], T1[0][0][1][0], 0),
                                        _dinsert(T1[0][0][1][2][0], T1[0][0][1][2], 0)]


    def test_diff_delete(self):
        conv = ASTConverter()
        T0 = conv.parse('[a, c, b]')
        T1 = conv.parse('[a, b]')
        assert gumtree_diff(T0, T1) == [_ddelete(T0[0][0][1][0]),
                                        _ddelete(T0[0][0][1])]

        T0 = conv.parse('[a, c+d, b]')
        T1 = conv.parse('[a, b]')
        assert gumtree_diff(T0, T1) == [_ddelete(T0[0][0][1][0][0]),
                                        _ddelete(T0[0][0][1][0]),
                                        _ddelete(T0[0][0][1][1]),
                                        _ddelete(T0[0][0][1][2][0]),
                                        _ddelete(T0[0][0][1][2]),
                                        _ddelete(T0[0][0][1])]


    def test_diff_move(self):
        conv = ASTConverter()
        T0 = conv.parse('[a, x(b, c+d(e)/f+g, h), i, y(j, k+l(m)/n+o, p), q]')
        T1 = conv.parse('[a, x(b, c+d(e)/f+g, y(j, k+l(m)/n+o, p), h), i, q]')
        assert gumtree_diff(T0, T1) == [_dmove(T0[0][0][3], T1[0][0][1], 3)]

        conv = ASTConverter()
        T0 = conv.parse('[a, x(b, c+d(e)/f+g, h), i]')
        T1 = conv.parse('[a, i, x(b, c+d(e)/f+g, h)]')
        assert gumtree_diff(T0, T1) == [_dmove(T0[0][0][1], T1[0][0], 3)]

        conv = ASTConverter()
        T0 = conv.parse('[a, i, x(b, c+d(e)/f+g, h)]')
        T1 = conv.parse('[a, x(b, c+d(e)/f+g, h), i]')
        assert gumtree_diff(T0, T1) == [_dmove(T0[0][0][1], T1[0][0], 3)]


    def test_diff_all(self):
        conv = ASTConverter()
        T0 = conv.parse('[a, x(b, c+d(e)/f+g, h), i, y(j, k+l(m)/n+o, p), q]')
        T1 = conv.parse('[a, x(b, c+d(e)/f+g, y(j, k+l(m)/n+o, p), r), i, q]')
        assert gumtree_diff(T0, T1) == [_dmove(T0[0][0][3], T1[0][0][1], 3),
                                        _dupdate(T0[0][0][1][3], 'r')]


    def test_diff_examples(self):
        conv = ASTConverter()
        T0 = conv.parse("""
def gaussian(x, a, b, c):
    return a * np.exp(-(x-b)**2 / (2.0*c**2))

def softmax(x):
    b = np.exp(x)
    return b / b.sum()

def relu(x):
    return np.max(x, 0)
        """)
        T1 = conv.parse("""
def gaussian(x, a, b, c):
    return a * np.exp(-(x-b)**2 / (2.0*c**2))

def relu(x):
    return np.max(x, 0)

def softmax(x):
    b = np.exp(x)
    return b / b.sum()
        """)
        assert gumtree_diff(T0, T1) == [_dmove(T0[1], T1, 3)]
        # delta = gumtree_diff(T0, T1)
        # print delta[0]
        # print delta[0].pred_id, delta[0].succ_id
        # assert False



class Test_gumtree_diff3:
    def test_merge_same(self):
        conv = ASTConverter()
        T0 = conv.parse('a')
        T1 = conv.parse('a')
        T2 = conv.parse('a')
        Tm = conv.parse('a')
        assert _diff3(T0, T1, T2) == (Tm, [])

        T0 = conv.parse('a+b')
        T1 = conv.parse('a+b')
        T2 = conv.parse('a+b')
        Tm = conv.parse('a+b')
        assert _diff3(T0, T1, T2) == (Tm, [])

        T0 = conv.parse('[a, b]')
        T1 = conv.parse('[a, b]')
        T2 = conv.parse('[a, b]')
        Tm = conv.parse('[a, b]')
        assert _diff3(T0, T1, T2) == (Tm, [])


    def test_merge_update(self):
        conv = ASTConverter()
        T0 = conv.parse('[a, b, c, d, e]')
        T1 = conv.parse('[a, x, c, d, e]')
        T2 = conv.parse('[a, b, c, y, e]')
        Tm = conv.parse('[a, x, c, y, e]')
        assert _diff3(T0, T1, T2) == (Tm, [])

        conv = ASTConverter()
        T0 = conv.parse('[a, [b,c], d, [e,f], g]')
        T1 = conv.parse('[a, [x,y], d, [e,f], g]')
        T2 = conv.parse('[a, [b,c], d, [w,z], g]')
        Tm = conv.parse('[a, [x,y], d, [w,z], g]')
        assert _diff3(T0, T1, T2) == (Tm, [])

        conv = ASTConverter()
        T0 = conv.parse('[a, b, c, d, e]')
        T1 = conv.parse('[a, x, c, d, e]')
        T2 = conv.parse('[a, x, c, d, e]')
        Tm = conv.parse('[a, x, c, d, e]')
        assert _diff3(T0, T1, T2) == (Tm, [])

    def test_merge_delete(self):
        conv = ASTConverter()
        T0 = conv.parse('[a, b, c, d, e]')
        T1 = conv.parse('[a, c, d, e]')
        T2 = conv.parse('[a, b, c, e]')
        Tm = conv.parse('[a, c, e]')
        assert _diff3(T0, T1, T2) == (Tm, [])

        conv = ASTConverter()
        T0 = conv.parse('[a, b, c, d, e]')
        T1 = conv.parse('[a, c, d, e]')
        T2 = conv.parse('[a, c, d, e]')
        Tm = conv.parse('[a, c, d, e]')
        assert _diff3(T0, T1, T2) == (Tm, [])


    def test_merge_insert(self):
        conv = ASTConverter()
        T0 = conv.parse('[a, b, c, d, e]')
        T1 = conv.parse('[a, x, b, c, d, e]')
        T2 = conv.parse('[a, b, c, d, y, e]')
        Tm = conv.parse('[a, x, b, c, d, y, e]')
        assert _diff3(T0, T1, T2) == (Tm, [])

        conv = ASTConverter()
        T0 = conv.parse('[a, b, c, d, e]')
        T1 = conv.parse('[a, x, b, c, d, e]')
        T2 = conv.parse('[a, x, b, c, d, e]')
        Tm = conv.parse('[a, x, b, c, d, e]')
        assert _diff3(T0, T1, T2) == (Tm, [])


    def test_merge_move(self):
        conv = ASTConverter()
        T0 = conv.parse('[a, x(b, c+d(e)/f+g, h), i, y(j, k+l(m)/n+o, p), q, z(r, s+t(u)/v+w, aa), bb]')
        T1 = conv.parse('[a, x(b, c+d(e)/f+g, y(j, k+l(m)/n+o, p), h), i, q, z(r, s+t(u)/v+w, aa), bb]')
        T2 = conv.parse('[a, x(b, z(r, s+t(u)/v+w, aa), c+d(e)/f+g, h), i, y(j, k+l(m)/n+o, p), q, bb]')
        Tm = conv.parse('[a, x(b, z(r, s+t(u)/v+w, aa), c+d(e)/f+g, y(j, k+l(m)/n+o, p), h), i, q, bb]')
        assert _diff3(T0, T1, T2) == (Tm, [])

        conv = ASTConverter()
        T0 = conv.parse('[a, x(b, c+d(e)/f+g, h), i, y(j, k+l(m)/n+o, p), q, z(r, s+t(u)/v+w, aa), bb]')
        T1 = conv.parse('[a, x(b, c+d(e)/f+g, y(j, k+l(m)/n+o, p), h), i, q, z(r, s+t(u)/v+w, aa), bb]')
        T2 = conv.parse('[a, x(b, c+d(e)/f+g, y(j, k+l(m)/n+o, p), h), i, q, z(r, s+t(u)/v+w, aa), bb]')
        Tm = conv.parse('[a, x(b, c+d(e)/f+g, y(j, k+l(m)/n+o, p), h), i, q, z(r, s+t(u)/v+w, aa), bb]')
        assert _diff3(T0, T1, T2) == (Tm, [])


    def test_merge_all(self):
        # Update-delete
        conv = ASTConverter()
        T0 = conv.parse('[a, b, c, d, e]')
        T1 = conv.parse('[a, x, c, d, e]')
        T2 = conv.parse('[a, b, c, e]')
        Tm = conv.parse('[a, x, c, e]')
        assert _diff3(T0, T1, T2) == (Tm, [])

        # Update-insert
        conv = ASTConverter()
        T0 = conv.parse('[a, b, c, d, e]')
        T1 = conv.parse('[a, x, c, d, e]')
        T2 = conv.parse('[a, b, c, d, y, e]')
        Tm = conv.parse('[a, x, c, d, y, e]')
        assert _diff3(T0, T1, T2) == (Tm, [])

        # Delete-insert
        conv = ASTConverter()
        T0 = conv.parse('[a, b, c, d, e]')
        T1 = conv.parse('[a, c, d, e]')
        T2 = conv.parse('[a, b, c, d, y, e]')
        Tm = conv.parse('[a, c, d, y, e]')
        assert _diff3(T0, T1, T2) == (Tm, [])

        # Move-update
        conv = ASTConverter()
        T0 = conv.parse('[a, x(b, c+d(e)/f+g, h), i, y(j, k+l(m)/n+o, p), q, z(r, s+t(u)/v+w, aa), bb]')
        T1 = conv.parse('[a, x(b, c+d(e)/f+g, y(j, k+l(m)/n+o, p), h), i, q, z(r, s+t(u)/v+w, aa), bb]')
        T2 = conv.parse('[a, x(b, c+d(e)/f+g, h), i, y(j, k+l(hi)/n+o, p), q, z(r, s+t(u)/v+w, aa), bb]')
        Tm = conv.parse('[a, x(b, c+d(e)/f+g, y(j, k+l(hi)/n+o, p), h), i, q, z(r, s+t(u)/v+w, aa), bb]')
        assert _diff3(T0, T1, T2) == (Tm, [])

        conv = ASTConverter()
        T0 = conv.parse('[a, x(b, c+d(e)/f+g, h), y(j, k+l(m)/n+o, p)]')
        T1 = conv.parse('[a, y(j, k+l(m)/n+o, p), x(b, c+d(e)/f+g, h)]')
        T2 = conv.parse('[a, x(b, c+d(e)/f+g, q), y(j, k+l(m)/n+o, p)]')
        Tm = conv.parse('[a, y(j, k+l(m)/n+o, p), x(b, c+d(e)/f+g, q)]')
        assert _diff3(T0, T1, T2) == (Tm, [])

        # Move-insert
        conv = ASTConverter()
        T0 = conv.parse('[a, x(b, c+d(e)/f+g, h), i, y(j, k+l(m)/n+o, p), q, z(r, s+t(u)/v+w, aa), bb]')
        T1 = conv.parse('[a, x(b, c+d(e)/f+g, y(j, k+l(m)/n+o, p), h), i, q, z(r, s+t(u)/v+w, aa), bb]')
        T2 = conv.parse('[a, x(b, c+d(e)/f+g, h), i, y(j, k+l(m)/n+o, hi, p), q, z(r, s+t(u)/v+w, aa), bb]')
        Tm = conv.parse('[a, x(b, c+d(e)/f+g, y(j, k+l(m)/n+o, hi, p), h), i, q, z(r, s+t(u)/v+w, aa), bb]')
        assert _diff3(T0, T1, T2) == (Tm, [])

        # Move-delete
        conv = ASTConverter()
        T0 = conv.parse('[a, x(b, c+d(e)/f+g, h), i, y(j, k+l(m)/n+o, p), q, z(r, s+t(u)/v+w, aa), bb]')
        T1 = conv.parse('[a, x(b, c+d(e)/f+g, y(j, k+l(m)/n+o, p), h), i, q, z(r, s+t(u)/v+w, aa), bb]')
        T2 = conv.parse('[a, x(b, c+d(e)/f+g, h), i, y(j, k+l(m)/n+o), q, z(r, s+t(u)/v+w, aa), bb]')
        Tm = conv.parse('[a, x(b, c+d(e)/f+g, y(j, k+l(m)/n+o), h), i, q, z(r, s+t(u)/v+w, aa), bb]')
        assert _diff3(T0, T1, T2) == (Tm, [])


    def test_merge_examples(self):
        conv = ASTConverter()
        T0 = conv.parse("""
def gaussian(x, a, b, c):
    return a * np.exp(-(x-b)**2 / (2.0*c**2))

def softmax(x):
    b = np.exp(x)
    return b / b.sum()

def relu(x):
    return np.max(x, 0)
        """)
        T1 = conv.parse("""
def gaussian(x, a, b, c):
    return a * np.exp(-(x-b)**2 / (2.0*c**2))

def relu(x):
    return np.max(x, 0)

def softmax(x):
    b = np.exp(x)
    return b / b.sum()
        """)
        T2 = conv.parse("""
def gaussian(x, a, b, c):
    return a * np.exp(-(x-b)**2 / (2.0*c**2))

def softmax(x):
    e_x = np.exp(x)
    return e_x / e_x.sum()

def relu(x):
    return np.max(x, 0)
        """)
        Tm = conv.parse("""
def gaussian(x, a, b, c):
    return a * np.exp(-(x-b)**2 / (2.0*c**2))

def relu(x):
    return np.max(x, 0)

def softmax(x):
    e_x = np.exp(x)
    return e_x / e_x.sum()
        """)
        # assert _diff3(T0, T1, T2) == (Tm, [])
        merged = _diff3(T0, T1, T2)
        assert merged == (Tm, [])
