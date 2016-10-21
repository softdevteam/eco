# Copyright (c) 2012--2014 King's College London
# Created by the Software Development Team <http://soft-dev.org/>
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to
# deal in the Software without restriction, including without limitation the
# rights to use, copy, modify, merge, publish, distribute, sublicense, and/or
# sell copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
# FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS
# IN THE SOFTWARE.

from grammars.grammars import calc, java, python, Language, sql, pythonprolog, lang_dict, phppython, pythonphp
from treemanager import TreeManager
from incparser.incparser import IncParser
from inclexer.inclexer import IncrementalLexer
from incparser.astree import BOS, EOS
from grammar_parser.gparser import MagicTerminal
from utils import KEY_UP as UP, KEY_DOWN as DOWN, KEY_LEFT as LEFT, KEY_RIGHT as RIGHT

from PyQt4 import QtCore

import programs

import pytest
slow = pytest.mark.slow

if pytest.config.option.log:
    import logging
    logging.getLogger().setLevel(logging.DEBUG)

class Test_Typing:

    def setup_class(cls):
        parser, lexer = calc.load()
        cls.lexer = lexer
        cls.parser = parser
        cls.parser.init_ast()
        cls.ast = cls.parser.previous_version
        cls.treemanager = TreeManager()
        cls.treemanager.add_parser(cls.parser, cls.lexer, calc.name)

        cls.treemanager.set_font_test(7, 17) # hard coded. PyQt segfaults in test suite

    def reset(self):
        self.parser.reset()
        self.treemanager = TreeManager()
        self.treemanager.add_parser(self.parser, self.lexer, calc.name)
        self.treemanager.set_font_test(7, 17)

    def test_normaltyping(self):
        assert self.parser.last_status == False
        self.treemanager.key_normal("1")
        assert self.parser.last_status == True
        self.treemanager.key_normal("+")
        assert self.parser.last_status == False
        self.treemanager.key_normal("2")
        assert self.parser.last_status == True

    def test_cursormovement1(self):
        self.treemanager.key_home()
        assert isinstance(self.treemanager.cursor.node, BOS)
        self.treemanager.cursor_movement(RIGHT)
        assert self.treemanager.cursor.node.symbol.name == "1"
        self.treemanager.key_end()
        assert self.treemanager.cursor.node.symbol.name == "2"

    def test_normaltyping2(self):
        self.treemanager.key_normal("\r")
        assert self.treemanager.cursor.node.symbol.name == "\r"
        self.treemanager.key_normal("3")
        assert self.treemanager.cursor.node.symbol.name == "3"
        self.treemanager.key_normal("+")
        assert self.treemanager.cursor.node.symbol.name == "+"
        self.treemanager.key_normal("5")
        assert self.treemanager.cursor.node.symbol.name == "5"

    def test_cursormovement2(self):
        assert self.treemanager.cursor.node.symbol.name == "5"
        self.treemanager.key_end()
        assert self.treemanager.cursor.node.symbol.name == "5"
        self.treemanager.cursor_movement(UP)
        assert self.treemanager.cursor.node.symbol.name == "2"
        self.treemanager.cursor_movement(LEFT)
        assert self.treemanager.cursor.node.symbol.name == "+"
        self.treemanager.cursor_movement(DOWN)
        assert self.treemanager.cursor.node.symbol.name == "+"

    def test_deletion(self):
        import pytest
        self.treemanager.key_end()
        assert self.treemanager.cursor.node.symbol.name == "5"
        self.treemanager.key_backspace()
        assert self.treemanager.cursor.node.symbol.name == "+"
        self.treemanager.key_delete()
        assert self.treemanager.cursor.node.symbol.name == "+"
        self.treemanager.cursor_movement(LEFT)
        self.treemanager.key_delete()
        assert self.treemanager.cursor.node.symbol.name == "3"

    def test_cursor_reset(self):
        self.treemanager.cursor_reset()
        assert isinstance(self.treemanager.cursor.node, BOS)

    def test_delete_selection(self):
        self.reset()
        self.treemanager.key_normal("a")
        self.treemanager.key_shift()
        self.treemanager.key_cursors(LEFT, shift=True)
        assert self.treemanager.hasSelection()
        nodes, _, _ = self.treemanager.get_nodes_from_selection()
        self.treemanager.key_delete()

    def test_paste(self):
        self.reset()
        assert self.parser.last_status == False
        self.treemanager.pasteText("1 + 2\r+4+5\r+6+789")
        assert self.parser.last_status == True
        assert self.treemanager.cursor.node.symbol.name == "789"
        assert self.treemanager.cursor.pos == 3

    def test_colon_colon_equals(self):
        # typing colon colon equals makes the cursor disappear
        grammar = Language("grammar with colon",
"""
S ::= "a" "assign" "b"
""",
"""
"a":a
"b":b
"::=":assign
":":colon
"=":equal
""")
        lexer = IncrementalLexer(grammar.priorities)
        parser = IncParser(grammar.grammar, 1, True)
        parser.init_ast()
        ast = parser.previous_version
        treemanager = TreeManager()
        treemanager.add_parser(parser, lexer, grammar.name)
        treemanager.set_font_test(7, 17) # hard coded. PyQt segfaults in test suite

        treemanager.key_normal(":")
        assert treemanager.cursor.node.lookup == "colon"
        assert treemanager.cursor.node.symbol.name == ":"
        assert treemanager.cursor.node.lookahead == 1

        treemanager.key_normal(":")
        assert treemanager.cursor.node.lookup == "colon"
        assert treemanager.cursor.node.symbol.name == ":"
        assert treemanager.cursor.node.lookahead == 1

        treemanager.key_normal("=")

        assert treemanager.cursor.node.lookup == "assign"
        assert treemanager.cursor.node.symbol.name == "::="

    def test_fix_cursor_bug(self):
        grammar = Language("bug",
"""
S ::= "brack" "htm"
    | "html"
""",
"""
"<":brack
"htm":htm
"<html":html
""")
        lexer = IncrementalLexer(grammar.priorities)
        parser = IncParser(grammar.grammar, 1, True)
        parser.init_ast()
        ast = parser.previous_version
        treemanager = TreeManager()
        treemanager.add_parser(parser, lexer, grammar.name)
        treemanager.set_font_test(7, 17) # hard coded. PyQt segfaults in test suite

        treemanager.key_normal("<")
        treemanager.key_normal("h")
        treemanager.key_normal("t")
        treemanager.key_normal("m")
        assert treemanager.cursor.node.symbol.name == "htm"
        treemanager.key_normal("l")
        assert treemanager.cursor.node.symbol.name == "<html"
        treemanager.key_backspace()
        assert treemanager.cursor.node.symbol.name == "htm"

class Test_AST_Conversion(object):
    def setup_class(cls):
        pytest.skip("Skipped until new AST conversion is merged into Eco")

    def test_calculator(self):
        lexer = IncrementalLexer(calc_annotation.priorities)
        parser = IncParser(calc_annotation.grammar, 1, False)
        parser.init_ast()
        ast = parser.previous_version
        treemanager = TreeManager()
        treemanager.add_parser(parser, lexer, calc_annotation.name)
        treemanager.set_font_test(7, 17) # hard coded. PyQt segfaults in test suite

        inputstring = "1+2*3"
        for c in inputstring:
            treemanager.key_normal(c)
        parsetree = parser.previous_version.parent
        assert parsetree.symbol.name == "Root"
        # test normal parse tree
        E = parsetree.children[1]
        assert E.symbol.name == "E"

        E2 = E.children[0]
        plus = E.children[1]
        T = E.children[2]
        assert E2.symbol.name == "E"
        assert plus.symbol.name == "+"
        assert T.symbol.name == "T"

        assert E2.children[0].symbol.name == "T"
        assert E2.children[0].children[0].symbol.name == "P"
        assert E2.children[0].children[0].children[0].symbol.name == "1"

        assert T.children[0].symbol.name == "T"
        assert T.children[1].symbol.name == "*"
        assert T.children[2].symbol.name == "P"

        P = T.children[2]
        T = T.children[0]
        assert T.children[0].symbol.name == "P"
        assert T.children[0].children[0].symbol.name == "2"
        assert P.children[0].symbol.name == "3"

        # test AST
        plus = E.alternate
        assert plus.symbol.name == "+"
        assert plus.children[0].alternate.symbol.name == "1"
        assert plus.children[1].alternate.symbol.name == "*"

        T = plus.children[1]
        assert T.alternate.symbol.name == "*"
        assert T.children[0].alternate.symbol.name == "2"
        assert T.children[2].alternate.symbol.name == "3"
        # alternate children can be accessed in two ways
        times = T.alternate
        assert times.children[0].alternate.symbol.name == "2"
        assert times.children[1].alternate.symbol.name == "3"

    def test_johnstone_grammar(self):
        grammar = johnstone_grammar
        lexer = IncrementalLexer(grammar.priorities)
        parser = IncParser(grammar.grammar, 1, True)
        parser.init_ast()
        ast = parser.previous_version
        treemanager = TreeManager()
        treemanager.add_parser(parser, lexer, grammar.name)
        treemanager.set_font_test(7, 17) # hard coded. PyQt segfaults in test suite

        inputstring = "if(x<y)a=b else c=d"
        for c in inputstring:
            treemanager.key_normal(c)
        parsetree = parser.previous_version.parent
        assert parsetree.symbol.name == "Root"
        assert parsetree.children[1].symbol.name == "Startrule"
        startrule = parsetree.children[1]
        assert startrule.children[1].symbol.name == "S"
        assert startrule.children[1].alternate.symbol.name == "if"

        if_node = startrule.children[1].alternate
        assert if_node.children[0].alternate.symbol.name == "<"
        assert if_node.children[1].alternate.symbol.name == "="
        assert if_node.children[2].alternate.symbol.name == "="

        le = if_node.children[0].alternate
        assert le.children[0].alternate.symbol.name == "x"
        assert le.children[1].alternate.symbol.name == "y"
        eq1 = if_node.children[1].alternate
        assert eq1.children[0].symbol.name == "a" # 'a' wasn't folded so it doesn't have an alternative
        assert eq1.children[1].alternate.symbol.name == "b"
        eq2 = if_node.children[2].alternate
        assert eq2.children[0].symbol.name == "c" # same as 'a'
        assert eq2.children[1].alternate.symbol.name == "d"

    def test_python_bug(self):
        grammar = Language("Annotation test grammar",
"""
arith_expr ::= term^ arith_expr_loop^^
arith_expr_loop ::= arith_expr_loop "+^^" term^
                  | arith_expr_loop "-^^" term^
                  |
term ::= "1"
""",
"""
"1":1
"\+":+
"\-":-
""")
        lexer = IncrementalLexer(grammar.priorities)
        parser = IncParser(grammar.grammar, 1, True)
        parser.init_ast()
        ast = parser.previous_version
        treemanager = TreeManager()
        treemanager.add_parser(parser, lexer, grammar.name)
        treemanager.set_font_test(7, 17) # hard coded. PyQt segfaults in test suite

        inputstring = "1"
        for c in inputstring:
            treemanager.key_normal(c)

        state4 = parser.graph.state_sets[4]
        production = None
        for element in state4.elements:
            if element.p.left.name == "arith_expr":
                production = element.p
                break

        assert production.right[1].name == "arith_expr_loop"
        assert production.right[1].folding == "^^"
        treemanager.key_normal("+")
        assert production.right[1].name == "arith_expr_loop"
        assert production.right[1].folding == "^^"
        treemanager.key_normal("1")
        assert production.right[1].name == "arith_expr_loop"
        assert production.right[1].folding == "^^"

    def test_tear(self):
        grammar = Language("Tear Test",
"""
S ::= "a" "b" C^^^ D
C ::= "c"
D ::= "d"
""",
"""
"a":a
"b":b
"c":c
"d":d
""")
        lexer = IncrementalLexer(grammar.priorities)
        parser = IncParser(grammar.grammar, 1, False)
        parser.init_ast()
        ast = parser.previous_version
        treemanager = TreeManager()
        treemanager.add_parser(parser, lexer, grammar.name)
        treemanager.set_font_test(7, 17) # hard coded. PyQt segfaults in test suite

        inputstring = "abcd"
        for c in inputstring:
            treemanager.key_normal(c)

        parsetree = parser.previous_version.parent
        assert parsetree.symbol.name == "Root"

        assert parsetree.children[1].symbol.name == "S"
        S = parsetree.children[1]
        assert S.children[0].symbol.name == "a"
        assert S.children[1].symbol.name == "b"
        assert S.children[2].symbol.name == "C"
        assert S.children[3].symbol.name == "D"

        assert S.alternate.children[0].symbol.name == "a"
        assert S.alternate.children[1].symbol.name == "b"
        assert S.alternate.children[2].symbol.name == "D"

    def test_tear_and_insert(self):
        grammar = Language("Tear/Insert Test",
"""
S ::= "a" "b" C^^^ D C< "e"
C ::= "c"
D ::= "d"
""",
"""
"a":a
"b":b
"c":c
"d":d
"e":e
""")
        lexer = IncrementalLexer(grammar.priorities)
        parser = IncParser(grammar.grammar, 1, False)
        parser.init_ast()
        ast = parser.previous_version
        treemanager = TreeManager()
        treemanager.add_parser(parser, lexer, grammar.name)
        treemanager.set_font_test(7, 17) # hard coded. PyQt segfaults in test suite

        inputstring = "abcde"
        for c in inputstring:
            treemanager.key_normal(c)

        parsetree = parser.previous_version.parent
        assert parsetree.symbol.name == "Root"

        assert parsetree.children[1].symbol.name == "S"
        S = parsetree.children[1]
        assert S.children[0].symbol.name == "a"
        assert S.children[1].symbol.name == "b"
        assert S.children[2].symbol.name == "C"
        assert S.children[3].symbol.name == "D"
        assert S.children[4].symbol.name == "e"

        assert S.alternate.children[0].symbol.name == "a"
        assert S.alternate.children[1].symbol.name == "b"
        assert S.alternate.children[2].symbol.name == "D"
        assert S.alternate.children[3].symbol.name == "C"
        assert S.alternate.children[3].children[0].symbol.name == "c"
        assert S.alternate.children[4].symbol.name == "e"

    def test_tear_and_insert2(self):
        grammar = Language("Tear/Insert Test",
"""
S ::= "a" "b" C^^^ "d" "e" C< "f" "g"
    | "x" D^^^ "y" D< "z" "a" "b"
C ::= "c"
D ::= "d"
""",
"""
"a":a
"b":b
"c":c
"d":d
"e":e
"x":x
"y":y
"z":z
""")
        lexer = IncrementalLexer(grammar.priorities)
        parser = IncParser(grammar.grammar, 1, False)
        parser.init_ast()
        ast = parser.previous_version
        treemanager = TreeManager()
        treemanager.add_parser(parser, lexer, grammar.name)
        treemanager.set_font_test(7, 17) # hard coded. PyQt segfaults in test suite

        inputstring = "xdyzab"
        for c in inputstring:
            treemanager.key_normal(c)

        parsetree = parser.previous_version.parent
        assert parsetree.symbol.name == "Root"

        assert parsetree.children[1].symbol.name == "S"
        S = parsetree.children[1]
        assert S.children[0].symbol.name == "x"
        assert S.children[1].symbol.name == "D"
        assert S.children[2].symbol.name == "y"
        assert S.children[3].symbol.name == "z"
        assert S.children[4].symbol.name == "a"
        assert S.children[5].symbol.name == "b"

        assert S.alternate.children[0].symbol.name == "x"
        assert S.alternate.children[1].symbol.name == "y"
        assert S.alternate.children[2].symbol.name == "D"
        assert S.alternate.children[3].symbol.name == "z"
        assert S.alternate.children[4].symbol.name == "a"
        assert S.alternate.children[5].symbol.name == "b"

    def test_tear_and_insert_whitespace(self):
        grammar = Language("Tear/Insert Test",
"""
test ::= or_test^^
       | or_test^^^ "if" or_test or_test< "else"^ test

or_test ::= "1"^^
          | "2"^^
          | "3"^^
          | or_test "or"^^ "False"

""",
"""
"[ \\t]+":<ws>
"if":if
"else":else
"1":1
"2":2
"3":3
""")
        lexer = IncrementalLexer(grammar.priorities)
        parser = IncParser(grammar.grammar, 1, True)
        parser.init_ast()
        ast = parser.previous_version
        treemanager = TreeManager()
        treemanager.add_parser(parser, lexer, grammar.name)
        treemanager.set_font_test(7, 17) # hard coded. PyQt segfaults in test suite

        inputstring = "1 if 2 else 3"
        for c in inputstring:
            treemanager.key_normal(c)

        parsetree = parser.previous_version.parent
        assert parsetree.symbol.name == "Root"
        assert parsetree.children[1].symbol.name == "Startrule"

        assert parsetree.children[1].children[1].symbol.name == "test"
        test = parsetree.children[1].children[1]
        assert test.children[0].symbol.name == "or_test"
        assert test.children[1].symbol.name == "if"
        assert test.children[2].symbol.name == "WS"
        assert test.children[3].symbol.name == "or_test"
        assert test.children[4].symbol.name == "else"
        assert test.children[5].symbol.name == "WS"
        assert test.children[6].symbol.name == "test"

        assert test.alternate.children[0].symbol.name == "if"
        assert test.alternate.children[1].alternate.symbol.name == "2"
        assert test.alternate.children[2].alternate.symbol.name == "1"
        assert test.alternate.children[3].alternate.symbol.name == "3" # test -> or_test -> 3

    def test_sql_bug(self):
        grammar = sql

        lexer = IncrementalLexer(grammar.priorities)
        parser = IncParser(grammar.grammar, 1, True)
        parser.init_ast()
        ast = parser.previous_version
        treemanager = TreeManager()
        treemanager.add_parser(parser, lexer, grammar.name)
        treemanager.set_font_test(7, 17) # hard coded. PyQt segfaults in test suite

        inputstring = "SELECT * FROM test"
        for c in inputstring:
            treemanager.key_normal(c)

        assert parser.last_status == True

from grammars.grammars import EcoFile
class Test_General:

    def test_undo_bug(self):
        # Sometimes grammar changes can change subtrees that haven't been marked
        # as changed. As a consequence they are not marked with a version and
        # won't be reverted during an undo. This tests the fix in
        # incparser:reduce that version marks nodes whose parent has changed
        # during reparsing.
        grm = EcoFile("Undotest", "test/undobug1.eco", "Undo")
        t = TreeManager()
        parser, lexer = grm.load()
        t.add_parser(parser, lexer, python.name)

        t.key_normal("a")
        t.undo_snapshot()
        t.key_normal("b")
        t.undo_snapshot()
        t.key_normal("c")
        t.undo_snapshot()
        assert parser.last_status == True

        c = t.cursor.node
        assert c.symbol.name == "c"
        cp = c.parent

        t.key_cursors(LEFT)
        t.key_cursors(LEFT)
        t.key_normal("x")
        t.undo_snapshot()
        assert parser.last_status == True
        assert c.parent is not cp

        t.key_ctrl_z()
        assert parser.last_status == True

        assert c.parent is cp

class Test_Helper:
    def reset(self):
        self.parser.reset()
        self.treemanager = TreeManager()
        self.treemanager.add_parser(self.parser, self.lexer, python.name)
        self.treemanager.set_font_test(7, 17)

    def move(self, direction, times):
        for i in range(times): self.treemanager.cursor_movement(direction)

    def tree_compare(self, node1, node2):
        # XXX: test references (next_term, parent, lookup)
        while True:
            assert node1.symbol == node2.symbol
            if node1.right:
                assert node1.right.symbol == node2.right.symbol
            if node1.next_term:
                assert node1.next_term.symbol == node2.next_term.symbol
            if isinstance(node1.symbol, MagicTerminal):
                self.tree_compare(node1.symbol.ast, node2.symbol.ast)
            if isinstance(node1, EOS) and isinstance(node2, EOS):
                break
            node1 = self.next_node(node1)
            node2 = self.next_node(node2)

    def next_node(self, node):
        if node.children:
            return node.children[0]
        while(node.right_sibling() is None):
            node = node.parent
        return node.right_sibling()

class Test_Compare(Test_Helper):

    def test_compare(self):
        t = TreeManager()
        parser, lexer = python.load()
        t.add_parser(parser, lexer, python.name)
        inputstring = "class Test:\r    def x():\r        pass\r"
        t.import_file(inputstring)
        self.tree_compare(parser.previous_version.parent, parser.previous_version.parent)

    def test_compare2(self):
        t1 = TreeManager()
        parser1, lexer1 = python.load()
        t1.add_parser(parser1, lexer1, python.name)
        inputstring = "class Test:\r    def x():\r        pass\r"
        t1.import_file(inputstring)

        t2 = TreeManager()
        parser2, lexer2 = python.load()
        t2.add_parser(parser2, lexer2, python.name)
        inputstring = "class Test:\r    def x():\r        pass\r"
        t2.import_file(inputstring)

        self.tree_compare(parser1.previous_version.parent, parser2.previous_version.parent)

    def test_compare3(self):
        t1 = TreeManager()
        parser1, lexer1 = python.load()
        t1.add_parser(parser1, lexer1, python.name)
        inputstring = "class Test:\r    def x():\r    pass\r"
        t1.import_file(inputstring)

        t2 = TreeManager()
        parser2, lexer2 = python.load()
        t2.add_parser(parser2, lexer2, python.name)
        inputstring = "class Test:\r    def y():\r    pass\r"
        t2.import_file(inputstring)

        with pytest.raises(AssertionError):
            self.tree_compare(parser1.previous_version.parent, parser2.previous_version.parent)

class Test_Python(Test_Helper):
    def setup_class(cls):
        parser, lexer = python.load()
        cls.lexer = lexer
        cls.parser = parser
        cls.parser.init_ast()
        cls.ast = cls.parser.previous_version
        cls.treemanager = TreeManager()
        cls.treemanager.add_parser(cls.parser, cls.lexer, python.name)

        cls.treemanager.set_font_test(7, 17) # hard coded. PyQt segfaults in test suite

class Test_Boogie(Test_Python):
    def test_simple(self):
        for c in "class X:\r    p":
            self.treemanager.key_normal(c)

class Test_Bugs(Test_Python):

    def test_bug_goto(self):
        inputstring = "class Test:\r    def x():\r    pass\r"
        for c in inputstring:
            self.treemanager.key_normal(c)
        for i in range(4): self.treemanager.key_backspace() # remove whitespace (unindent)
        inputstring = "def y():"
        for c in inputstring:
            self.treemanager.key_normal(c)
        assert self.treemanager.cursor.node.symbol.name == ":"
        for i in range(8):
            self.treemanager.key_backspace() # shouldn't throw AssertionError goto != None

    def test_bug_goto2(self):
        self.reset()
        inputstring = "class Test:\r    def x():\r    print()\r"
        for c in inputstring:
            self.treemanager.key_normal(c)
        inputstring = "br"
        for c in inputstring:
            self.treemanager.key_normal(c)
        assert self.treemanager.cursor.node.symbol.name == "br"
        self.treemanager.key_backspace()
        self.treemanager.key_backspace() # shouldn't throw AssertionError goto != None

    def test_last_line_nonlogical(self):
        self.reset()
        inputstring = "class Test:\r    pass"
        for c in inputstring:
            self.treemanager.key_normal(c)
        assert self.parser.last_status == True
        self.treemanager.key_normal("\r")
        assert self.parser.last_status == True
        self.treemanager.key_backspace()
        self.treemanager.key_backspace()
        self.treemanager.key_backspace()
        self.treemanager.key_backspace()
        assert self.parser.last_status == True

    def test_type_and_remove(self):
        self.reset()
        self.treemanager.key_normal("c")
        self.treemanager.key_backspace() # shouldn't throw IndexError in repair_indentations

    def test_delete_all(self):
        self.reset()
        source = "x = 1"
        for c in source:
            self.treemanager.key_normal(c)
        assert self.parser.last_status == True
        for c in source:
            self.treemanager.key_backspace()
        assert self.parser.last_status == True
        for c in source:
            self.treemanager.key_normal(c)
        assert self.parser.last_status == True

    def test_select_and_paste(self):
        self.reset()
        source = "pass"
        for c in source:
            self.treemanager.key_normal(c)
        assert self.parser.last_status == True

        self.treemanager.key_end()
        self.treemanager.key_shift()
        self.treemanager.key_cursors(LEFT, True)
        self.treemanager.key_cursors(LEFT, True)
        self.treemanager.key_cursors(LEFT, True)
        self.treemanager.key_cursors(LEFT, True)
        self.treemanager.pasteText("back")
        assert self.treemanager.export_as_text() == "back"

        self.treemanager.key_home()
        self.treemanager.key_shift()
        self.treemanager.key_cursors(RIGHT, True)
        self.treemanager.key_cursors(RIGHT, True)
        self.treemanager.key_cursors(RIGHT, True)
        self.treemanager.key_cursors(RIGHT, True)
        self.treemanager.pasteText("again")
        assert self.treemanager.export_as_text() == "again"

        self.move(LEFT, 2)
        self.treemanager.doubleclick_select()
        self.treemanager.pasteText("test")
        assert self.treemanager.export_as_text() == "test"

class Test_Indentation(Test_Python):

    def test_indentation(self):
        assert self.parser.last_status == True
        inputstring = "class Test:\r    def x():\r    return x"
        for c in inputstring:
            self.treemanager.key_normal(c)
        assert self.parser.last_status == True

        self.treemanager.key_normal("\r")
        assert self.treemanager.cursor.node.symbol.name == "        "
        self.treemanager.key_backspace() # beware of auto indent
        self.treemanager.key_backspace()
        self.treemanager.key_backspace()
        self.treemanager.key_backspace()
        inputstring = "def y():\r    pass"
        for c in inputstring:
            self.treemanager.key_normal(c)

        assert self.parser.last_status == True

    def test_indentation_tokens(self):
        def check_next_nodes(node, l):
            for name in l:
                node = node.next_term
                assert node.symbol.name == name

        assert self.treemanager.lines[0].node.next_term.symbol.name == "class"

        node = self.treemanager.lines[1].node
        check_next_nodes(node, ["NEWLINE", "INDENT", "    ", "def"])

        node = self.treemanager.lines[2].node
        check_next_nodes(node, ["NEWLINE", "INDENT", "        ", "return"])

        node = self.treemanager.lines[3].node
        check_next_nodes(node, ["NEWLINE", "DEDENT", "    ", "def"])

        node = self.treemanager.lines[4].node
        check_next_nodes(node, ["NEWLINE", "INDENT", "        ", "pass", "NEWLINE", "DEDENT", "DEDENT", "eos"])

    def test_unexpected_indentation_after_bos(self):
        self.reset()
        inputstring = """test"""
        for i in inputstring:
            self.treemanager.key_normal(i)

        assert self.parser.last_status == True
        self.treemanager.key_home()
        self.treemanager.key_normal(" ")
        assert self.parser.last_status == False
        self.treemanager.key_backspace()
        assert self.parser.last_status == True

    def test_indentation_last_line(self):
        # change last line from unlogical to logical
        # dedents are now being created after \r not before eos
        self.reset()
        inputstring = """if x:
    x
"""
        self.treemanager.import_file(inputstring)
        assert self.parser.last_status == True
        self.move(DOWN, 2)
        self.treemanager.key_normal("z")
        assert self.parser.last_status == True

    def test_indentation2(self):
        self.reset()
        assert self.parser.last_status == True
        inputstring = """class Test:
    def x():
        return x
    def y():
        execute_something()
        for i in range(10):
            x = x + 1
            if x > 10:
                print("message")
                break
    def z():
        pass"""
        self.treemanager.import_file(inputstring)
        assert self.parser.last_status == True
        assert isinstance(self.treemanager.cursor.node, BOS)

        # move cursor to 'break'
        self.move(DOWN, 9)
        self.move(RIGHT, 16)

        assert self.treemanager.cursor.node.symbol.name == "                "
        assert self.treemanager.cursor.node.next_term.symbol.name == "break"

        # add space
        self.treemanager.key_normal(" ")
        assert self.parser.last_status == False
        # undo
        self.treemanager.key_backspace()
        assert self.parser.last_status == True

        # dedent 'break' 2 times
        # dedent 4 spaces
        self.treemanager.key_backspace()
        self.treemanager.key_backspace()
        self.treemanager.key_backspace()
        assert self.parser.last_status == False
        self.treemanager.key_backspace()
        assert self.parser.last_status == True
        # dedent 4 spaces
        self.treemanager.key_backspace()
        self.treemanager.key_backspace()
        self.treemanager.key_backspace()
        assert self.parser.last_status == False
        self.treemanager.key_backspace()
        assert self.parser.last_status == True

    def test_indentation3(self):
        self.reset()
        assert self.parser.last_status == True
        inputstring = """class Test:
    def x():
        return x
    def y():
        for i in range(10):
            x = x + 1
            if x > 10:
                print("message")
    def z():
        pass"""
        self.treemanager.import_file(inputstring)
        assert self.parser.last_status == True
        assert isinstance(self.treemanager.cursor.node, BOS)

        # move cursor to 'break'
        self.move(DOWN, 4)
        self.move(RIGHT, 8)

        # indent 'for' and 'x = x + 1'
        assert self.treemanager.cursor.node.next_term.symbol.name == "for"
        for i in range(4): self.treemanager.key_normal(" ")
        assert self.parser.last_status == False
        self.move(DOWN, 1)
        assert self.treemanager.cursor.node.next_term.symbol.name == "x"
        for i in range(4): self.treemanager.key_normal(" ")
        assert self.parser.last_status == True

    def test_indentation4(self):
        self.reset()
        assert self.parser.last_status == True
        inputstring = """class Test:
    def x():
        x = 1
        return x
    def y():
        y = 2
        return y
    def z():
        z = 3
        return z"""
        self.treemanager.import_file(inputstring)
        assert self.parser.last_status == True
        assert isinstance(self.treemanager.cursor.node, BOS)

        # move cursor to 'break'
        self.move(DOWN, 4)
        self.move(RIGHT, 4)

        # indent 'def y', 'y = 2' and 'return y'
        assert self.treemanager.cursor.node.next_term.symbol.name == "def"
        for i in range(4): self.treemanager.key_normal(" ")
        assert self.parser.last_status == False
        self.move(DOWN, 1)
        assert self.treemanager.cursor.node.next_term.symbol.name == "y"
        for i in range(4): self.treemanager.key_normal(" ")
        assert self.parser.last_status == True
        self.move(DOWN, 1)
        self.move(LEFT, 4)
        assert self.treemanager.cursor.node.next_term.symbol.name == "return"
        for i in range(4): self.treemanager.key_normal(" ")
        assert self.parser.last_status == True

    @slow
    def test_indentation_stresstest(self):
        import random
        self.reset()

        self.treemanager.import_file(programs.connect4)
        assert self.parser.last_status == True

        deleted = {}
        line_count = len(self.treemanager.lines)
        random_lines = range(line_count)
        random.shuffle(random_lines)
        for linenr in random_lines:
            whitespace = self.treemanager.get_indentation(linenr)
            if whitespace:
                del_ws = random.randint(0, whitespace)
                if del_ws > 0:
                    self.treemanager.cursor_reset()
                    self.move(DOWN, linenr)
                    self.move(RIGHT, del_ws)
                    assert self.treemanager.cursor.node.symbol.name == " " * whitespace
                    for i in range(del_ws):
                        self.treemanager.key_backspace()
                    deleted[linenr] = del_ws
        assert self.parser.last_status == False

        # undo
        for linenr in deleted:
            del_ws = deleted[linenr]
            self.treemanager.cursor_reset()
            self.move(DOWN, linenr)
            for i in range(del_ws):
                self.treemanager.key_normal(" ")
        assert self.parser.last_status == True

    def test_single_statement(self):
        self.reset()
        assert self.parser.last_status == True
        inputstring = """x = 12"""
        self.treemanager.import_file(inputstring)
        assert self.parser.last_status == True

    def test_line_becomes_first_line(self):
        self.reset()
        assert self.parser.last_status == True
        inputstring = """class X:\r    pass"""
        self.treemanager.import_file(inputstring)
        assert self.parser.last_status == True

        for i in range(13):
            self.treemanager.key_delete()

        assert self.parser.last_status == True

    def test_not_logical_lines(self):
        self.reset()
        inputstring = """class X(object):\r    def test():\r        return asd\r        \r    def relex(self, startnode):\r        pass"""

        self.treemanager.import_file(inputstring)
        assert self.parser.last_status == True

    def test_paste(self):
        self.reset()
        inputstring = """class X(object):\r    pass1\rx"""
        self.treemanager.import_file(inputstring)
        assert self.parser.last_status == True
        self.treemanager.key_end()
        assert self.treemanager.cursor.node.symbol.name == ":"
        self.treemanager.key_normal("\r")
        assert self.treemanager.cursor.node.symbol.name == "\r"
        self.treemanager.pasteText("""    if a:
        pass2
    pass3
if b:
    if c:
        pass4""")
        assert self.treemanager.cursor.node.symbol.name == "pass4"
        assert self.parser.last_status == True

    def test_bug(self):
        self.reset()
        inputstring = """class X(object):\rpass"""
        self.treemanager.import_file(inputstring)
        assert self.parser.last_status == False
        self.treemanager.cursor_movement(DOWN)
        self.treemanager.key_home()
        self.treemanager.key_normal(" ")
        assert self.parser.last_status == True

    def test_opt_push_last_before_eos_1(self):
        self.reset()
        inputstring = """class X:\r    def x():\r        pass\r    def y():\r        pass"""
        self.treemanager.import_file(inputstring)
        self.move(DOWN, 3)
        assert self.parser.last_status == True
        # delete whitespace before def y():
        self.treemanager.key_delete()
        self.treemanager.key_delete()
        self.treemanager.key_delete()
        assert self.parser.last_status == False
        self.treemanager.key_delete()
        assert self.parser.last_status == True
        # put whitespace back in
        self.treemanager.key_normal(" ")
        self.treemanager.key_normal(" ")
        self.treemanager.key_normal(" ")
        assert self.parser.last_status == False
        self.treemanager.key_normal(" ")
        assert self.parser.last_status == True

    def test_opt_push_last_before_eos_2(self):
        self.reset()
        inputstring = """class X:\r    def x():\r        pass\rdef y():\r        pass"""
        self.treemanager.import_file(inputstring)
        assert self.parser.last_status == True
        self.move(DOWN, 3)
        # insert whitespace before def y()
        self.treemanager.key_normal(" ")
        self.treemanager.key_normal(" ")
        self.treemanager.key_normal(" ")
        assert self.parser.last_status == False
        self.treemanager.key_normal(" ")
        assert self.parser.last_status == True
        self.treemanager.key_backspace()
        self.treemanager.key_backspace()
        self.treemanager.key_backspace()
        assert self.parser.last_status == False
        self.treemanager.key_backspace()
        assert self.parser.last_status == True

    def test_indentation_and_any_symbol(self):
        # when making a line unlogical, need to mark all newlines afterwards as changed
        # ??? only mark the first and last line as changed, and update the indent-attribute on all other <return>
        self.reset()
        inputstring = """def x():
    if x:
        x = \"\"\"
string
    else:
        y"""
        self.treemanager.import_file(inputstring)
        assert self.parser.last_status == False
        self.move(DOWN, 3)
        self.treemanager.key_end()
        self.treemanager.key_normal("\"")
        self.treemanager.key_normal("\"")
        self.treemanager.key_normal("\"")
        assert self.parser.last_status == True

    def test_indentation_bug(self):
        self.reset()
        inputstring = """class X:
    def x():
      pass
      def z():
        pass  
x()"""
        self.treemanager.import_file(inputstring)
        assert self.parser.last_status == True
        self.move(DOWN, 1)
        self.move(RIGHT, 4)
        self.treemanager.key_normal("    ")
        assert self.parser.last_status == False
        self.treemanager.key_shift()
        self.treemanager.key_cursors(LEFT, True)
        self.treemanager.key_cursors(LEFT, True)
        self.treemanager.key_cursors(LEFT, True)
        self.treemanager.key_cursors(LEFT, True)
        self.treemanager.key_backspace()
        assert self.parser.last_status == True

    def test_indentation_bug2(self):
        self.reset()
        inputstring = """class X:
    def y():
      if x:
        def x():
          pass
x()
"""
        self.treemanager.import_file(inputstring)
        assert self.parser.last_status == True
        self.move(DOWN, 3)
        self.treemanager.key_end()
        self.treemanager.key_normal("p")
        assert self.parser.last_status == False
        self.move(DOWN, 1)
        self.move(LEFT, 4)
        self.treemanager.key_shift()
        self.treemanager.key_cursors(LEFT, True)
        self.treemanager.key_cursors(LEFT, True)
        self.treemanager.key_cursors(LEFT, True)
        self.treemanager.key_cursors(LEFT, True)
        self.treemanager.key_backspace()
        assert self.parser.last_status == True

    def test_indentation_bug3(self):
        self.reset()
        inputstring = """def x():
    pass
x()
"""
        for k in inputstring:
            self.treemanager.key_normal(k)
        self.move(UP, 2)
        self.treemanager.key_home()
        assert self.parser.last_status == True
        self.treemanager.key_normal("    ")
        assert self.parser.last_status == False

    def test_indentation_multiline_bug(self):
        self.reset()
        inputstring = """class X:
    def x():
        s = 2
        pass1
    def x():
        pass2
def z():
    z"""
        self.treemanager.import_file(inputstring)
        assert self.parser.last_status == True
        self.move(DOWN, 4)
        self.treemanager.key_end()
        self.treemanager.key_normal("\"")
        self.treemanager.key_normal("\"")
        self.treemanager.key_normal("\"")
        self.move(UP, 2)
        self.treemanager.key_end()
        self.move(LEFT, 1)
        self.treemanager.key_normal("\"")
        self.treemanager.key_normal("\"")
        self.treemanager.key_normal("\"")
        assert self.parser.last_status == True
        # remove quotes again
        self.treemanager.key_backspace()
        self.treemanager.key_backspace()
        self.treemanager.key_backspace()
        self.move(DOWN, 2)
        self.treemanager.key_end()
        self.treemanager.key_backspace()
        self.treemanager.key_backspace()
        self.treemanager.key_backspace()
        assert self.parser.last_status == True

    def test_indentation_comment(self):
        self.reset()
        inputstring = """class X:
    # test
    pass"""
        self.treemanager.import_file(inputstring)
        assert self.parser.last_status == True
        

class Test_NestedLboxWithIndentation():
    def setup_class(cls):
        parser, lexer = calc.load()
        cls.lexer = lexer
        cls.parser = parser
        cls.parser.init_ast()
        cls.ast = cls.parser.previous_version
        cls.treemanager = TreeManager()
        cls.treemanager.add_parser(cls.parser, cls.lexer, calc.name)

        cls.treemanager.set_font_test(7, 17) # hard coded. PyQt segfaults in test suite

    def reset(self):
        self.parser.reset()
        self.treemanager = TreeManager()
        self.treemanager.add_parser(self.parser, self.lexer, calc.name)
        self.treemanager.set_font_test(7, 17)

    def test_simple(self):
        inputstring = "1+"
        for c in inputstring:
            self.treemanager.key_normal(c)
        self.treemanager.add_languagebox(lang_dict["Python 2.7.5"])
        inputstring = "def x():\r    pass"
        for c in inputstring:
            self.treemanager.key_normal(c)

        assert self.treemanager.parsers[1][2] == "Python 2.7.5"
        assert self.treemanager.parsers[1][0].last_status == True

    def test_remove_empty_lbox(self):
        # whitespace sensitive languages still contain indentation tokens when they are "empty"
        self.reset()
        self.treemanager.add_languagebox(lang_dict["Python 2.7.5"])
        self.treemanager.key_normal("a")
        self.treemanager.key_backspace()
        assert isinstance(self.treemanager.cursor.node, BOS)
        assert isinstance(self.treemanager.cursor.node.next_term, EOS)

#from grammars.grammars import lang_dict, python_prolog
class Test_Languageboxes(Test_Python):

    def setup_class(cls):
        parser, lexer = pythonprolog.load()
        cls.lexer = lexer
        cls.parser = parser
        cls.parser.init_ast()
        cls.ast = cls.parser.previous_version
        cls.treemanager = TreeManager()
        cls.treemanager.add_parser(cls.parser, cls.lexer, pythonprolog.name)

        cls.treemanager.set_font_test(7, 17) # hard coded. PyQt segfaults in test suite

    def test_simple(self):
        assert self.parser.last_status == True
        inputstring = "class Test:\r    def x():\r    return x"
        for c in inputstring:
            self.treemanager.key_normal(c)
        assert self.parser.last_status == True
        self.treemanager.key_backspace()
        assert self.parser.last_status == True
        self.treemanager.add_languagebox(lang_dict["Prolog"])
        assert self.parser.last_status == True
        assert self.treemanager.parsers[1][2] == "Prolog"
        assert self.treemanager.parsers[1][0].last_status == False
        self.treemanager.key_normal("x")
        assert self.treemanager.parsers[1][0].last_status == False
        self.treemanager.key_normal(".")
        assert self.treemanager.parsers[1][0].last_status == True

    def test_backspace_return_in_box(self):
        self.reset()
        inputstring = "class Test:\r    def x():\r    return x"
        for c in inputstring:
            self.treemanager.key_normal(c)
        self.treemanager.key_backspace()
        self.treemanager.add_languagebox(lang_dict["Prolog"])
        self.treemanager.key_normal("x")
        self.treemanager.key_normal("\r")
        for i in range(8):
            self.treemanager.key_backspace()

    def test_lbox_skips_newline(self):
        # when inserting a languagebox at the line beginning the next token
        # skips NEWLINE tokens. It should only skip INDENT/DEDENT
        self.reset()
        self.treemanager.key_normal("a") # needs to be valid once
        assert self.treemanager.parsers[0][0].last_status == True
        self.treemanager.key_backspace()
        self.treemanager.add_languagebox(lang_dict["Prolog"])
        self.treemanager.key_normal("a")
        self.treemanager.key_normal(".")
        self.treemanager.leave_languagebox()
        self.treemanager.key_normal(".")
        self.treemanager.key_normal("x")
        assert self.treemanager.parsers[0][0].last_status == True

    def test_delete_selection(self):
        self.reset()
        for c in "a = 1":
            self.treemanager.key_normal(c)
        self.treemanager.key_normal("\r")
        self.treemanager.add_languagebox(lang_dict["Prolog"])
        lbox = self.treemanager.cursor.node.get_root().get_magicterminal()
        assert lbox.symbol.name == "<Prolog>"
        for c in "abc def":
            self.treemanager.key_normal(c)
        self.treemanager.key_cursors(LEFT)
        # select "bc de"
        self.treemanager.key_shift()
        self.treemanager.key_cursors(LEFT, shift=True)
        self.treemanager.key_cursors(LEFT, shift=True)
        self.treemanager.key_cursors(LEFT, shift=True)
        self.treemanager.key_cursors(LEFT, shift=True)
        self.treemanager.key_cursors(LEFT, shift=True)
        self.treemanager.deleteSelection()
        assert lbox.symbol.name == "<Prolog>"

    def test_auto_indent(self):
        self.reset()
        self.treemanager.add_languagebox(lang_dict["Prolog"])
        for c in "abc:\r    def":
            self.treemanager.key_normal(c)
        self.treemanager.leave_languagebox()
        self.treemanager.key_normal("\r")
        self.treemanager.key_normal("a")
        assert self.treemanager.export_as_text() == "abc:\n    def\na"

    def test_auto_indent2(self):
        self.reset()
        self.treemanager.add_languagebox(lang_dict["Prolog"])
        for c in "abc:\r    def":
            self.treemanager.key_normal(c)
        self.treemanager.key_normal("\r")
        self.treemanager.add_languagebox(lang_dict["Python 2.7.5"])
        for c in "def x():\r        pass":
            self.treemanager.key_normal(c)
        self.treemanager.leave_languagebox()
        self.treemanager.key_normal("\r")
        self.treemanager.key_normal("a")
        assert self.treemanager.export_as_text() == "abc:\n    def\n    def x():\n        pass\n    a"

class Test_Backslash(Test_Python):

    def test_parse(self):
        self.reset()

        program = """class X:\r    def x():\r        return \\\r            [1,2,3]"""

        for c in program:
            self.treemanager.key_normal(c)
        assert self.parser.last_status == True

    def test_parse_fail(self):
        self.reset()

        program = """class X:\r    def x():\r        return \\ \r            [1,2,3]"""

        for c in program:
            self.treemanager.key_normal(c)
        assert self.parser.last_status == False

    def test_parse_delete_insert(self):
        self.reset()

        program = """class X:\r    def x():\r        return \\\r            [1,2,3]"""

        for c in program:
            self.treemanager.key_normal(c)

        assert self.parser.last_status == True
        self.move(UP, 1)
        self.treemanager.key_end()
        self.treemanager.key_backspace()
        assert self.parser.last_status == False
        self.treemanager.key_normal("\\")
        assert self.parser.last_status == True

class Test_Java:
    def setup_class(cls):
        parser, lexer = java.load()
        cls.lexer = lexer
        cls.parser = parser
        cls.parser.init_ast()
        cls.ast = cls.parser.previous_version
        cls.treemanager = TreeManager()
        cls.treemanager.add_parser(cls.parser, cls.lexer, java.name)

        cls.treemanager.set_font_test(7, 17) # hard coded. PyQt segfaults in test suite

    def reset(self):
        self.parser.reset()
        self.treemanager = TreeManager()
        self.treemanager.add_parser(self.parser, self.lexer, python.name)
        self.treemanager.set_font_test(7, 17)

    def move(self, direction, times):
        for i in range(times): self.treemanager.cursor_movement(direction)

    def test_incparse_optshift_bug(self):
        prog = """class Test {\r    public static void main() {\r        String y = z;\r    }\r}"""
        for c in prog:
            self.treemanager.key_normal(c)
        assert self.parser.last_status == True
        self.move(LEFT, 1)
        self.move(UP, 3)
        self.treemanager.key_end()
        self.treemanager.key_normal("\r")
        for c in "int x = 1;":
            self.treemanager.key_normal(c)
        assert self.parser.last_status == True

class Test_Undo(Test_Python):

    def reset(self):
        Test_Python.reset(self)
        self.treemanager.version = 1
        self.treemanager.last_saved_version = 1

    def compare(self, text):
        import tempfile
        f = tempfile.NamedTemporaryFile()
        result = self.treemanager.export_as_text("/tmp/temp.py")
        assert result == text
        f.close()

    def type_save(self, text):
        self.treemanager.key_normal(text)
        self.treemanager.undo_snapshot() # tells treemanager to save after the next operation and increase the version

    def save(self):
        self.treemanager.version += 1
        self.treemanager.save()

    def test_simple_undo_redo(self):
        self.treemanager.key_normal("1")
        self.treemanager.undo_snapshot()
        self.treemanager.key_normal("+")
        self.treemanager.undo_snapshot()
        self.treemanager.key_normal("2")
        self.compare("1+2")
        self.treemanager.key_ctrl_z()
        self.compare("1+")
        self.treemanager.key_ctrl_z()
        self.compare("1")
        self.treemanager.key_ctrl_z()
        self.compare("")

        self.treemanager.key_shift_ctrl_z()
        self.compare("1")
        self.treemanager.key_shift_ctrl_z()
        self.compare("1+")
        self.treemanager.key_shift_ctrl_z()
        self.compare("1+2")

    def test_undo_indentation(self):
        self.reset()
        self.type_save("class")
        self.type_save(" X:")
        self.type_save("\r    ")
        self.type_save("pass")
        self.compare("class X:\n    pass")

        self.treemanager.key_ctrl_z()
        self.compare("class X:\n    ")

        self.treemanager.key_ctrl_z()
        self.compare("class X:")
        # with the new indentation that NEWLINE is only added after a successful parse
        #assert self.treemanager.cursor.node.next_term.symbol.name == "NEWLINE"
        #assert isinstance(self.treemanager.cursor.node.next_term.next_term, EOS)

        self.treemanager.key_ctrl_z()
        self.compare("class")

        self.treemanager.key_shift_ctrl_z()
        self.treemanager.key_shift_ctrl_z()
        self.treemanager.key_shift_ctrl_z()
        self.compare("class X:\n    pass")
        assert self.treemanager.cursor.node.next_term.symbol.name == "NEWLINE"
        assert self.treemanager.cursor.node.next_term.next_term.symbol.name == "DEDENT"
        assert isinstance(self.treemanager.cursor.node.next_term.next_term.next_term, EOS)

    def test_undo_and_type(self):
        self.reset()
        self.type_save("12")
        self.type_save("+")
        self.type_save("34")
        self.compare("12+34")

        self.treemanager.key_ctrl_z()
        self.treemanager.key_ctrl_z()
        self.compare("12")
        self.type_save("-56")
        self.compare("12-56")

        self.treemanager.key_shift_ctrl_z()
        self.compare("12-56")

    def test_redo_bug(self):
        self.reset()
        self.type_save("1")
        self.type_save("\r")
        self.type_save("2")
        self.move(UP, 1)
        self.compare("1\n2")
        self.type_save("\r")
        self.type_save("3")
        self.compare("1\n3\n2")

        self.treemanager.key_ctrl_z()
        self.treemanager.key_ctrl_z()
        self.treemanager.key_ctrl_z()
        self.treemanager.key_ctrl_z()
        self.compare("1")

        self.treemanager.key_shift_ctrl_z()
        self.treemanager.key_shift_ctrl_z()
        self.treemanager.key_shift_ctrl_z()
        self.treemanager.key_shift_ctrl_z()
        self.compare("1\n3\n2")

        self.move(DOWN, 1)
        self.treemanager.key_backspace()
        self.compare("1\n3\n")
        self.treemanager.key_backspace()
        self.compare("1\n3")
        self.treemanager.key_backspace()
        self.compare("1\n")
        self.treemanager.key_backspace()
        self.compare("1")

    def test_redo_bug2(self):
        self.reset()
        self.type_save("1")
        self.type_save("+")
        self.type_save("2")
        self.move(LEFT, 2)
        self.compare("1+2")
        self.treemanager.key_delete()
        self.treemanager.undo_snapshot()
        self.compare("12")

        self.treemanager.key_ctrl_z()
        self.compare("1+2")
        self.treemanager.key_ctrl_z()
        self.compare("1+")
        self.treemanager.key_ctrl_z()
        self.compare("1")

        self.treemanager.key_shift_ctrl_z()
        self.compare("1+")
        self.treemanager.key_shift_ctrl_z()
        self.compare("1+2")
        self.treemanager.key_shift_ctrl_z()
        self.compare("12")

    def test_bug_lingering_nodes(self):
        self.reset()
        p = """class X:
    def foo():
        return 23"""
        self.treemanager.import_file(p)
        self.treemanager.key_end()
        self.move(LEFT, 1)
        self.treemanager.key_normal("s")
        self.treemanager.undo_snapshot()
        dp = self.copy()

        self.move(DOWN, 2)
        self.treemanager.key_end()
        self.move(LEFT, 1)
        self.treemanager.key_normal("+")
        self.treemanager.undo_snapshot()

        self.treemanager.key_ctrl_z()

        self.text_compare("""class Xs:
    def foo():
        return 23""")
        self.tree_compare(self.parser.previous_version.parent, dp)

    def test_bug_lingering_after_redo(self):
        self.reset()

        p = """class X:
    def x():
        pass

    def y():
        pass"""

        ast = self.parser.previous_version
        self.treemanager.import_file(p)
        imp = self.copy()
        imptext = self.treemanager.export_as_text()

        self.treemanager.key_end()
        self.move(LEFT, 1)
        self.treemanager.key_normal("a")
        self.treemanager.undo_snapshot()
        a = self.copy()
        atext = self.treemanager.export_as_text()

        self.move(DOWN, 1)
        self.treemanager.key_end()
        self.move(LEFT, 3)
        self.treemanager.key_normal("b")
        self.treemanager.undo_snapshot()
        b = self.copy()
        btext = self.treemanager.export_as_text()

        self.move(DOWN, 1)
        self.treemanager.key_end()
        self.treemanager.key_normal("c")
        self.treemanager.undo_snapshot()
        #c = self.copy()
        ctext = self.treemanager.export_as_text()

        self.move(DOWN, 2)
        self.treemanager.key_end()
        self.move(LEFT, 3)
        self.treemanager.key_normal("d")
        self.treemanager.undo_snapshot()
        #d = self.copy()
        dtext = self.treemanager.export_as_text()

        self.move(DOWN, 1)
        self.treemanager.key_end()
        self.treemanager.key_normal("e")
        self.treemanager.undo_snapshot()
        #e = self.copy()
        etext = self.treemanager.export_as_text()

        self.treemanager.key_ctrl_z()
        #self.tree_compare(ast.parent, d)
        self.treemanager.key_ctrl_z()
        #self.tree_compare(ast.parent, c)
        self.treemanager.key_ctrl_z()
        #self.tree_compare(ast.parent, b)
        self.treemanager.key_ctrl_z()
        #self.tree_compare(ast.parent, a)
        self.treemanager.key_ctrl_z()
        #self.tree_compare(ast.parent, imp)

        self.treemanager.key_shift_ctrl_z()
        #self.tree_compare(ast.parent, a)
        self.treemanager.key_shift_ctrl_z()
        #self.tree_compare(ast.parent, b)
        self.treemanager.key_shift_ctrl_z()
        #self.tree_compare(ast.parent, c)
        self.treemanager.key_shift_ctrl_z()
        #self.tree_compare(ast.parent, d)
        self.treemanager.key_shift_ctrl_z()
        #self.tree_compare(ast.parent, e)

        self.text_compare(etext)
        self.treemanager.key_ctrl_z()
        self.text_compare(dtext)
        #self.tree_compare(ast.parent, d)
        self.treemanager.key_ctrl_z()
        self.text_compare(ctext)
        #self.tree_compare(ast.parent, c)
        self.treemanager.key_ctrl_z()
        self.text_compare(btext)
        #self.tree_compare(ast.parent, b)
        self.treemanager.key_ctrl_z()
        self.text_compare(atext)
        #self.tree_compare(ast.parent, a)
        self.treemanager.key_ctrl_z()
        self.text_compare(imptext)
        #self.tree_compare(ast.parent, imp)

    def text_compare(self, original):
        original = original.replace("\r", "").split("\n")
        current = self.treemanager.export_as_text("/dev/null").replace("\r", "").split("\n")

        for i in xrange(len(current)):
            assert original[i] == current[i]

    def copy(self):
        import copy
        return copy.deepcopy(self.parser.previous_version.parent)

    def test_import(self):
        self.reset() # saves automatically

        self.treemanager.import_file("class X:\n    def x():\n         pass") # saves automatically
        self.move(DOWN, 2)
        self.treemanager.key_end()
        self.treemanager.key_normal("1")
        self.compare("class X:\n    def x():\n         pass1")
        self.treemanager.key_ctrl_z()
        self.compare("class X:\n    def x():\n         pass")

    def test_overflow(self):
        self.reset() # this saves the inital version as 1
        min_version = self.treemanager.version
        self.treemanager.import_file("class X:\n    def x():\n        pass")
        max_version = self.treemanager.version

        self.treemanager.key_ctrl_z()
        self.treemanager.key_ctrl_z()
        self.treemanager.key_ctrl_z()
        self.treemanager.key_ctrl_z()
        self.treemanager.key_ctrl_z()
        self.treemanager.key_ctrl_z()
        assert self.treemanager.version == min_version

        self.treemanager.key_shift_ctrl_z()
        self.treemanager.key_shift_ctrl_z()
        self.treemanager.key_shift_ctrl_z()
        self.treemanager.key_shift_ctrl_z()
        self.treemanager.key_shift_ctrl_z()
        self.treemanager.key_shift_ctrl_z()
        assert self.treemanager.version == max_version

    @slow
    def test_undo_random_deletion(self):
        import random
        self.reset()

        self.treemanager.import_file(programs.connect4)
        assert self.parser.last_status == True

        self.text_compare(programs.connect4)

        line_count = len(self.treemanager.lines)
        random_lines = range(line_count)
        random.shuffle(random_lines)

        start_version = self.treemanager.version
        for linenr in random_lines:
            cols = range(20)
            random.shuffle(cols)
            for col in cols:
                self.treemanager.cursor_reset()
                print("self.treemanager.cursor_reset()")
                self.move(DOWN, linenr)
                print("self.move(DOWN, %s)" % linenr)
                self.move(RIGHT, col)
                print("self.move(RIGHT, %s)" % col)
                x = self.treemanager.key_delete()
                print("self.treemanager.key_delete()")
                if x == "eos":
                    continue
            self.treemanager.undo_snapshot()
            print("self.treemanager.undo_snapshot()")

        end_version = self.treemanager.version
        broken = self.treemanager.export_as_text()

        # undo all and compare with original
        while self.treemanager.version > start_version:
            self.treemanager.key_ctrl_z()
        self.text_compare(programs.connect4)

        # redo all and compare with broken
        while self.treemanager.version < end_version:
            self.treemanager.key_shift_ctrl_z()
        self.text_compare(broken)

        # undo again and compare with original
        while self.treemanager.version > start_version:
            self.treemanager.key_ctrl_z()
        self.text_compare(programs.connect4)

        t1 = TreeManager()
        parser, lexer = python.load()
        parser.init_ast()
        t1.add_parser(parser, lexer, python.name)
        t1.set_font_test(7, 17)
        t1.import_file(programs.connect4)

        assert self.parser.last_status == True
        assert parser.last_status == True

        self.tree_compare(self.parser.previous_version.parent, parser.previous_version.parent)

    def test_undo_random_deletion_bug1(self):
        self.reset()

        src = """class X:
    def _end(self, winner_colour=None):
        for i in self.insert_buttons:
            i["state"] = tk.DISABLED
        """
        self.treemanager.import_file(src)
        assert self.parser.last_status == True

        self.text_compare(src)
        start_version = self.treemanager.version

        self.treemanager.cursor_reset()
        self.move(DOWN, 3)
        self.move(RIGHT, 12)
        self.treemanager.key_delete()
        self.treemanager.cursor_reset()
        self.move(DOWN, 3)
        self.move(RIGHT, 19)
        self.treemanager.key_delete()

        self.treemanager.undo_snapshot()

        while self.treemanager.version > start_version:
            self.treemanager.key_ctrl_z()
        self.text_compare(src)


    def test_undo_random_deletion_infitite_loop(self):
        pass

    def get_random_key(self):
        import random
        keys = list("abcdefghijklmnopqrstuvwxyz0123456789 \r:,.[]{}()!$%^&*()_+=")
        return random.choice(keys)

    @slow
    def test_undo_random_insertion(self):
        import random
        self.reset()

        self.treemanager.import_file(programs.connect4)
        assert self.parser.last_status == True

        self.text_compare(programs.connect4)

        line_count = len(self.treemanager.lines)
        random_lines = range(line_count)
        random.shuffle(random_lines)

        start_version = self.treemanager.version
        for linenr in random_lines:
            cols = range(20)
            random.shuffle(cols)
            for col in cols:
                self.treemanager.cursor_reset()
                self.move(DOWN, linenr)
                self.move(RIGHT, col)
                k = self.get_random_key()
                x = self.treemanager.key_normal(k)
                if x == "eos":
                    continue
            self.treemanager.undo_snapshot()

        end_version = self.treemanager.version
        broken = self.treemanager.export_as_text()

        # undo all and compare with original
        while self.treemanager.version > start_version:
            self.treemanager.key_ctrl_z()
        self.text_compare(programs.connect4)

        # redo all and compare with broken
        while self.treemanager.version < end_version:
            self.treemanager.key_shift_ctrl_z()
        self.text_compare(broken)

        # undo again and compare with original
        while self.treemanager.version > start_version:
            self.treemanager.key_ctrl_z()
        self.text_compare(programs.connect4)

        t1 = TreeManager()
        parser, lexer = python.load()
        t1.add_parser(parser, lexer, python.name)
        t1.import_file(programs.connect4)

        self.tree_compare(self.parser.previous_version.parent, parser.previous_version.parent)

    def test_undo_random_newlines(self):
        import random
        self.reset()

        p = """class X:
    def helloworld(x, y, z):
        for x in range(0, 10):
            if x == 1:
                return 1
            else:
                return 12
        return 13

    def foo(x):
        x = 1
        y = 2
        foo()
        return 12"""
        self.treemanager.import_file(p)
        assert self.parser.last_status == True

        self.text_compare(p)

        line_count = len(self.treemanager.lines)
        random_lines = range(line_count)
        random.shuffle(random_lines)

        start_version = self.treemanager.version
        for linenr in random_lines[:2]:
            cols = range(20)
            random.shuffle(cols)
            for col in cols[:1]: # add one newline per line
                self.treemanager.cursor_reset()
                self.move(DOWN, linenr)
                self.move(RIGHT, col)
                x = self.treemanager.key_normal("\r")
                if x == "eos":
                    continue
            self.treemanager.undo_snapshot()

        end_version = self.treemanager.version
        broken = self.treemanager.export_as_text()

        # undo all and compare with original
        while self.treemanager.version > start_version:
            self.treemanager.key_ctrl_z()
        self.text_compare(p)

        # redo all and compare with broken
        while self.treemanager.version < end_version:
            self.treemanager.key_shift_ctrl_z()
        self.text_compare(broken)

        # undo again and compare with original
        while self.treemanager.version > start_version:
            self.treemanager.key_ctrl_z()
        self.text_compare(p)

        t1 = TreeManager()
        parser, lexer = python.load()
        t1.add_parser(parser, lexer, python.name)
        t1.import_file(p)

        self.text_compare(t1.export_as_text())

        self.tree_compare(self.parser.previous_version.parent, parser.previous_version.parent)

    def test_bug_insert_newline_2(self):
        import random
        self.reset()

        p = """class X:
    def helloworld():
        for x in y:
            if x:
                return 1
            else:
                return 12
        return 13"""
        self.treemanager.import_file(p)
        assert self.parser.last_status == True

        self.text_compare(p)

        line_count = len(self.treemanager.lines)
        random_lines = range(line_count)
        random.shuffle(random_lines)

        start_version = self.treemanager.version

        self.treemanager.cursor_reset()
        self.move(DOWN, 4)
        self.move(RIGHT, 1)
        self.treemanager.key_normal("\r")
        self.treemanager.undo_snapshot()

        self.treemanager.cursor_reset()
        self.move(DOWN, 6)
        self.move(RIGHT, 1)
        self.treemanager.key_normal("\r")
        self.treemanager.undo_snapshot()

        end_version = self.treemanager.version
        broken = self.treemanager.export_as_text()

        # undo all and compare with original
        while self.treemanager.version > start_version:
            self.treemanager.key_ctrl_z()
        self.text_compare(p)

        # redo all and compare with broken
        while self.treemanager.version < end_version:
            self.treemanager.key_shift_ctrl_z()
        self.text_compare(broken)

        # undo again and compare with original
        while self.treemanager.version > start_version:
            self.treemanager.key_ctrl_z()
        self.text_compare(p)

        t1 = TreeManager()
        parser, lexer = python.load()
        t1.add_parser(parser, lexer, python.name)
        t1.import_file(p)

        self.text_compare(t1.export_as_text())

        self.tree_compare(self.parser.previous_version.parent, parser.previous_version.parent)

    def test_bug_delete(self):
        import random
        self.reset()

        p = """class X:
    def helloworld():
        for x in y:
            if x:
                return 1
            else:
                return 12
        return 13"""
        self.treemanager.import_file(p)
        assert self.parser.last_status == True

        self.text_compare(p)

        line_count = len(self.treemanager.lines)
        random_lines = range(line_count)
        random.shuffle(random_lines)

        start_version = self.treemanager.version

        self.treemanager.cursor_reset()
        self.move(DOWN, 1)
        self.move(RIGHT, 6)
        self.treemanager.key_delete()
        self.treemanager.key_delete()
        self.treemanager.key_delete()
        self.treemanager.undo_snapshot()

        self.treemanager.cursor_reset()
        self.move(DOWN, 2)
        self.move(RIGHT, 7)
        self.treemanager.key_delete()
        self.treemanager.key_delete()
        self.treemanager.undo_snapshot()

        self.treemanager.cursor_reset()
        self.move(DOWN, 3)
        self.move(RIGHT, 10)
        self.treemanager.key_delete()
        self.treemanager.key_delete()
        self.treemanager.undo_snapshot()

        end_version = self.treemanager.version
        broken = self.treemanager.export_as_text()

        # undo all and compare with original
        while self.treemanager.version > start_version:
            self.treemanager.key_ctrl_z()
        self.text_compare(p)

        # redo all and compare with broken
        while self.treemanager.version < end_version:
            self.treemanager.key_shift_ctrl_z()
        self.text_compare(broken)

        # undo again and compare with original
        while self.treemanager.version > start_version:
            self.treemanager.key_ctrl_z()
        self.text_compare(p)

        t1 = TreeManager()
        parser, lexer = python.load()
        t1.add_parser(parser, lexer, python.name)
        t1.import_file(p)

        self.text_compare(t1.export_as_text())

        self.tree_compare(self.parser.previous_version.parent, parser.previous_version.parent)

    def test_bug_insert_newline(self):
        self.reset()

        p = """class X:
    def helloworld(x, y, z):
        for x in range(0, 10):
            if x == 1:
                return 1
            else:
                return 12
        return 13

    def foo(x):
        x = 1
        y = 2
        foo()
        return 12"""
        self.treemanager.import_file(p)
        assert self.parser.last_status == True

        self.text_compare(p)

        start_version = self.treemanager.version

        self.treemanager.cursor_reset()
        self.move(DOWN, 7)
        self.move(RIGHT, 10)
        self.treemanager.key_normal("\r")
        self.treemanager.undo_snapshot()

        self.treemanager.cursor_reset()
        self.move(DOWN, 6)
        self.move(RIGHT, 0)
        self.treemanager.key_normal("\r") # this has to be \r not \n (Eco works with \r)
        self.treemanager.undo_snapshot()

        end_version = self.treemanager.version
        broken = self.treemanager.export_as_text()

        # undo all and compare with original
        while self.treemanager.version > start_version:
            self.treemanager.key_ctrl_z()
        self.text_compare(p)

        # redo all and compare with broken
        while self.treemanager.version < end_version:
            self.treemanager.key_shift_ctrl_z()
        self.text_compare(broken)

        # undo again and compare with original
        while self.treemanager.version > start_version:
            self.treemanager.key_ctrl_z()
        self.text_compare(p)

        t1 = TreeManager()
        parser, lexer = python.load()
        t1.add_parser(parser, lexer, python.name)
        t1.import_file(p)

        self.tree_compare(self.parser.previous_version.parent, parser.previous_version.parent)

    @slow
    def test_undo_random_insertdelete(self):
        import random
        self.reset()
        #self.save()

        self.treemanager.import_file(programs.connect4)
        assert self.parser.last_status == True
        #self.save()

        self.text_compare(programs.connect4)

        line_count = len(self.treemanager.lines)
        random_lines = range(line_count)
        random.shuffle(random_lines)

        start_version = self.treemanager.version
        for linenr in random_lines:
            cols = range(20)
            random.shuffle(cols)
            for col in cols:
                self.treemanager.cursor_reset()
                self.move(DOWN, linenr)
                self.move(RIGHT, col)
                k = self.get_random_key()
                if k in ["a", "c", "e", "g", "i", "k", "m", "1", "3", "5", "7"]:
                    # for a few characters DELETE instead of INSERT
                    x = self.treemanager.key_delete()
                else:
                    x = self.treemanager.key_normal(self.get_random_key())
                if x == "eos":
                    continue
            self.treemanager.undo_snapshot()

        end_version = self.treemanager.version
        broken = self.treemanager.export_as_text()

        # undo all and compare with original
        while self.treemanager.version > start_version:
            self.treemanager.key_ctrl_z()
        self.text_compare(programs.connect4)

        # redo all and compare with broken
        while self.treemanager.version < end_version:
            self.treemanager.key_shift_ctrl_z()
        self.text_compare(broken)

        # undo again and compare with original
        while self.treemanager.version > start_version:
            self.treemanager.key_ctrl_z()
        self.text_compare(programs.connect4)

        t1 = TreeManager()
        parser, lexer = python.load()
        t1.add_parser(parser, lexer, python.name)
        t1.import_file(programs.connect4)

        self.tree_compare(self.parser.previous_version.parent, parser.previous_version.parent)

    @slow
    def test_undo_random_insertdeleteundo_slow(self):
        self.random_insert_delete_undo(programs.connect4)

    def test_undo_random_insertdeleteundo(self):
        self.random_insert_delete_undo(programs.pythonsmall)

    def test_undo_random_insertdeleteundo_bug1(self):
        self.reset()

        program = """class Connect4():
    UI_DEPTH = 5

    def __init__():
        pass"""

        self.treemanager.import_file(program)
        assert self.parser.last_status == True

        self.text_compare(program)
        start_version = self.treemanager.version

        self.treemanager.cursor_reset()
        self.move(DOWN, 2)
        self.move(RIGHT, 0)
        self.treemanager.key_normal(',')
        self.treemanager.undo_snapshot()
        self.treemanager.cursor_reset()
        self.move(DOWN, 1)
        self.move(RIGHT, 3)
        self.treemanager.key_delete()
        self.treemanager.cursor_reset()
        self.move(DOWN, 1)
        self.move(RIGHT, 4)
        self.treemanager.key_normal(' ')
        self.treemanager.undo_snapshot()


        # undo all and compare with original
        while self.treemanager.version > start_version:
            self.treemanager.key_ctrl_z()
        self.text_compare(program)

    def test_undo_random_insertdeleteundo_bug2(self):
        self.reset()

        prog = """class X:
    def hello():
        pass
        
    def foo():
        do
        something
        here"""
        self.treemanager.import_file(prog)
        assert self.parser.last_status == True

        self.text_compare(prog)
        start_version = self.treemanager.version

        self.treemanager.cursor_reset()
        self.move(DOWN, 1)
        self.move(RIGHT, 0)
        self.treemanager.key_normal(' ')
        self.treemanager.undo_snapshot()
        self.treemanager.cursor_reset()
        self.move(DOWN, 1)
        self.move(RIGHT, 3)
        self.treemanager.key_delete()
        self.treemanager.undo_snapshot()
        self.treemanager.key_ctrl_z()
        self.treemanager.cursor_reset()
        self.move(DOWN, 6)
        self.move(RIGHT, 11)
        self.treemanager.key_normal('x')
        self.treemanager.undo_snapshot()

        self.treemanager.key_ctrl_z()
        self.treemanager.key_ctrl_z()
        self.text_compare(prog)

    def test_undo_random_insertdeleteundo_bug3(self):
        self.reset()

        self.treemanager.import_file("""class C:
    x = 5
""")
        assert self.parser.last_status == True

        self.treemanager.cursor_reset()
        self.move(DOWN, 0)
        self.move(RIGHT, 1)
        self.treemanager.key_normal('\r')
        self.treemanager.cursor_reset()
        self.move(DOWN, 0)
        self.move(RIGHT, 0)
        self.treemanager.key_normal('\r')
        self.treemanager.cursor_reset()
        self.move(DOWN, 0)
        self.move(RIGHT, 2)
        self.treemanager.key_delete()

        assert self.parser.last_status == False

    def test_undo_random_insertdeleteundo_bug4(self):
        self.reset()

        program = """class X:
    def helloworld():
        for x in y:
            if x:
                return 1"""
        self.treemanager.import_file(program)
        assert self.parser.last_status == True

        start_version = self.treemanager.version

        self.treemanager.cursor_reset()
        self.move(DOWN, 4)
        self.move(RIGHT, 1)
        self.treemanager.key_normal('c')
        self.treemanager.undo_snapshot()
        self.treemanager.cursor_reset()
        self.move(DOWN, 4)
        self.move(RIGHT, 0)
        self.treemanager.key_normal('(')
        self.treemanager.undo_snapshot()
        self.treemanager.cursor_reset()
        self.move(DOWN, 4)
        self.move(RIGHT, 2)
        self.treemanager.key_normal('b')
        self.treemanager.undo_snapshot()

        end_version = self.treemanager.version
        broken = self.treemanager.export_as_text()

        # bug causes the 'b' to be ignored by undo
        assert self.treemanager.cursor.node.symbol.name == "bc"
        self.treemanager.key_ctrl_z()
        assert self.treemanager.cursor.node.next_term.next_term.symbol.name == "c"

        # undo all and compare with original
        while self.treemanager.version > start_version:
            self.treemanager.key_ctrl_z()
        self.text_compare(program)

        # redo all and compare with broken
        while self.treemanager.version < end_version:
            self.treemanager.key_shift_ctrl_z()

        self.text_compare(broken)

    def test_undo_random_insertdeleteundo_bug5(self):
        self.reset()
        program = """class X:
    def x():
        pass

    def y():
        pass2"""
        self.treemanager.import_file(program)
        assert self.parser.last_status == True
        start_version = self.treemanager.version

        self.treemanager.cursor_reset()
        self.move(DOWN, 4)
        self.move(RIGHT, 0)
        self.treemanager.key_normal('&')
        self.treemanager.undo_snapshot()
        self.treemanager.cursor_reset()
        self.move(DOWN, 5)
        self.move(RIGHT, 0)
        self.treemanager.key_normal('!')
        self.treemanager.undo_snapshot()
        self.treemanager.cursor_reset()
        self.move(DOWN, 4)
        self.move(RIGHT, 0)
        self.treemanager.key_delete()
        self.treemanager.undo_snapshot()
        self.treemanager.cursor_reset()
        self.move(DOWN, 3)
        self.move(RIGHT, 0)
        self.treemanager.key_normal('^')
        self.treemanager.undo_snapshot()

        end_version = self.treemanager.version
        broken = self.treemanager.export_as_text()

        # undo all and compare with original
        while self.treemanager.version > start_version:
            self.treemanager.key_ctrl_z()
        self.text_compare(program)

        # redo all and compare with broken
        while self.treemanager.version < end_version:
            self.treemanager.key_shift_ctrl_z()

        self.text_compare(broken)

    def random_insert_delete_undo(self, program):
        import random
        self.reset()
        #self.save()

        self.treemanager.import_file(program)
        assert self.parser.last_status == True
        #self.save()

        self.text_compare(program)

        line_count = len(self.treemanager.lines)
        random_lines = range(line_count)
        random.shuffle(random_lines)

        start_version = self.treemanager.version
        for linenr in random_lines:
            cols = range(5)
            random.shuffle(cols)
            for col in cols:
                last_was_undo = False
                print("self.treemanager.cursor_reset()")
                self.treemanager.cursor_reset()
                print("self.move(DOWN, %s)" % (linenr))
                print("self.move(RIGHT, %s)" % (col))
                self.move(DOWN, linenr)
                self.move(RIGHT, col)
                k = self.get_random_key()
                if k in ["a", "c", "e", "g", "i", "k", "m", "1", "3", "5", "7"]:
                    # for a few characters DELETE instead of INSERT
                    print("self.treemanager.key_delete()")
                    x = self.treemanager.key_delete()
                elif k in ["o", "q", "s", "u"]:
                    print("self.treemanager.key_ctrl_z()")
                    x = self.treemanager.key_ctrl_z()
                    last_was_undo = True
                else:
                    key = self.get_random_key()
                    print("self.treemanager.key_normal(%s)" % (repr(key)))
                    x = self.treemanager.key_normal(key)
                if x == "eos":
                    continue
            if not last_was_undo:
                print("self.treemanager.undo_snapshot()")
                self.treemanager.undo_snapshot()

        end_version = self.treemanager.version
        broken = self.treemanager.export_as_text()

        # undo all and compare with original
        while self.treemanager.version > start_version:
            self.treemanager.key_ctrl_z()
        self.text_compare(program)

        # redo all and compare with broken
        while self.treemanager.version < end_version:
            self.treemanager.key_shift_ctrl_z()

        self.text_compare(broken)

        # undo again and compare with original
        while self.treemanager.version > start_version:
            self.treemanager.key_ctrl_z()
        self.text_compare(program)

        t1 = TreeManager()
        parser, lexer = python.load()
        t1.add_parser(parser, lexer, python.name)
        t1.import_file(program)

        self.tree_compare(self.parser.previous_version.parent, parser.previous_version.parent)



    def test_bug_infinite_loop(self):
        self.reset()

        self.treemanager.import_file(programs.pythonsmall)
        assert self.parser.last_status == True

        self.treemanager.cursor_reset()
        self.move(DOWN, 8)
        self.move(RIGHT, 0)
        self.treemanager.key_delete()
        self.treemanager.undo_snapshot()
        self.treemanager.cursor_reset()
        self.treemanager.key_ctrl_z()
        self.treemanager.cursor_reset()
        self.move(DOWN, 9)
        self.move(RIGHT, 0)
        self.treemanager.key_delete()

    def test_bug_undo_loop_2(self):

        self.reset()

        self.treemanager.import_file(programs.pythonsmall)
        assert self.parser.last_status == True

        start_version = self.treemanager.version

        self.treemanager.cursor_reset()
        self.move(DOWN, 5)
        self.move(RIGHT, 3)
        self.treemanager.key_normal('#')
        self.treemanager.cursor_reset()
        self.move(DOWN, 5)
        self.move(RIGHT, 3)
        self.treemanager.key_normal(')')
        self.treemanager.undo_snapshot()

        end_version = self.treemanager.version
        broken = self.treemanager.export_as_text()

        # undo all and compare with original
        while self.treemanager.version > start_version:
            self.treemanager.key_ctrl_z()
        self.text_compare(programs.pythonsmall)

        t1 = TreeManager()
        parser, lexer = python.load()
        t1.add_parser(parser, lexer, python.name)
        t1.import_file(programs.pythonsmall)

        self.tree_compare(self.parser.previous_version.parent, parser.previous_version.parent)

    def test_bug_undo_typing(self):
        self.reset()

        self.treemanager.import_file(programs.pythonsmall)
        assert self.parser.last_status == True

        self.treemanager.cursor_reset()
        self.move(DOWN, 12)
        self.move(RIGHT, 0)
        self.treemanager.key_normal("g")
        self.treemanager.key_ctrl_z()

        self.treemanager.cursor_reset()
        self.move(DOWN, 12)
        self.move(RIGHT, 2)
        self.treemanager.key_normal("%")
        self.treemanager.key_ctrl_z()

        self.treemanager.cursor_reset()
        self.move(DOWN, 13)
        self.move(RIGHT, 0)
        self.treemanager.key_normal("y")


class Test_Undo_LBoxes(Test_Helper):

    def setup_class(cls):
        parser, lexer = phppython.load()
        cls.lexer = lexer
        cls.parser = parser
        cls.parser.init_ast()
        cls.ast = cls.parser.previous_version
        cls.treemanager = TreeManager()
        cls.treemanager.add_parser(cls.parser, cls.lexer, phppython.name)

        cls.treemanager.set_font_test(7, 17) # hard coded. PyQt segfaults in test suite

    def test_simple(self):
        self.reset()
        self.treemanager.import_file(programs.phpclass)
        self.move(UP, 1)

        self.treemanager.add_languagebox(lang_dict["Python + PHP"])

        self.treemanager.key_normal("p")
        self.treemanager.key_normal("a")
        self.treemanager.key_normal("s")
        self.treemanager.key_normal("s")
        self.treemanager.undo_snapshot()

        self.move(DOWN, 1)
        self.treemanager.key_end()
        self.treemanager.key_normal("a")
        self.treemanager.undo_snapshot()

        self.treemanager.key_ctrl_z()
        self.treemanager.key_ctrl_z()

    def test_simple2(self):
        pytest.skip("For some reason copy.deepcopy errors on this test with the new history service.")
        self.versions = []
        self.reset()
        self.versions.append(self.treemanager.export_as_text())
        self.treemanager.import_file(programs.phpclass)
        self.versions.append(self.treemanager.export_as_text())
        self.move(DOWN, 1)

        self.treemanager.add_languagebox(lang_dict["Python + PHP"])

        text = "def x():\r    pass"
        for c in text:
            self.treemanager.key_normal(c)

        self.treemanager.undo_snapshot()

        import copy
        dp = copy.deepcopy(self.parser.previous_version.parent)
        self.versions.append(self.treemanager.export_as_text())
        self.treemanager.key_normal("a")
        self.treemanager.undo_snapshot()
        self.versions.append(self.treemanager.export_as_text())

        self.move(UP, 2)
        self.treemanager.key_end()
        self.treemanager.key_normal("\r")
        self.treemanager.undo_snapshot()
        self.versions.append(self.treemanager.export_as_text())
        self.treemanager.key_normal("a")
        self.treemanager.undo_snapshot()
        self.versions.append(self.treemanager.export_as_text())

        assert self.versions.pop() == self.treemanager.export_as_text()
        self.treemanager.key_ctrl_z()
        assert self.versions.pop() == self.treemanager.export_as_text()
        self.treemanager.key_ctrl_z()
        assert self.versions.pop() == self.treemanager.export_as_text()
        self.treemanager.key_ctrl_z()
        assert self.versions.pop() == self.treemanager.export_as_text()

        self.tree_compare(self.parser.previous_version.parent, dp)

    def test_clean_version_bug(self):
        self.reset()
        self.treemanager.import_file(programs.phpclass)
        self.move(DOWN, 1)

        self.treemanager.add_languagebox(lang_dict["Python + PHP"])
        self.treemanager.key_normal("p")
        self.treemanager.key_normal("a")
        self.treemanager.key_normal("s")
        self.treemanager.key_normal("s")
        self.treemanager.undo_snapshot()

        import copy
        dp = copy.deepcopy(self.parser.previous_version.parent)

        self.treemanager.key_normal("a")
        self.treemanager.undo_snapshot()
        self.treemanager.key_ctrl_z()
        self.treemanager.undo_snapshot()

        self.tree_compare(self.parser.previous_version.parent, dp)

        self.move(UP, 1)
        self.treemanager.key_end()
        self.move(LEFT, 2)
        self.treemanager.key_normal("x")
        self.treemanager.undo_snapshot()

        dp2 = copy.deepcopy(self.parser.previous_version.parent)
        self.treemanager.key_ctrl_z()
        self.treemanager.key_shift_ctrl_z()

        self.tree_compare(self.parser.previous_version.parent, dp2)

class Test_InputLogger(Test_Python):
    def test_simple(self):
        log = """self.key_normal('c')
self.key_normal('l')
self.key_normal('a')
self.key_normal('s')
self.key_normal('s')
self.key_normal(' ')
self.key_shift()
self.key_normal('X')
self.key_shift()
self.key_normal(':')
self.key_normal('\r')
self.key_normal('    ')
self.key_normal('d')
self.key_normal('e')
self.key_normal('f')
self.key_normal(' ')
self.key_normal('x')
self.key_backspace()
self.key_normal('y')
self.key_shift()
self.key_normal('o')
self.key_normal('o')
self.key_shift()
self.key_normal('(')
self.key_shift()
self.key_normal(')')
self.key_normal(':')
self.key_normal('\r')
self.key_normal('    ')
self.key_normal('x')
self.key_normal(' ')
self.key_normal('=')
self.key_normal(' ')
self.key_normal('1')
self.key_cursors(KEY_UP, False)
self.key_cursors(KEY_LEFT, False)
self.key_cursors(KEY_LEFT, False)
# mousePressEvent
self.cursor.line = 1
self.cursor.move_to_x(11)
self.selection_start = self.cursor.copy()
self.selection_end = self.cursor.copy()
self.cursor.line = 1
self.cursor.move_to_x(8)
self.selection_end = self.cursor.copy()
self.cursor.line = 2
self.key_normal('f')
self.key_normal('o')
self.key_normal('o')
# mousePressEvent
self.cursor.line = 2
self.cursor.move_to_x(16)
self.selection_start = self.cursor.copy()
self.selection_end = self.cursor.copy()
self.key_backspace()
self.add_languagebox('SQL')
self.key_shift()
self.key_normal('S')
self.key_normal('E')
self.key_normal('L')
self.key_normal('E')
self.key_normal('C')
self.key_normal('T')
self.key_normal(' ')
self.key_shift()
self.key_normal('*')
self.key_shift()
self.key_normal(' ')
self.key_normal('F')
self.key_normal('R')
self.key_normal('O')
self.key_normal('M')
self.key_normal(' ')
self.key_normal('t')
self.key_normal('a')
self.key_normal('b')
self.key_normal('l')
self.key_normal('e')"""

        self.treemanager.apply_inputlog(log)
        assert self.treemanager.export_as_text() == """class X:
    def foo():
        x = SELECT * FROM table"""

class Test_Comments_Indents(Test_Python):
    def test_newline(self):
        self.reset()
        for c in "y = 12 # blaz = 13":
            self.treemanager.key_normal(c)
        assert self.parser.last_status == True

        self.move(LEFT, 6)
        self.treemanager.key_normal("\r")
        assert self.parser.last_status == True

    def test_single_line_comment(self):
        self.reset()
        for c in """x = 12
y = 13""":
            self.treemanager.key_normal(c)
        assert self.parser.last_status == True

        self.move(LEFT, 6)
        self.move(UP, 1)
        self.treemanager.key_normal("#")
        assert self.parser.last_status == True
        
