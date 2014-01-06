from grammars.grammars import calc1, java15, python275
from treemanager import TreeManager
from incparser.incparser import IncParser
from inclexer.inclexer import IncrementalLexer
from incparser.astree import BOS, EOS

from PyQt4 import QtCore

class Test_Typing:

    def setup_class(cls):
        cls.lexer = IncrementalLexer(calc1.priorities)
        cls.parser = IncParser(calc1.grammar, 1, True)
        cls.parser.init_ast()
        cls.ast = cls.parser.previous_version
        cls.treemanager = TreeManager()
        cls.treemanager.add_parser(cls.parser, cls.lexer, calc1.name)

        cls.treemanager.set_font_test(7, 17) # hard coded. PyQt segfaults in test suite

    def test_normaltyping(self):
        assert self.parser.last_status == False
        self.treemanager.key_normal("1")
        assert self.parser.last_status == True
        self.treemanager.key_normal("+")
        assert self.parser.last_status == False
        self.treemanager.key_normal("2")
        assert self.parser.last_status == True

    def test_cursormovement(self):
        self.treemanager.key_home()
        assert isinstance(self.treemanager.cursor.node, BOS)
        self.treemanager.cursor_movement(QtCore.Qt.Key_Right)
        assert self.treemanager.cursor.node.symbol.name == "1"
        self.treemanager.key_end()
        assert self.treemanager.cursor.node.symbol.name == "2"

    def test_normaltyping2(self):
        self.treemanager.key_normal("\r")
        self.treemanager.key_normal("3")
        self.treemanager.key_normal("+")
        self.treemanager.key_normal("5")

    def test_cursormovement(self):
        assert self.treemanager.cursor.node.symbol.name == "5"
        self.treemanager.key_end()
        assert self.treemanager.cursor.node.symbol.name == "5"
        self.treemanager.cursor_movement(QtCore.Qt.Key_Up)
        assert self.treemanager.cursor.node.symbol.name == "2"
        self.treemanager.cursor_movement(QtCore.Qt.Key_Left)
        assert self.treemanager.cursor.node.symbol.name == "+"
        self.treemanager.cursor_movement(QtCore.Qt.Key_Down)
        assert self.treemanager.cursor.node.symbol.name == "+"

    def test_deletion(self):
        import pytest
        self.treemanager.key_end()
        assert self.treemanager.cursor.node.symbol.name == "5"
        self.treemanager.key_backspace()
        assert self.treemanager.cursor.node.symbol.name == "+"
        self.treemanager.key_delete()
        assert self.treemanager.cursor.node.symbol.name == "+"
        self.treemanager.cursor_movement(QtCore.Qt.Key_Left)
        self.treemanager.key_delete()
        assert self.treemanager.cursor.node.symbol.name == "3"

class Test_Indentation:

    def setup_class(cls):
        cls.lexer = IncrementalLexer(python275.priorities)
        cls.parser = IncParser(python275.grammar, 1, True)
        cls.parser.init_ast()
        cls.ast = cls.parser.previous_version
        cls.treemanager = TreeManager()
        cls.treemanager.add_parser(cls.parser, cls.lexer, python275.name)

        cls.treemanager.set_font_test(7, 17) # hard coded. PyQt segfaults in test suite

    def test_indentation(self):
        assert self.parser.last_status == True
        inputstring = "class Test:\r    def x():\r    return x"
        for c in inputstring:
            self.treemanager.key_normal(c)
        assert self.parser.last_status == True
        assert self.treemanager.lines[0].indent == 0
        assert self.treemanager.lines[1].indent == 1
        assert self.treemanager.lines[2].indent == 2

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
        assert self.treemanager.lines[3].indent == 1
        assert self.treemanager.lines[4].indent == 2

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

