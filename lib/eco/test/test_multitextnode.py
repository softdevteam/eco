from grammars.grammars import lang_dict
from treemanager import TreeManager
from grammar_parser.gparser import MagicTerminal
from utils import KEY_UP as UP, KEY_DOWN as DOWN, KEY_LEFT as LEFT, KEY_RIGHT as RIGHT
from grammars.grammars import EcoFile

import pytest

calc = lang_dict["Basic Calculator"]
python = lang_dict["Python 2.7.5"]
php = lang_dict["PHP"]

if pytest.config.option.log:
    import logging
    logging.getLogger().setLevel(logging.DEBUG)

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

        self.treemanager.key_normal("\r")

    def test_relex_over_indentation(self):
        self.reset()
        inputstring = """class X:
    x = 1
    def x():
        pass
    y = 2"""

        self.treemanager.import_file(inputstring)

        assert self.parser.last_status == True

        self.treemanager.cursor_movement(DOWN)
        self.treemanager.cursor_movement(DOWN)
        self.treemanager.cursor_movement(DOWN)
        self.treemanager.key_end()

        assert self.treemanager.cursor.node.symbol.name == "pass"

        self.treemanager.key_normal("\"")
        self.treemanager.key_normal("\"")
        self.treemanager.key_normal("\"")

        self.treemanager.cursor_movement(UP)
        self.treemanager.cursor_movement(UP)
        self.treemanager.key_end()

        assert self.treemanager.cursor.node.symbol.name == "1"
        self.treemanager.cursor_movement(LEFT)

        self.treemanager.key_normal("\"")
        self.treemanager.key_normal("\"")
        self.treemanager.key_normal("\"")

        assert self.parser.last_status == True

    def test_indentation_to_string_and_back(self):
        self.reset()
        inputstring = """class X:
    a
    b"""

        self.treemanager.import_file(inputstring)

        assert self.parser.last_status == True

        self.treemanager.cursor_movement(DOWN)
        self.treemanager.cursor_movement(DOWN)
        self.treemanager.key_end()

        self.treemanager.key_normal("\"")
        self.treemanager.key_normal("\"")
        self.treemanager.key_normal("\"")

        self.treemanager.cursor_movement(UP)
        self.treemanager.cursor_movement(UP)
        self.treemanager.key_home()

        self.treemanager.key_normal("\"")
        self.treemanager.key_normal("\"")
        self.treemanager.key_normal("\"")

        assert self.parser.last_status == True

        self.treemanager.cursor_movement(DOWN)
        self.treemanager.cursor_movement(DOWN)
        self.treemanager.key_end()
        self.treemanager.key_backspace()

        assert self.parser.last_status == False

    def test_remember_open_lexing_states(self):

        self.reset()
        inputstring = """x = 1
y = 2"""

        self.treemanager.import_file(inputstring)

        assert self.parser.last_status == True

        self.treemanager.key_end()
        self.treemanager.cursor_movement(LEFT)
        self.treemanager.key_normal("\"")
        #assert self.parser.last_status == False # unfinished lexing jobs

        self.treemanager.key_end()
        self.treemanager.key_normal("\"")
        assert self.parser.last_status == True

    def test_triplequote_string(self):

        self.reset()
        inputstring = 'x="""abc"""'

        for i in inputstring:
            self.treemanager.key_normal(i)

        bos = self.parser.previous_version.parent.children[0]
        assert bos.next_term.symbol.name == "x"
        assert bos.next_term.next_term.symbol.name == "="
        assert bos.next_term.next_term.next_term.symbol.name == '"""abc"""'

        self.treemanager.cursor_movement(LEFT)
        self.treemanager.cursor_movement(LEFT)
        self.treemanager.cursor_movement(LEFT)
        self.treemanager.cursor_movement(LEFT)
        self.treemanager.key_normal("\"")

        assert bos.next_term.symbol.name == "x"
        assert bos.next_term.next_term.symbol.name == "="
        assert bos.next_term.next_term.next_term.symbol.name == '""'
        assert bos.next_term.next_term.next_term.next_term.symbol.name == '"ab"'
        assert bos.next_term.next_term.next_term.next_term.lookback == 1
        assert bos.next_term.next_term.next_term.next_term.next_term.symbol.name == 'c'
        assert bos.next_term.next_term.next_term.next_term.next_term.lookback == 2
        assert bos.next_term.next_term.next_term.next_term.next_term.next_term.symbol.name == '""'
        assert bos.next_term.next_term.next_term.next_term.next_term.next_term.next_term.symbol.name == '"'

        self.treemanager.key_normal("\"")

        assert bos.next_term.symbol.name == "x"
        assert bos.next_term.next_term.symbol.name == "="
        assert bos.next_term.next_term.next_term.symbol.name == '""'
        assert bos.next_term.next_term.next_term.next_term.symbol.name == '"ab"'
        assert bos.next_term.next_term.next_term.next_term.lookback == 1
        assert bos.next_term.next_term.next_term.next_term.next_term.symbol.name == '"c"'
        assert bos.next_term.next_term.next_term.next_term.next_term.lookback == 2
        assert bos.next_term.next_term.next_term.next_term.next_term.next_term.symbol.name == '""'


        self.treemanager.key_normal("\"")
        #assert self.parser.last_status == False


        assert bos.next_term.symbol.name == "x"
        assert bos.next_term.next_term.symbol.name == "="
        assert bos.next_term.next_term.next_term.symbol.name == '"""ab"""'
        assert bos.next_term.next_term.next_term.next_term.symbol.name == 'c'
        assert bos.next_term.next_term.next_term.next_term.next_term.symbol.name == '""'
        assert bos.next_term.next_term.next_term.next_term.next_term.next_term.symbol.name == '"'

        self.treemanager.key_end()
        self.treemanager.key_backspace()

        assert bos.next_term.symbol.name == "x"
        assert bos.next_term.next_term.symbol.name == "="
        assert bos.next_term.next_term.next_term.symbol.name == '"""ab"""'
        assert bos.next_term.next_term.next_term.next_term.symbol.name == 'c'
        assert bos.next_term.next_term.next_term.next_term.next_term.symbol.name == '""'

    def test_ignore_nonlbox_x80(self):

        self.reset()
        inputstring = 'x="""ab\x80c"""'

        for i in inputstring:
            self.treemanager.key_normal(i)

        bos = self.parser.previous_version.parent.children[0]
        assert bos.next_term.symbol.name == "x"
        assert bos.next_term.next_term.symbol.name == "="
        assert bos.next_term.next_term.next_term.symbol.name == '"""ab\x80c"""'

    def test_multinode_from_the_start(self):

        self.reset()
        inputstring = '''x="""a\rbc"""'''

        for i in inputstring:
            self.treemanager.key_normal(i)

        bos = self.parser.previous_version.parent.children[0]
        assert bos.next_term.symbol.name == "x"
        assert bos.next_term.next_term.symbol.name == "="
        assert bos.next_term.next_term.next_term.symbol.name == '<Multinode>'

    def test_multinode_and_nonlbox_x80(self):

        self.reset()
        inputstring = '''x="""a\x80bc"""'''

        for i in inputstring:
            self.treemanager.key_normal(i)

        bos = self.parser.previous_version.parent.children[0]
        assert bos.next_term.symbol.name == "x"
        assert bos.next_term.next_term.symbol.name == "="
        assert bos.next_term.next_term.next_term.symbol.name == '"""a\x80bc"""'

        self.treemanager.cursor_movement(LEFT)
        self.treemanager.cursor_movement(LEFT)
        self.treemanager.cursor_movement(LEFT)
        self.treemanager.cursor_movement(LEFT)

        self.treemanager.key_normal("\r")
        bos = self.parser.previous_version.parent.children[0]
        assert bos.next_term.symbol.name == "x"
        assert bos.next_term.next_term.symbol.name == "="
        assert bos.next_term.next_term.next_term.symbol.name == '<Multinode>'

    def test_multinode_nonlbox_and_lbox(self):
        self.reset()
        inputstring = '''x="""a\x80bc"""'''

        for i in inputstring:
            self.treemanager.key_normal(i)

        bos = self.parser.previous_version.parent.children[0]
        assert bos.next_term.symbol.name == "x"
        assert bos.next_term.next_term.symbol.name == "="
        assert bos.next_term.next_term.next_term.symbol.name == '"""a\x80bc"""'

        self.treemanager.cursor_movement(LEFT)
        self.treemanager.cursor_movement(LEFT)
        self.treemanager.cursor_movement(LEFT)
        self.treemanager.cursor_movement(LEFT)

        self.treemanager.add_languagebox(lang_dict["SQL (Dummy)"])
        self.treemanager.key_normal("S")
        bos = self.parser.previous_version.parent.children[0]
        assert bos.next_term.symbol.name == "x"
        assert bos.next_term.next_term.symbol.name == "="
        assert bos.next_term.next_term.next_term.symbol.name == '<Multinode>'
        multi = bos.next_term.next_term.next_term
        assert multi.children[0].symbol.name == "\"\"\"a\x80b"
        assert type(multi.children[1].symbol) is MagicTerminal
        assert multi.children[2].symbol.name == "c\"\"\""

    def test_multinode_merged_first(self):
        self.reset()
        inputstring = '''"""a\rbc"""'''

        for i in inputstring:
            self.treemanager.key_normal(i)

        for i in 'def"""':
            self.treemanager.key_normal(i)

        bos = self.parser.previous_version.parent.children[0]
        assert bos.next_term.symbol.name == "<Multinode>"
        assert bos.next_term.next_term.symbol.name == 'def'
        assert bos.next_term.next_term.next_term.symbol.name == '""'
        assert bos.next_term.next_term.next_term.next_term.symbol.name == '"'

        self.treemanager.cursor_movement(LEFT)
        self.treemanager.cursor_movement(LEFT)
        self.treemanager.cursor_movement(LEFT)
        self.treemanager.cursor_movement(LEFT)
        self.treemanager.cursor_movement(LEFT)
        self.treemanager.cursor_movement(LEFT)

        self.treemanager.key_backspace()
        self.treemanager.key_backspace()
        self.treemanager.key_backspace()

        assert bos.next_term.symbol.name == "<Multinode>"
        assert bos.next_term.next_term.symbol.name == "NEWLINE"
        assert bos.next_term.next_term.next_term.symbol.name == "eos"

    def test_multinode_string_bug(self):
        self.reset()
        inputstring = '''x="abc"'''
        for i in inputstring:
            self.treemanager.key_normal(i)

        self.treemanager.cursor_movement(LEFT)
        self.treemanager.add_languagebox(lang_dict["SQL (Dummy)"])
        self.treemanager.key_normal("x")

        bos = self.parser.previous_version.parent.children[0]
        x = bos.next_term
        assert x.symbol.name == "x"
        eq = x.next_term
        assert eq.symbol.name == "="
        multi = eq.next_term
        assert multi.lookup == "dstring"
        assert multi.symbol.name == "<Multinode>"

        self.treemanager.cursor_movement(RIGHT)
        self.treemanager.key_backspace()

        # removing the ending quote results in a lexingerror,
        # so the multinode remains
        assert eq.next_term.symbol.name == "<Multinode>"

        # now remove the first quote, which should lead to the destruction of
        # the multinode
        self.treemanager.cursor_movement(LEFT)
        self.treemanager.cursor_movement(LEFT)
        self.treemanager.cursor_movement(LEFT)
        self.treemanager.cursor_movement(LEFT)
        self.treemanager.key_backspace()
        assert eq.next_term.symbol.name == "abc"

    def test_multinode_string_bug2(self):
        self.reset()
        inputstring = '''x="abc"'''
        for i in inputstring:
            self.treemanager.key_normal(i)

        self.treemanager.cursor_movement(LEFT)
        self.treemanager.add_languagebox(lang_dict["SQL (Dummy)"])
        self.treemanager.key_normal("x")

        self.treemanager.leave_languagebox()
        self.treemanager.key_normal("z")
        bos = self.parser.previous_version.parent.children[0]
        x = bos.next_term
        assert x.symbol.name == "x"
        eq = x.next_term
        assert eq.symbol.name == "="
        multi = eq.next_term
        assert multi.children[0].symbol.name == "\"abc"
        assert multi.children[1].symbol.name == "<SQL (Dummy)>"
        assert multi.children[2].symbol.name == "z\""

class Test_MultiTextNodePHP:

    def setup_class(cls):
        parser, lexer = php.load()
        cls.lexer = lexer
        cls.parser = parser
        cls.parser.init_ast()
        cls.ast = cls.parser.previous_version
        cls.treemanager = TreeManager()
        cls.treemanager.add_parser(cls.parser, cls.lexer, php.name)

        cls.treemanager.set_font_test(7, 17) # hard coded. PyQt segfaults in test suite

    def test_paste_comment(self):
        paste = """$shake_error_codes = array( 'empty_password', 'empty_email', 'invalid_email', 'invalidcombo', 'empty_username', 'invalid_username', 'incorrect_password' );
	/**
	 * Filters the error codes array for shaking the login form.
	 *
	 * @since 3.0.0
	 *
	 * @param array $shake_error_codes Error codes that shake the login form.
	 */
	$shake_error_codes = apply_filters( 'shake_error_codes', $shake_error_codes );"""

        self.treemanager.pasteText(paste)
