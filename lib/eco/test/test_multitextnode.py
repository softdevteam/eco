from grammars.grammars import calc, python
from treemanager import TreeManager
from utils import KEY_UP as UP, KEY_DOWN as DOWN, KEY_LEFT as LEFT, KEY_RIGHT as RIGHT
from grammars.grammars import EcoFile

class Test_MultiTextNode:

    def setup_class(cls):
        grm = EcoFile("MultiTest", "test/calcmultistring.eco", "Multi")
        parser, lexer = grm.load()
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
        self.reset()
        self.treemanager.key_normal("1")
        self.treemanager.key_normal("+")
        self.treemanager.key_normal("\"")
        self.treemanager.key_normal("abc")
        assert self.parser.last_status == False

        self.treemanager.key_normal("\"")
        assert self.parser.last_status == True

    def test_newline(self):
        self.reset()
        self.treemanager.key_normal("1")
        self.treemanager.key_normal("+")
        self.treemanager.key_normal("\"")
        self.treemanager.key_normal("abc")
        self.treemanager.key_normal("\"")

        assert self.parser.last_status == True

        self.treemanager.cursor_movement(LEFT)
        self.treemanager.cursor_movement(LEFT)

        self.treemanager.key_normal("\r")

        assert self.parser.last_status == True

    def test_doublenewline(self):
        self.reset()
        self.treemanager.key_normal("1")
        self.treemanager.key_normal("+")
        self.treemanager.key_normal("\"")
        self.treemanager.key_normal("abcd")
        self.treemanager.key_normal("\"")

        assert self.parser.last_status == True

        self.treemanager.cursor_movement(LEFT)
        self.treemanager.cursor_movement(LEFT)

        self.treemanager.key_normal("\r")

        assert self.parser.last_status == True

        self.treemanager.cursor_movement(LEFT)
        self.treemanager.cursor_movement(LEFT)

        self.treemanager.key_normal("\r")

        assert self.parser.last_status == True

    def test_doublenewline_delete(self):
        self.reset()
        self.treemanager.key_normal("1")
        self.treemanager.key_normal("+")
        self.treemanager.key_normal("\"")
        self.treemanager.key_normal("abcd")
        self.treemanager.key_normal("\"")

        assert self.parser.last_status == True

        self.treemanager.cursor_movement(LEFT)
        self.treemanager.cursor_movement(LEFT)

        self.treemanager.key_normal("\r")

        assert self.parser.last_status == True

        self.treemanager.cursor_movement(LEFT)
        self.treemanager.cursor_movement(LEFT)

        self.treemanager.key_normal("\r")

        bos = self.parser.previous_version.parent.children[0]
        assert bos.next_term.next_term.next_term.children[0].symbol.name == "\"ab"
        assert bos.next_term.next_term.next_term.children[1].symbol.name == "\r"
        assert bos.next_term.next_term.next_term.children[2].symbol.name == "c"
        assert bos.next_term.next_term.next_term.children[3].symbol.name == "\r"
        assert bos.next_term.next_term.next_term.children[4].symbol.name == "d\""

        self.treemanager.cursor_movement(DOWN)
        self.treemanager.key_backspace()

        assert bos.next_term.symbol.name == "1"
        assert bos.next_term.next_term.symbol.name == "+"
        assert bos.next_term.next_term.next_term.children[0].symbol.name == "\"ab"
        assert bos.next_term.next_term.next_term.children[1].symbol.name == "\r"
        assert bos.next_term.next_term.next_term.children[2].symbol.name == "cd\""
        assert len(bos.next_term.next_term.next_term.children) == 3
        assert bos.next_term.next_term.next_term.children[2].next_term is None

        assert self.parser.last_status == True

class Test_MultiTextNodePython:

    def setup_class(cls):
        parser, lexer = python.load()
        cls.lexer = lexer
        cls.parser = parser
        cls.parser.init_ast()
        cls.ast = cls.parser.previous_version
        cls.treemanager = TreeManager()
        cls.treemanager.add_parser(cls.parser, cls.lexer, python.name)

        cls.treemanager.set_font_test(7, 17) # hard coded. PyQt segfaults in test suite

    def reset(self):
        self.parser.reset()
        self.treemanager = TreeManager()
        self.treemanager.add_parser(self.parser, self.lexer, calc.name)
        self.treemanager.set_font_test(7, 17)

    def test_simple(self):
        self.reset()
        inputstring = "x = \"\"\"abcdef\"\"\""
        for c in inputstring:
            self.treemanager.key_normal(c)

        self.treemanager.cursor_movement(LEFT)
        self.treemanager.cursor_movement(LEFT)
        self.treemanager.cursor_movement(LEFT)
        self.treemanager.cursor_movement(LEFT)
        self.treemanager.cursor_movement(LEFT)
        self.treemanager.cursor_movement(LEFT)

        print "DO THE PRESS NOW!!!"
        self.treemanager.key_normal("\r")
