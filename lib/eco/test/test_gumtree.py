import ast
import pytest

from version_control.gumtree_driver import GumTreeMerger, gumtree_swingdiff, EcoTreeDocument as Doc,\
    EcoTreeNode as Node, EcoTreeNodeClass as NodeClass,\
    GumtreeDiffUpdate as DUpdate, GumtreeDiffDelete as DDelete, GumtreeDiffInsert as DInsert,\
    GumtreeDiffMove as DMove


class ASTConverter (object):
    def __init__(self):
        self._node_classes = {}

    def _get_node_class(self, ast_node):
        t = type(ast_node)
        try:
            return self._node_classes[t]
        except KeyError:
            cls = NodeClass(len(self._node_classes), t.__name__)
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


class Test_gumtree:
    def test_same(self):
        conv = ASTConverter()
        T0 = conv.parse('a')
        T1 = conv.parse('a')
        assert GumTreeMerger(T0).diff(T1) == []

        T0 = conv.parse('a+b')
        T1 = conv.parse('a+b')
        assert GumTreeMerger(T0).diff(T1) == []

        T0 = conv.parse('[a, b]')
        T1 = conv.parse('[a, b]')
        assert GumTreeMerger(T0).diff(T1) == []


    def test_update(self):
        conv = ASTConverter()
        T0 = conv.parse('a+b')
        T1 = conv.parse('a+x')
        assert GumTreeMerger(T0).diff(T1) == [DUpdate(T0[0][0][2], 'x')]

        T0 = conv.parse('[a, b]')
        T1 = conv.parse('[x, y]')
        assert GumTreeMerger(T0).diff(T1) == [DUpdate(T0[0][0][0], 'x'),
                                              DUpdate(T0[0][0][1], 'y')]

        T0 = conv.parse('[a, b+c]')
        T1 = conv.parse('[a, x+y]')
        assert GumTreeMerger(T0).diff(T1) == [DUpdate(T0[0][0][1][0], 'x'),
                                              DUpdate(T0[0][0][1][2], 'y')]


    def test_insert(self):
        conv = ASTConverter()
        T0 = conv.parse('[a, b]')
        T1 = conv.parse('[a, c, b]')
        assert GumTreeMerger(T0).diff(T1) == [DInsert(T1[0][0][1], T0[0][0], 1),
                                              DInsert(T1[0][0][1][0], T1[0][0][1], 0)]

        T0 = conv.parse('[a, b]')
        T1 = conv.parse('[a, c+d, b]')
        assert GumTreeMerger(T0).diff(T1) == [DInsert(T1[0][0][1], T0[0][0], 1),
                                              DInsert(T1[0][0][1][0], T1[0][0][1], 0),
                                              DInsert(T1[0][0][1][1], T1[0][0][1], 1),
                                              DInsert(T1[0][0][1][2], T1[0][0][1], 2),
                                              DInsert(T1[0][0][1][0][0], T1[0][0][1][0], 0),
                                              DInsert(T1[0][0][1][2][0], T1[0][0][1][2], 0)]


    def test_delete(self):
        conv = ASTConverter()
        T0 = conv.parse('[a, c, b]')
        T1 = conv.parse('[a, b]')
        assert GumTreeMerger(T0).diff(T1) == [DDelete(T0[0][0][1][0]),
                                              DDelete(T0[0][0][1])]

        T0 = conv.parse('[a, c+d, b]')
        T1 = conv.parse('[a, b]')
        assert GumTreeMerger(T0).diff(T1) == [DDelete(T0[0][0][1][0][0]),
                                              DDelete(T0[0][0][1][0]),
                                              DDelete(T0[0][0][1][1]),
                                              DDelete(T0[0][0][1][2][0]),
                                              DDelete(T0[0][0][1][2]),
                                              DDelete(T0[0][0][1])]


    def test_move(self):
        conv = ASTConverter()
        T0 = conv.parse('[a, x(b, c+d(e)/f+g, h), i, y(j, k+l(m)/n+o, p), q]')
        T1 = conv.parse('[a, x(b, c+d(e)/f+g, y(j, k+l(m)/n+o, p), h), i, q]')
        assert GumTreeMerger(T0).diff(T1) == [DMove(T0[0][0][3], T1[0][0][1], 3)]


    def test_all(self):
        conv = ASTConverter()
        T0 = conv.parse('[a, x(b, c+d(e)/f+g, h), i, y(j, k+l(m)/n+o, p), q]')
        T1 = conv.parse('[a, x(b, c+d(e)/f+g, y(j, k+l(m)/n+o, p), r), i, q]')
        assert GumTreeMerger(T0).diff(T1) == [DMove(T0[0][0][3], T1[0][0][1], 3),
                                              DUpdate(T0[0][0][1][3], 'r')]
