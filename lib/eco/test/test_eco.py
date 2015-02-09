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

from PyQt4 import QtCore

import programs

import pytest
slow = pytest.mark.slow

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
        self.treemanager.cursor_movement("right")
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
        self.treemanager.cursor_movement("up")
        assert self.treemanager.cursor.node.symbol.name == "2"
        self.treemanager.cursor_movement("left")
        assert self.treemanager.cursor.node.symbol.name == "+"
        self.treemanager.cursor_movement("down")
        assert self.treemanager.cursor.node.symbol.name == "+"

    def test_deletion(self):
        import pytest
        self.treemanager.key_end()
        assert self.treemanager.cursor.node.symbol.name == "5"
        self.treemanager.key_backspace()
        assert self.treemanager.cursor.node.symbol.name == "+"
        self.treemanager.key_delete()
        assert self.treemanager.cursor.node.symbol.name == "+"
        self.treemanager.cursor_movement("left")
        self.treemanager.key_delete()
        assert self.treemanager.cursor.node.symbol.name == "3"

    def test_cursor_reset(self):
        self.treemanager.cursor_reset()
        assert isinstance(self.treemanager.cursor.node, BOS)

    def test_delete_selection(self):
        self.reset()
        self.treemanager.key_normal("a")
        self.treemanager.key_shift()
        self.treemanager.key_cursors("left", mod_shift=True)
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
        self.move('down', 9)
        self.move('right', 16)

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
        self.move('down', 4)
        self.move('right', 8)

        # indent 'for' and 'x = x + 1'
        assert self.treemanager.cursor.node.next_term.symbol.name == "for"
        for i in range(4): self.treemanager.key_normal(" ")
        assert self.parser.last_status == False
        self.move('down', 1)
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
        self.move('down', 4)
        self.move('right', 4)

        # indent 'def y', 'y = 2' and 'return y'
        assert self.treemanager.cursor.node.next_term.symbol.name == "def"
        for i in range(4): self.treemanager.key_normal(" ")
        assert self.parser.last_status == False
        self.move('down', 1)
        assert self.treemanager.cursor.node.next_term.symbol.name == "y"
        for i in range(4): self.treemanager.key_normal(" ")
        assert self.parser.last_status == True
        self.move('down', 1)
        self.move('left', 4)
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
                    self.move('down', linenr)
                    self.move('right', del_ws)
                    assert self.treemanager.cursor.node.symbol.name == " " * whitespace
                    for i in range(del_ws):
                        self.treemanager.key_backspace()
                    deleted[linenr] = del_ws
        assert self.parser.last_status == False

        # undo
        for linenr in deleted:
            del_ws = deleted[linenr]
            self.treemanager.cursor_reset()
            self.move('down', linenr)
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
        self.treemanager.cursor_movement("down")
        self.treemanager.key_home()
        self.treemanager.key_normal(" ")
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
        self.treemanager.key_cursors("left")
        # select "bc de"
        self.treemanager.key_shift()
        self.treemanager.key_cursors("left", mod_shift=True)
        self.treemanager.key_cursors("left", mod_shift=True)
        self.treemanager.key_cursors("left", mod_shift=True)
        self.treemanager.key_cursors("left", mod_shift=True)
        self.treemanager.key_cursors("left", mod_shift=True)
        self.treemanager.deleteSelection()
        assert lbox.symbol.name == "<Prolog>"

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
        self.treemanager.savestate() # tells treemanager to save after the next operation and increase the version
        self.treemanager.key_normal(text)

    def save(self):
        self.treemanager.version += 1
        self.treemanager.save()

    def test_simple_undo_redo(self):
        self.treemanager.savestate()
        self.treemanager.key_normal("1")
        self.treemanager.savestate()
        self.treemanager.key_normal("+")
        self.treemanager.savestate()
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
        self.compare("class X:\r\n    pass")

        self.treemanager.key_ctrl_z()
        self.compare("class X:\r\n    ")

        self.treemanager.key_ctrl_z()
        self.compare("class X:")
        assert self.treemanager.cursor.node.next_term.symbol.name == "NEWLINE"
        assert isinstance(self.treemanager.cursor.node.next_term.next_term, EOS)

        self.treemanager.key_ctrl_z()
        self.compare("class")

        self.treemanager.key_shift_ctrl_z()
        self.treemanager.key_shift_ctrl_z()
        self.treemanager.key_shift_ctrl_z()
        self.compare("class X:\r\n    pass")
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
        self.move("up", 1)
        self.compare("1\r\n2")
        self.type_save("\r")
        self.type_save("3")
        self.compare("1\r\n3\r\n2")

        self.treemanager.key_ctrl_z()
        self.treemanager.key_ctrl_z()
        self.treemanager.key_ctrl_z()
        self.treemanager.key_ctrl_z()
        self.compare("1")

        self.treemanager.key_shift_ctrl_z()
        self.treemanager.key_shift_ctrl_z()
        self.treemanager.key_shift_ctrl_z()
        self.treemanager.key_shift_ctrl_z()
        self.compare("1\r\n3\r\n2")

        self.move("down", 1)
        self.treemanager.key_backspace()
        self.compare("1\r\n3\r\n")
        self.treemanager.key_backspace()
        self.compare("1\r\n3")
        self.treemanager.key_backspace()
        self.compare("1\r\n")
        self.treemanager.key_backspace()
        self.compare("1")

    def test_redo_bug2(self):
        self.reset()
        self.type_save("1")
        self.type_save("+")
        self.type_save("2")
        self.move("left", 2)
        self.compare("1+2")
        self.treemanager.savestate()
        self.treemanager.key_delete()
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
        self.move("left", 1)
        self.treemanager.savestate()
        self.treemanager.key_normal("s")
        dp = self.copy()

        self.move("down", 2)
        self.treemanager.key_end()
        self.move("left", 1)
        self.treemanager.savestate()
        self.treemanager.key_normal("+")

        self.treemanager.key_ctrl_z()

        self.text_compare("""class Xs:
    def foo():
        return 23""")
        self.tree_compare(self.parser.previous_version.parent, dp)


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
        self.move("down", 2)
        self.treemanager.key_end()
        self.treemanager.key_normal("1")
        self.compare("class X:\r\n    def x():\r\n         pass1")
        self.treemanager.key_ctrl_z()
        self.compare("class X:\r\n    def x():\r\n         pass")
        self.treemanager.key_ctrl_z()
        self.compare("")

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
                self.move('down', linenr)
                self.move('right', col)
                x = self.treemanager.key_delete()
                if x == "eos":
                    continue
            self.treemanager.savestate()

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
                self.move('down', linenr)
                self.move('right', col)
                x = self.treemanager.key_normal(self.get_random_key())
                if x == "eos":
                    continue
            self.treemanager.savestate()

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
        for linenr in random_lines[:5]:
            cols = range(20)
            random.shuffle(cols)
            for col in cols[:1]: # add one newline per line
                print("added newline at line %s:%s" % (linenr,col))
                self.treemanager.cursor_reset()
                self.move('down', linenr)
                self.move('right', col)
                x = self.treemanager.key_normal("\r")
                if x == "eos":
                    continue
            self.treemanager.savestate()

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
        self.move("down", 7)
        self.move("right", 10)
        self.treemanager.key_normal("\r")
        self.treemanager.savestate()

        self.treemanager.cursor_reset()
        self.move("down", 6)
        self.move("right", 0)
        self.treemanager.key_normal("\r") # this has to be \r not \n (Eco works with \r)
        self.treemanager.savestate()

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
                self.move('down', linenr)
                self.move('right', col)
                k = self.get_random_key()
                if k in ["a", "c", "e", "g", "i", "k", "m", "1", "3", "5", "7"]:
                    # for a few characters DELETE instead of INSERT
                    x = self.treemanager.key_delete()
                else:
                    x = self.treemanager.key_normal(self.get_random_key())
                if x == "eos":
                    continue
            self.treemanager.savestate()

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
        self.move("up", 1)

        self.treemanager.add_languagebox(lang_dict["Python + PHP"])

        self.treemanager.key_normal("p")
        self.treemanager.key_normal("a")
        self.treemanager.key_normal("s")
        self.treemanager.savestate()
        self.treemanager.key_normal("s")

        self.move("down", 1)
        self.treemanager.key_end()
        self.treemanager.savestate()
        self.treemanager.key_normal("a")

        self.treemanager.key_ctrl_z()
        self.treemanager.key_ctrl_z()

    def test_simple2(self):
        self.versions = []
        self.reset()
        self.versions.append(self.treemanager.export_as_text())
        self.treemanager.import_file(programs.phpclass)
        self.versions.append(self.treemanager.export_as_text())
        self.move("down", 1)

        self.treemanager.add_languagebox(lang_dict["Python + PHP"])

        text = "def x():\r    pass"
        for c in text:
            self.treemanager.key_normal(c)

        import copy
        dp = copy.deepcopy(self.parser.previous_version.parent)
        self.versions.append(self.treemanager.export_as_text())
        self.treemanager.savestate()
        self.treemanager.key_normal("a")
        self.versions.append(self.treemanager.export_as_text())

        self.move("up", 2)
        self.treemanager.key_end()
        self.treemanager.savestate()
        self.treemanager.key_normal("\r")
        self.versions.append(self.treemanager.export_as_text())
        self.treemanager.savestate()
        self.treemanager.key_normal("a")
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
        self.move("down", 1)

        self.treemanager.add_languagebox(lang_dict["Python + PHP"])
        self.treemanager.key_normal("p")
        self.treemanager.key_normal("a")
        self.treemanager.key_normal("s")
        self.treemanager.savestate()
        self.treemanager.key_normal("s")

        import copy
        dp = copy.deepcopy(self.parser.previous_version.parent)

        self.treemanager.savestate()
        self.treemanager.key_normal("a")
        self.treemanager.savestate()
        self.treemanager.key_ctrl_z()

        self.tree_compare(self.parser.previous_version.parent, dp)

        self.move("up", 1)
        self.treemanager.key_end()
        self.move("left", 2)
        self.treemanager.savestate()
        self.treemanager.key_normal("x")

        dp2 = copy.deepcopy(self.parser.previous_version.parent)
        self.treemanager.key_ctrl_z()
        self.treemanager.key_shift_ctrl_z()

        self.tree_compare(self.parser.previous_version.parent, dp2)
