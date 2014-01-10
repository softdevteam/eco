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

    def test_cursor_reset(self):
        self.treemanager.cursor_reset()
        assert isinstance(self.treemanager.cursor.node, BOS)

class Test_Python:

    def setup_class(cls):
        cls.lexer = IncrementalLexer(python275.priorities)
        cls.parser = IncParser(python275.grammar, 1, True)
        cls.parser.init_ast()
        cls.ast = cls.parser.previous_version
        cls.treemanager = TreeManager()
        cls.treemanager.add_parser(cls.parser, cls.lexer, python275.name)

        cls.treemanager.set_font_test(7, 17) # hard coded. PyQt segfaults in test suite

    def reset(self):
        self.parser.reset()
        self.treemanager = TreeManager()
        self.treemanager.add_parser(self.parser, self.lexer, python275.name)
        self.treemanager.set_font_test(7, 17)

    def move(self, direction, times):
        if direction == "up":
            for i in range(times): self.treemanager.cursor_movement(QtCore.Qt.Key_Up)
        if direction == "down":
            for i in range(times): self.treemanager.cursor_movement(QtCore.Qt.Key_Down)
        if direction == "left":
            for i in range(times): self.treemanager.cursor_movement(QtCore.Qt.Key_Left)
        if direction == "right":
            for i in range(times): self.treemanager.cursor_movement(QtCore.Qt.Key_Right)

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


class Test_Indentation(Test_Python):

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

    def test_indentation_stresstest(self):
        import random
        self.reset()
        inputstring = """class Connect4(object):
    UI_DEPTH = 5 # lookahead for minimax

    def __init__(self, p1_is_ai, p2_is_ai):
        self.top = tk.Tk()
        self.top.title("Unipycation: Connect 4 GUI (Python)")

        self.pl_engine = uni.Engine()

        # controls cpu/human players
        self.turn = None # True for p1, False for p2
        self.ai_players = { True : p1_is_ai, False : p2_is_ai }

        self.cols = []
        self.insert_buttons = []
        for colno in range(COLS):
            col = []
            b = tk.Button(self.top, text=str(colno), command=token_click_closure(self, colno))
            b.grid(column=colno, row=0)
            self.insert_buttons.append(b)

            for rowno in range(ROWS):
                b = tk.Button(self.top, state=tk.DISABLED)
                b.grid(column=colno, row=rowno + 1)
                col.append(b)
            self.cols.append(col)

        self.new_game_button = tk.Button(self.top, text="Start New Game", command=self._new)
        self.new_game_button.grid(column=COLS, row=0)

        self.status_text = tk.Label(self.top, text="---")
        self.status_text.grid(column=COLS, row=1)

    def _set_status_text(self, text):
        self.status_text["text"] = text

    def _update_from_pos_one_colour(self, pylist, colour):
        assert colour in ["red", "yellow"]

        for c in pylist:
            assert c.name == "c"
            (x, y) = c
            self.cols[x][y]["background"] = colour

    def _turn(self):
        # Not pretty, but works...
        while True:
            self.turn = not self.turn # flip turn
            if self.ai_players[self.turn]:
                self._set_status_text("%s AI thinking" % (self._player_colour().title()))
                self._ai_turn()
                if self._check_win(): break # did the AI player win?
            else:
                self._set_status_text("%s human move" % (self._player_colour().title()))
                break # allow top loop to deal with human turn

    def _end(self, winner_colour=None):
        for i in self.insert_buttons:
            i["state"] = tk.DISABLED

        if winner_colour is not None:
            self.new_game_button["background"] = winner_colour
            self._set_status_text("%s wins" % winner_colour)"""

        self.treemanager.import_file(inputstring)
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
