import sys
import os
import random
import traceback
from grammars.grammars import lang_dict
from incparser.astree import BOS, EOS, TextNode, MultiTextNode
from grammar_parser.gparser import MagicTerminal, Terminal
from treemanager import TreeManager
from utils import KEY_UP as UP, KEY_DOWN as DOWN, KEY_LEFT as LEFT, KEY_RIGHT as RIGHT

ext_to_lang = {
    ".py": "Python 2.7.5",
    ".java": "Java 1.5"
}

class FuzzyTester():
    """Runs test that randomly modify a given program and tests for exceptions.
    If an exception occurs, or the modifications had unwanted side-effects, a
    log is saved which can be used to create a stand-alone test."""

    def __init__(self, filename):
        _, ext = os.path.splitext(filename)
        self.setlang(ext_to_lang[ext])
        with open(filename) as f:
            self.program = f.read()
        self.log = []
        self.filename = filename

    def reset(self):
        self.parser.reset()
        self.treemanager = TreeManager()
        self.treemanager.add_parser(self.parser, self.lexer, self.lang.name)

    def setlang(self, lang):
        self.lang = lang_dict[lang]
        self.parser, self.lexer = lang_dict[lang].load()
        self.treemanager = TreeManager()
        self.treemanager.add_parser(self.parser, self.lexer, self.lang.name)

    def move(self, direction, times):
        for i in range(times):
            self.treemanager.cursor_movement(direction)

    def text_compare(self, original):
        """Compare the textual representation of two programs. Faster than
        tree_compare, but less accurate."""
        original = original.replace("\r", "").split("\n")
        current = self.treemanager.export_as_text("/dev/null").replace("\r", "").split("\n")
        for i in range(len(current)):
            assert original[i] == current[i]

    def next_node(self, node):
        if node.children:
            return node.children[0]
        while node.right_sibling() is None:
            node = node.parent
        return node.right_sibling()

    def tree_compare(self, node1, node2):
        """Given two root nodes, compares that both trees are equivalent"""
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

    def get_random_key(self):
        keys = list("abcdefghijklmnopqrstuvwxyz0123456789 \r:,.[]{}()!$%^&*()_+=")
        return random.choice(keys)

    def random_deletion(self):
        """Delete random characters within a program."""
        print("Running random_deletion on {}".format(self.filename))
        program = self.program

        self.treemanager.import_file(program)
        assert self.parser.last_status == True

        self.text_compare(program)

        line_count = len(self.treemanager.lines)
        random_lines = list(range(line_count))
        random.shuffle(random_lines)
        random_lines = random_lines[:20] # restrict to 20 lines to reduce runtime

        start_version = self.treemanager.version
        for linenr in random_lines:
            cols = list(range(20))
            random.shuffle(cols)
            for col in cols:
                self.treemanager.cursor_reset()
                self.log.append("self.treemanager.cursor_reset()")
                self.move(DOWN, linenr)
                self.log.append("self.move(DOWN, %s)" % linenr)
                self.move(RIGHT, col)
                self.log.append("self.move(RIGHT, %s)" % col)
                self.log.append("self.treemanager.key_delete()")
                x = self.treemanager.key_delete()
                if x == "eos":
                    continue
            self.treemanager.undo_snapshot()
            self.log.append("self.treemanager.undo_snapshot()")

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
        parser, lexer = self.lang.load()
        parser.init_ast()
        t1.add_parser(parser, lexer, self.lang.name)
        t1.set_font_test(7, 17)
        t1.import_file(self.program)

        assert self.parser.last_status == True
        assert parser.last_status == True

        self.tree_compare(self.parser.previous_version.parent, parser.previous_version.parent)

    def random_insertion(self):
        """Insert random characters at random locations within a program."""
        print("Running random_insert on {}".format(self.filename))
        self.reset()

        self.treemanager.import_file(self.program)
        assert self.parser.last_status == True

        self.text_compare(self.program)

        line_count = len(self.treemanager.lines)
        random_lines = list(range(line_count))
        random.shuffle(random_lines)

        start_version = self.treemanager.version
        for linenr in random_lines:
            cols = list(range(20))
            random.shuffle(cols)
            for col in cols:
                self.log.append("self.treemanager.cursor_reset()")
                self.log.append("self.move(DOWN, %s)" % linenr)
                self.log.append("self.move(RIGHT, %s)" % col)
                self.treemanager.cursor_reset()
                self.move(DOWN, linenr)
                self.move(RIGHT, col)
                k = self.get_random_key()
                self.log.append("self.treemanager.key_normal(%s)" % repr(k))
                x = self.treemanager.key_normal(k)
                if x == "eos":
                    continue
            self.log.append("self.treemanager.undo_snapshot()")
            self.treemanager.undo_snapshot()

        end_version = self.treemanager.version
        broken = self.treemanager.export_as_text()

        # undo all and compare with original
        while self.treemanager.version > start_version:
            self.treemanager.key_ctrl_z()
        self.text_compare(self.program)

        # redo all and compare with broken
        while self.treemanager.version < end_version:
            self.treemanager.key_shift_ctrl_z()
        self.text_compare(broken)

        # undo again and compare with original
        while self.treemanager.version > start_version:
            self.treemanager.key_ctrl_z()
        self.text_compare(self.program)

        t1 = TreeManager()
        parser, lexer = self.lang.load()
        t1.add_parser(parser, lexer, self.lang.name)
        t1.import_file(self.program)

        self.tree_compare(self.parser.previous_version.parent, parser.previous_version.parent)

    def random_insertdelete(self):
        """Insert and delete random characters at random locations within a
        program."""
        print("Running random_insertdelete on {}".format(self.filename))
        self.reset()

        self.treemanager.import_file(self.program)
        assert self.parser.last_status == True

        self.text_compare(self.program)

        line_count = len(self.treemanager.lines)
        random_lines = list(range(line_count))
        random.shuffle(random_lines)
        random_lines = random_lines[:20] # restrict to 20 lines to reduce runtime

        start_version = self.treemanager.version
        for linenr in random_lines:
            cols = list(range(20))
            random.shuffle(cols)
            for col in cols:
                self.log.append("self.treemanager.cursor_reset()")
                self.log.append("self.move(%s, %s)" % (DOWN, linenr))
                self.log.append("self.move(%s, %s)" % (RIGHT, col))
                self.treemanager.cursor_reset()
                self.move(DOWN, linenr)
                self.move(RIGHT, col)
                k = self.get_random_key()
                if k in ["a", "c", "e", "g", "i", "k", "m", "1", "3", "5", "7"]:
                    # for a few characters DELETE instead of INSERT
                    self.log.append("self.treemanager.key_delete()")
                    x = self.treemanager.key_delete()
                else:
                    rk = self.get_random_key()
                    self.log.append("self.treemanager.key_normal(%s)" % rk)
                    x = self.treemanager.key_normal(rk)
                if x == "eos":
                    continue
            self.log.append("self.treemanager.undo_snapshot()")
            self.treemanager.undo_snapshot()

        end_version = self.treemanager.version
        broken = self.treemanager.export_as_text()

        # undo all and compare with original
        while self.treemanager.version > start_version:
            self.treemanager.key_ctrl_z()
        self.text_compare(self.program)

        # redo all and compare with broken
        while self.treemanager.version < end_version:
            self.treemanager.key_shift_ctrl_z()
        self.text_compare(broken)

        # undo again and compare with original
        while self.treemanager.version > start_version:
            self.treemanager.key_ctrl_z()
        self.text_compare(self.program)

        t1 = TreeManager()
        parser, lexer = self.lang.load()
        t1.add_parser(parser, lexer, self.lang.name)
        t1.import_file(self.program)

        self.tree_compare(self.parser.previous_version.parent, parser.previous_version.parent)

    def run(self):
        try:
            ft.random_deletion()
            self.reset()
            ft.random_insertion()
            self.reset()
            ft.random_insertdelete()
        except Exception as e:
            traceback.print_exc()
            print("Written log to 'fuzzy.log'.")
            with open("fuzzy.log", "w") as f:
                for l in self.log:
                    f.write(l)
                    f.write("\n")
        else:
            print("Passed.")

if __name__ == "__main__":
    filename = sys.argv[1]
    ft = FuzzyTester(filename)
    ft.run()
