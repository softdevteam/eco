# Copyright (c) 2013--2014 King's College London
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

from incparser.incparser import IncParser
from inclexer.inclexer import IncrementalLexer
from cflexer.lexer import LexingError
from incparser.astree import TextNode, BOS, EOS, MultiTextNode
from grammar_parser.gparser import Terminal, MagicTerminal, IndentationTerminal
from PyQt4.QtGui import QApplication
from PyQt4.QtCore import QSettings
from grammars.grammars import lang_dict, Language, EcoFile
from indentmanager import IndentationManager
from export import HTMLPythonSQL, PHPPython, ATerms
from export.jruby import JRubyExporter
from export.jruby_simple_language import JRubySimpleLanguageExporter
from export.jruby_javascript import JRubyJavaScriptExporter
from export.simple_language import SimpleLanguageExporter
from export.cpython import CPythonExporter
from utils import arrow_keys, KEY_UP, KEY_DOWN, KEY_LEFT, KEY_RIGHT

import math

class FontManager(object):
    def __init__(self):
        self.fontht = 0
        self.fontwt = 0

fontmanager = FontManager()

class NodeSize(object):
    def __init__(self, w, h):
        self.w = w
        self.h = h

class Line(object):
    def __init__(self, node, height=1):
        self.node = node        # this lines newline node
        self.height = height    # line height
        self.width = 0          # line width
        self.indent = 0         # line indentation
        self.ws = 0

    def __repr__(self):
        return "Line(%s, width=%s, height=%s)" % (self.node, self.width, self.height)

class Cursor(object):
    def __init__(self, node, pos, line, lines):
        self.node = node
        self.pos = pos
        self.line = line
        self.lines = lines
        self.log = {}

    def save(self, version):
        self.log[version] = (self.node, self.pos, self.line)

    def load(self, version, lines):
        (self.node, self.pos, self.line) = self.log[version]
        self.lines = lines

    def clean_versions(self, version):
        for key in self.log.keys():
            if key > version:
                del self.log[key]

    def copy(self):
        return Cursor(self.node, self.pos, self.line, self.lines)

    def fix(self):
        while self.node.deleted:
            self.pos = 0
            self.left()
        while self.pos > len(self.node.symbol.name):
            self.pos -= len(self.node.symbol.name)
            self.node = self.find_next_visible(self.node)

    def left(self):
        node = self.node
        if not self.is_visible(node):
            node = self.find_previous_visible(self.node)
        if node.symbol.name == "\r":
            self.line -= 1
        if isinstance(node, BOS):
            return
        if not node is self.node:
            self.node = node
            self.pos = len(node.symbol.name)
        if self.pos > 1 and (not node.image or node.plain_mode):
            self.pos -= 1
        else:
            node = self.find_previous_visible(node)
            self.node = node
            self.pos = len(node.symbol.name)

    def right(self):
        node = self.node
        if not self.is_visible(node):
            node = self.find_next_visible(self.node)
        if isinstance(node, EOS):
            return
        if not node is self.node:
            self.node = node
            self.pos = 0
            if node.symbol.name == "\r":
                self.line += 1
        if self.pos < len(self.node.symbol.name):
            self.pos += 1
        else:
            node = self.find_next_visible(node)
            if node.symbol.name == "\r":
                self.line += 1
            if isinstance(node, EOS):
                return
            self.node = node
            self.pos = 1
            if node.image and not node.plain_mode:
                self.pos = len(node.symbol.name)

    def jump_to(self, other):
        """Apply other attributes to self.

        This ensures that the history is not lost.
        `self.cursor = other.copy()` becomes
        `self.cursor.jump_to(other)`.
        """

        self.node = other.node
        self.pos = other.pos
        self.line = other.line

    def jump_left(self):
        if self.node.symbol.name == "\r":
            self.line -= 1
        self.node = self.find_previous_visible(self.node)
        self.pos = len(self.node.symbol.name)

    def jump_right(self):
        node = self.find_next_visible(self.node)
        if self.inside() or isinstance(node, EOS):
            self.pos = len(self.node.symbol.name)
            return
        self.node = node
        self.pos = len(self.node.symbol.name)
        if node.symbol.name == "\r":
            self.line += 1

    def find_next_visible(self, node):
        if self.is_visible(node) or isinstance(node.symbol, MagicTerminal):
            node = node.next_terminal()
        while not self.is_visible(node):
            if isinstance(node, EOS):
                root = node.get_root()
                lbox = root.get_magicterminal()
                if lbox:
                    node = lbox.next_terminal()
                    continue
                else:
                    return node
            elif isinstance(node.symbol, MagicTerminal):
                node = node.symbol.ast.children[0]
                continue
            elif isinstance(node, MultiTextNode):
                node = node.children[0]
                continue
            node = node.next_terminal()
        return node

    def find_previous_visible(self, node):
        if self.is_visible(node):
            node = node.previous_terminal() # XXX check for multiterm
        while not self.is_visible(node):
            if isinstance(node, BOS):
                root = node.get_root()
                lbox = root.get_magicterminal()
                if lbox:
                    node = lbox.previous_terminal() #XXX check for multiterm
                    continue
                else:
                    return node
            elif isinstance(node.symbol, MagicTerminal):
                node = node.symbol.ast.children[-1]
                continue
            elif isinstance(node, MultiTextNode):
                node = node.children[-1]
                continue
            node = node.previous_terminal()
        return node

    def is_visible(self, node):
        if isinstance(node.symbol, IndentationTerminal):
            return False
        if isinstance(node, BOS):
            return False
        if isinstance(node, EOS):
            return False
        if isinstance(node.symbol, MagicTerminal):
            return False
        if isinstance(node.symbol, MultiTextNode):
            return False
        return True

    def up(self):
        if self.line > 0:
            x = self.get_x()
            self.line -= 1
            self.move_to_x(x)

    def down(self):
        if self.line < len(self.lines) - 1:
            x = self.get_x()
            self.line += 1
            self.move_to_x(x)

    def home(self):
        self.node = self.lines[self.line].node
        self.pos = len(self.node.symbol.name)

    def end(self):
        if self.line < len(self.lines)-1:
            self.node = self.find_previous_visible(self.lines[self.line+1].node)
        else:
            while not isinstance(self.node, EOS):
                self.node = self.node.next_terminal()
            self.node = self.find_previous_visible(self.node)
        self.pos = len(self.node.symbol.name)

    def move_to_x(self, x):
        node = self.lines[self.line].node
        while x > 0:
            newnode = self.find_next_visible(node)
            if newnode is node:
                self.node = node
                self.pos = len(node.symbol.name)
                return
            node = newnode
            if node.image and not node.plain_mode:
                x -= self.get_nodesize_in_chars(node).w
            else:
                x -= len(node.symbol.name)
            if node.symbol.name == "\r" or isinstance(node, EOS):
                self.node = self.find_previous_visible(node)
                self.pos = len(self.node.symbol.name)
                return
        self.pos = len(node.symbol.name) + x
        self.node = node

    def get_x(self):
        if self.node.symbol.name == "\r" or isinstance(self.node, BOS):
            return 0

        if self.node.image and not self.node.plain_mode:
            x = self.get_nodesize_in_chars(self.node).w
        else:
            x = self.pos
        node = self.find_previous_visible(self.node)
        while node.symbol.name != "\r" and not isinstance(node, BOS):
            if node.image and not node.plain_mode:
                x += self.get_nodesize_in_chars(node).w
            else:
                x += len(node.symbol.name)
            node = self.find_previous_visible(node)
        return x

    def get_nodesize_in_chars(self, node):
        gfont = QApplication.instance().gfont
        if node.image:
            w = math.ceil(node.image.width() * 1.0 / gfont.fontwt)
            h = math.ceil(node.image.height() * 1.0 / gfont.fontht)
            return NodeSize(w, h)
        else:
            return NodeSize(len(node.symbol.name), 1)

    def inside(self):
        return self.pos > 0 and self.pos < len(self.node.symbol.name)

    def isend(self):
        if isinstance(self.node.symbol, MagicTerminal):
            return True
        return self.pos == len(self.node.symbol.name)

    def __eq__(self, other):
        if isinstance(other, Cursor):
            return self.node is other.node and self.pos == other.pos
        return False

    def __ne__(self, other):
        return not self == other

    def __gt__(self, other):
        if self.line > other.line:
            return True
        if self.line < other.line:
            return False
        if self.get_x() > other.get_x():
            return True
        return False

    def __lt__(self, other):
        return not (self > other or self == other)

    def __repr__(self):
        return "Cursor(%s, %s)" % (self.node, self.pos)

class TreeManager(object):
    version = 1

    def __init__(self):
        self.lines = []             # storage for line objects
        self.mainroot = None        # root node (main language)
        self.parsers = []           # stores all currently used parsers
        self.edit_rightnode = False # changes which node to select when inbetween two nodes
        self.changed = False
        self.last_search = ""
        self.version = 1
        TreeManager.version = 1
        self.last_saved_version = 1
        self.savenextparse = False
        self.saved_lines = {}
        self.saved_parsers = {}
        self.undo_snapshots = []

        self.tool_data_is_dirty = False

        # This code and the can_profile() method should probably be refactored.
        self.langs_with_profiler = {
            "Python + Prolog" : False,
            "HTML + Python + SQL" : False,
            "PHP + Python" : False,
            "PHP" : False,
            "Python 2.7.5" : True,
            "SimpleLanguage" : False,
            "Ruby" : True,
            "Ruby + SimpleLanguage" : True,
            "Ruby + JavaScript" : True,
        }
        self.langs_with_debugger = {
            "Python 2.7.5"
        }
        self.input_log = []

    def can_profile(self):
        lang_name = self.parsers[0][2]
        if lang_name in self.langs_with_profiler:
            return self.langs_with_profiler[lang_name]
        return False

    def can_debug(self, main_lang):
        return main_lang in self.langs_with_debugger

    def log_input(self, method, *args):
        self.input_log.append("self.%s(%s)" % (method, ", ".join(args)))

    def set_font_test(self, width, height):
        # only needed for testing
        self.fontht = height
        self.fontwt = width
        fontmanager.fontwt = self.fontwt
        fontmanager.fontht = self.fontht

    def hasSelection(self):
        return self.selection_start != self.selection_end

    def get_bos(self):
        return self.parsers[0][0].previous_version.parent.children[0]

    def get_eos(self):
        return self.parsers[0][0].previous_version.parent.children[-1]

    def get_mainparser(self):
        return self.parsers[0][0]

    def delete_parser(self, root):
        for p in self.parsers:
            if p[0].previous_version.parent is root:
                self.parsers.remove(p)

    def get_parser(self, root):
        for parser, lexer, lang, _, im in self.parsers:
            if parser.previous_version.parent is root:
                return parser

    def get_lexer(self, root):
        for parser, lexer, lang, _, im in self.parsers:
            if parser.previous_version.parent is root:
                return lexer

    def get_language(self, root):
        for parser, lexer, lang, _, im in self.parsers:
            if parser.previous_version.parent is root:
                return lang

    def get_indentmanager(self, root):
        for parser, lexer, lang, _, im in self.parsers:
            if parser.previous_version.parent is root:
                return im

    def add_parser(self, parser, lexer, language):
        analyser = self.load_analyser(language)
        if lexer.is_indentation_based():
            im = IndentationManager(parser.previous_version.parent)
            parser.indentation_based = True
        else:
            im = None
        self.parsers.append((parser, lexer, language, analyser, im))
        parser.inc_parse()
        if len(self.parsers) == 1:
            self.lines.append(Line(parser.previous_version.parent.children[0]))
            self.mainroot = parser.previous_version.parent
            self.cursor = Cursor(self.mainroot.children[0], 0, 0, self.lines)
            self.selection_start = self.cursor.copy()
            self.selection_end = self.cursor.copy()
            lboxnode = self.create_node("<%s>" % language, lbox=True)
            lboxnode.parent_lbox = None
            lboxnode.symbol.parser = self.mainroot
            lboxnode.symbol.ast = self.mainroot
            self.main_lbox = lboxnode
            self.save()
            self.input_log.append("# Main language: %s" % language)

    def load_analyser(self, language):
        try:
            lang = lang_dict[language]
        except KeyError:
            return
        if isinstance(lang, EcoFile):
            import os
            filename = os.path.splitext(lang.filename)[0] + ".nb"
            if os.path.exists(filename):
                from astanalyser import AstAnalyser
                return AstAnalyser(filename)

    def get_languagebox(self, node):
        root = node.get_root()
        lbox = root.get_magicterminal()
        return lbox

    def has_error(self, node):
        for p in self.parsers:
            if p[3] and p[3].has_error(node):
                return True
        return False

    def get_error(self, node):
        for p in self.parsers:
            # check for syntax error
            if node is p[0].error_node:
                return "Syntax error on token '%s' (%s)." % (node.symbol.name, node.lookup)
            # check for namebinding error
            if p[3]:
                error = p[3].get_error(node)
                if error != "":
                    return error
        return ""

    def analyse(self):
        if self.parsers[0][2] == "PHP + Python":
            self.parsers[0][3].analyse(self.parsers[0][0].previous_version.parent, self.parsers)
            return

        for p in self.parsers:
            if p[0].last_status:
                if p[3]:
                    p[3].analyse(p[0].previous_version.parent)

    def getCompletion(self):
        for p in self.parsers:
            if p[3]:
                return p[3].get_completion(self.cursor.node)

    # ============================ ANALYSIS ============================= #

    def get_node_from_cursor(self):
        return self.cursor.node

    def get_selected_node(self):
        node = self.get_node_from_cursor()
        return node

    def get_nodes_from_selection(self):
        cur_start = min(self.selection_start, self.selection_end)
        cur_end = max(self.selection_start, self.selection_end)

        if cur_start == cur_end:
            return

        start_node = cur_start.node
        diff_start = 0
        if cur_start.inside():
            diff_start = cur_start.pos
            include_start = True
        else:
            include_start = False

        end_node = cur_end.node
        diff_end = len(end_node.symbol.name)

        if cur_end.inside():
            diff_end = cur_end.pos

        if not cur_start.inside():
            start = start_node.next_term


        if start_node is end_node:
            return ([start_node], diff_start, diff_end)

        start = start_node
        end = end_node

        if start is None or end is None or isinstance(start, EOS):
            return ([],0,0)

        nodes = []
        if include_start:
            nodes.append(start)
        node = start.next_terminal()
        while node is not end:
            # extend search into magic tree
            if isinstance(node.symbol, MagicTerminal):
                node = node.symbol.parser.children[0]
                continue
            # extend search outside magic tree
            if isinstance(node, EOS):
                root = node.get_root()
                magic = root.get_magicterminal()
                if magic:
                    node = magic.next_terminal()
                    continue
            nodes.append(node)
            node = node.next_terminal()
        nodes.append(end)

        return (nodes, diff_start, diff_end)

    def is_logical_line(self, y):
        newline_node = self.lines[y].node
        node = newline_node.next_term
        while True:
            if isinstance(node, EOS):
                return False
            if node.lookup == "<return>": # reached next line
                return False
            if node.lookup == "<ws>":
                node = node.next_term
                continue
            if  isinstance(node.symbol, IndentationTerminal):
                node = node.next_term
                continue
            # if we are here, we reached a normal node
            return True

    def is_same_language(self, node, other):
        root = node.get_root()
        other_root = other.get_root()
        return root is other_root

    def get_indentation(self, y):
        # indentation whitespaces
        if not self.is_logical_line(y):
            return None

        newline = self.lines[y].node # get newline node
        node = newline.next_term     # get first node in line

        while isinstance(node.symbol, IndentationTerminal):
            node = node.next_term

        if node.lookup == "<ws>":
            return len(node.symbol.name)

        return 0

    def getLookaheadList(self):
        selected_node = self.get_node_from_cursor()
        root = selected_node.get_root()
        lrp = self.get_parser(root)
        return lrp.get_next_symbols_list(selected_node.state)

    def find_next(self):
        self.log_input("find_next")
        if self.last_search != "":
            self.find_text(self.last_search)

    def find_text_no_cursor(self, text, parent_name='funcdef'):
        # FIXME - infinite loop!
        temp = self.cursor.copy()
        while True:
            self.find_text(text)
            if self.cursor.node.parent.symbol.name != parent_name:
                continue
            node = self.cursor.node
            break
        self.cursor = temp
        return node

    def find_text(self, text):
        startnode = self.cursor.node
        node = self.cursor.node.next_term
        line = self.cursor.line
        index = -1
        while node is not self.cursor.node:
            if node is startnode:
                break
            if isinstance(node.symbol, MagicTerminal):
                node = node.symbol.ast.children[0]
                continue
            if isinstance(node, EOS):
                root = node.get_root()
                lbox = root.get_magicterminal()
                if lbox:
                    node = lbox.next_term
                    continue
                else:
                    # start from beginning
                    node = self.get_bos()
                    line = 0
            index = node.symbol.name.find(text)
            if index > -1:
                break

            if node.symbol.name == "\r":
                line += 1
            node = node.next_term
        if index > -1:
            self.cursor.line = line
            self.cursor.node = node
            self.cursor.pos = index
            self.selection_start = self.cursor.copy()
            self.cursor.pos += len(text)
            self.selection_end = self.cursor.copy()
        self.last_search = text

    def jump_to_error(self, parser):
        bos = parser.previous_version.parent.children[0]
        eos = parser.previous_version.parent.children[-1]
        node = bos
        while node is not eos:
            if node is parser.error_node:
                break
            node = node.next_term

        # get linenode
        linenode = node
        while True:
            if isinstance(linenode, BOS):
                break
            if linenode is None:
                break
            if linenode.symbol.name == "\r":
                break
            linenode = self.cursor.find_previous_visible(linenode)

        # get line number
        linenr = 0
        for line in self.lines:
            if linenode is None:
                break
            if line.node is linenode:
                break
            linenr += 1

        self.cursor.line = linenr
        self.cursor.node = node
        self.cursor.pos = 0
        if node is eos:
            lbox = node.get_root().get_magicterminal()
            if lbox:
                self.cursor.node = node.prev_term
            else:
                self.cursor.node = self.cursor.find_previous_visible(node)
            self.cursor.pos = len(self.cursor.node.symbol.name)
        if isinstance(node.symbol, MagicTerminal):
            self.cursor.node = self.cursor.find_previous_visible(node)
            self.cursor.pos = len(self.cursor.node.symbol.name)
        self.selection_start = self.cursor.copy()
        self.selection_end = self.cursor.copy()

    # ============================ MODIFICATIONS ============================= #

    def key_shift_ctrl_z(self):
        self.log_input("key_shift_ctrl_z")
        try:
            i = self.undo_snapshots.index(self.version)
            if i == len(self.undo_snapshots) - 1:
                return
            undo_amount = self.undo_snapshots[i+1] - self.undo_snapshots[i]
        except ValueError:
            undo_amount = self.undo_snapshots[0] - self.version
        for i in range(undo_amount):
            self.version += 1
            TreeManager.version = self.version
            self.recover_version("redo")
            self.cursor.load(self.version, self.lines)

    def get_max_version(self):
        root = self.get_bos().parent
        maxversion = 0
        for (key, version) in root.log.keys():
            maxversion = max(maxversion, version)
        return maxversion

    def key_ctrl_z(self):
        self.log_input("key_ctrl_z")
        if len(self.undo_snapshots) == 0 and self.get_max_version() > 1:
            self.undo_snapshots.append(self.version)
        if not self.undo_snapshots:
            return
        if self.undo_snapshots[-1] != self.get_max_version() and self.version == self.get_max_version():
            # if there are unsaved changes, save before undo so we can redo them again
            self.undo_snapshots.append(self.version)
        try:
            i = self.undo_snapshots.index(self.version)
        except ValueError:
            return
        if i == 0:
            undo_amount = self.version - 1
        else:
            undo_amount = self.undo_snapshots[i] - self.undo_snapshots[i-1]
        for i in range(undo_amount):
            self.version -= 1
            TreeManager.version = self.version
            self.recover_version("undo")
            self.cursor.load(self.version, self.lines)

    def recover_version(self, direction):
        self.load_lines()
        self.load_parsers()
        for l in self.parsers:
            parser = l[0]
            parser.load_status(self.version)
            root = parser.previous_version.parent
            #root = self.cursor.node.get_root()#get_bos().parent
            root.load(self.version)
            bos = root.children[0]
            bos.load(self.version)
            eos = root.children[-1]
            eos.load(self.version)
            node = self.pop_lookahead(bos)
            while True:
                if isinstance(node, EOS):
                    break
                prev_version = node.version
                if direction == "undo":
                    # recover old version if changes were made in that version
                    if not node.has_changes(self.version):
                        node = self.pop_lookahead(node)
                        continue
                elif direction == "redo":
                    # recover newer version of node.version is smaller
                    # however, if after reloading the version stays the same
                    # we don't have to update the whole subtree
                    if node.version < self.version:
                        node.load(self.version)
                        if node.version == prev_version:
                            node = self.pop_lookahead(node)
                            continue
                node.load(self.version)
                # continue with children
                if len(node.children) > 0:
                    node = node.children[0]
                    continue
                else:
                    # skip subtree and continue otherwise
                    node = self.pop_lookahead(node)

    def pop_lookahead(self, la):
        while(la.right_sibling() is None):
            la = la.parent
        return la.right_sibling()

    def clean_versions(self, version):
        # clean linenumbers
        for key in self.saved_lines.keys():
            if key > version:
                del self.saved_lines[key]
        for key in self.saved_parsers.keys():
            if key > version:
                del self.saved_parsers[key]
        self.cursor.clean_versions(version)
        for i in range(len(self.undo_snapshots)):
            if self.undo_snapshots[i] > version:
                self.undo_snapshots = self.undo_snapshots[:i]
                break

        for l in self.parsers:
            p = l[0]
            root = p.previous_version.parent
            bos = root.children[0]
            self.delete_versions_from(bos, version)
            self.delete_versions_from(root, version)
            node = self.pop_lookahead(root.children[0])
            while True:
                if isinstance(node, EOS):
                    break
                self.delete_versions_from(node, version)
                if len(node.children) > 0:
                    node = node.children[0]
                    continue
                else:
                    node = self.pop_lookahead(node)

    def delete_versions_from(self, node, version):
        for (key, v) in node.log.keys():
            if v > version:
                del node.log[(key, v)]

    def save_lines(self):
        # check if lines have changed
        lines = self.get_lines_from_version(self.version)
        if len(lines) != len(self.lines):
            self.saved_lines[self.version] = list(self.lines)
            return

        # check if nodes are different (e.g. we could delete and reinsert a line between saves)
        for i in range(len(lines)):
            if lines[i] is not self.lines[i]:
                self.saved_lines[self.version] = list(self.lines)
                return

    def get_lines_from_version(self, version):
        version = self.version
        while True:
            if version == -1:
                return []
            try:
                l = self.saved_lines[version]
                break
            except KeyError:
                version -= 1
        return l

    def load_lines(self):
        version = self.version
        while True:
            if version == 0:
                return
            try:
                l = self.saved_lines[version]
                break
            except KeyError:
                version -= 1
        self.lines = list(l) # copy, otherwise saved list will be mutated

    def save_parsers(self):
        self.saved_parsers[self.version] = list(self.parsers)

    def load_parsers(self):
        self.parsers = list(self.saved_parsers[self.version])

    def save(self):
        self.save_lines()
        self.save_parsers()
        self.cursor.save(self.version)
        for l in self.parsers:
            parser = l[0]
            parser.save_status(self.version)
            root = parser.previous_version.parent
            root.save(self.version)
            bos = root.children[0]
            bos.save(self.version)
            eos = root.children[-1]
            eos.save(self.version)
            node = self.pop_lookahead(bos)
            while True:
                if isinstance(node, EOS):
                    node.save(self.version)
                    break
                if node.has_changes():
                    node.save(self.version)
                    if len(node.children) > 0:
                        node = node.children[0]
                        continue
                node = self.pop_lookahead(node)

    def key_home(self, shift=False):
        self.log_input("key_home", str(shift))
        self.unselect()
        self.cursor.home()
        if shift:
            self.selection_end = self.cursor.copy()

    def key_end(self, shift=False):
        self.log_input("key_end", str(shift))
        self.unselect()
        self.cursor.end()
        if shift:
            self.selection_end = self.cursor.copy()

    def key_normal(self, text):
        self.log_input("key_normal", repr(str(text)))
        indentation = 0
        self.tool_data_is_dirty = True

        if self.hasSelection():
            self.deleteSelection()
            self.input_log.pop()
            self.input_log.pop()

        edited_node = self.cursor.node

        if text == "\r":
            # if previous line is a language box, don't use its indentation
            y = self.cursor.line
            node = self.lines[y].node
            current_root = self.cursor.node.get_root()
            while node.get_root() is not current_root:
                y -= 1
                if y < 0:
                    y = 0
                    break
                node = self.lines[y].node
            indentation = self.get_indentation(y)
            if indentation is None:
                indentation = 0
            text += " " * indentation

        node = self.get_node_from_cursor()
        if node.image and not node.plain_mode:
            self.leave_languagebox()
            node = self.get_node_from_cursor()
        # edit node
        if self.cursor.inside():
            internal_position = self.cursor.pos #len(node.symbol.name) - (x - self.cursor.x)
            node.insert(text, internal_position)
        else:
            # append to node: [node newtext] [next node]
            pos = 0
            if str(text).startswith("\r"):
                newnode = TextNode(Terminal(""))
                node.insert_after(newnode)
                node = newnode
                self.cursor.pos = 0
            elif isinstance(node, BOS) or node.symbol.name == "\r":
                # insert new node: [bos] [newtext] [next node]
                old = node
                if old.next_term:
                    # skip over IndentationTerminals
                    old = old.next_term
                    while isinstance(old.symbol, IndentationTerminal):
                        old = old.next_term
                    old = old.prev_term
                node = TextNode(Terminal(""))
                old.insert_after(node)
                self.cursor.pos = 0
            elif isinstance(node.symbol, MagicTerminal):
                old = node
                node = TextNode(Terminal(""))
                old.insert_after(node)
                self.cursor.pos = 0
            else:
                pos = self.cursor.pos#len(node.symbol.name)
            node.insert(text, pos)
            self.cursor.node = node
        self.cursor.pos += len(text)

        need_reparse = self.relex(node)
        self.cursor.fix()
        self.fix_cursor_on_image()
        temp = self.cursor.node
        self.cursor.node = edited_node
        need_reparse |= self.post_keypress(text)
        self.cursor.node = temp
        self.reparse(node, need_reparse)
        self.changed = True
        return indentation

    def key_backspace(self):
        self.log_input("key_backspace")
        self.tool_data_is_dirty = True
        node = self.get_selected_node()
        if node is self.mainroot.children[0] and not self.hasSelection():
            return
        if node.image is not None and not node.plain_mode:
            return
        if self.cursor.node.symbol.name == "\r":
            self.cursor.node = self.cursor.find_previous_visible(self.cursor.node)
            self.cursor.line -= 1
            self.cursor.pos = len(self.cursor.node.symbol.name)
        else:
            self.cursor.left()
        self.key_delete()
        self.input_log.pop()

    def key_delete(self):
        self.log_input("key_delete")
        self.tool_data_is_dirty = True
        node = self.get_node_from_cursor()

        if self.hasSelection():
            self.deleteSelection()
            self.reparse(self.cursor.node, True)
            return

        if self.cursor.inside(): # cursor inside a node
            internal_position = self.cursor.pos
            self.last_delchar = node.backspace(internal_position)
            need_reparse = self.relex(node)
            repairnode = node
        else: # between two nodes
            need_reparse = False
            node = self.cursor.find_next_visible(node) # delete should edit the node to the right from the selected node
            # if lbox is selected, select first node in lbox
            if isinstance(node, EOS):
                lbox = self.get_languagebox(node)
                if lbox:
                    node = lbox.next_term
                else:
                    return "eos"
            while isinstance(node.symbol, IndentationTerminal):
                node = node.next_term
            if isinstance(node.symbol, MagicTerminal):
                self.leave_languagebox()
                self.key_delete()
                return
            if node.image and not node.plain_mode:
                return
            if node.symbol.name == "\r":
                self.remove_indentation_nodes(node.next_term)
                self.delete_linebreak(self.cursor.line, node)
            self.last_delchar = node.backspace(0)
            repairnode = node

            # if node is empty, delete it and repair previous/next node
            if node.symbol.name == "" and not isinstance(node, BOS):
                repairnode = self.cursor.find_previous_visible(node)

                if not self.clean_empty_lbox(node):
                    # normal node is empty -> remove it from AST
                    node.parent.remove_child(node)
                    need_reparse = True

            if repairnode is not None and not isinstance(repairnode, BOS):
                need_reparse |= self.relex(repairnode)

        need_reparse |= self.post_keypress("")
        self.cursor.fix()
        self.reparse(repairnode, need_reparse)
        self.changed = True

    def start_new_selection(self):
        self.selection_start = self.cursor.copy()

    def key_shift(self):
        self.log_input("key_shift")

    def key_escape(self):
        self.log_input("key_escape")
        node = self.get_selected_node()
        if node.plain_mode:
            node.plain_mode = False

    def key_cursors(self, key, shift=False):
        self.log_input("key_cursors", arrow_keys[key.key], str(shift))
        self.edit_rightnode = False

        # Four possible cases:
        # no   shift, no   selection -> normal movement of cursor
        # no   shift, with selection -> jump cursor w.r.t selection
        # with shift, no   selection -> start new selection, modify selection
        # with shift, with selection -> modify selection

        if shift:
            if not self.hasSelection():
                self.selection_start = self.cursor.copy()
            self.cursor_movement(key)
            self.selection_end = self.cursor.copy()
        else:
            if self.hasSelection():
                self.jump_cursor_within_selection(key)
            else:
                self.cursor_movement(key)
            self.unselect()

    def jump_cursor_within_selection(self, key):
        """
            Jump cursor with respect to text selection.

            There are 4*2 = 8 different cases, with four different
            arrow keys and two selection directions.

            Note: The start of the selection does not equal the left end
                  of the selection in right-to-left selections.

            * LEFT:  Jump to left end of selection.
            * RIGHT: Jump to right end of selection.
            * UP:    Jump one line upwards w.r.t. left end of selection.
            * DOWN:  Jump one line downwards w.r.t. right end of selection.
        """
        selection_start, selection_end = sorted(
            [self.selection_start, self.selection_end])

        if key.left:
            self.cursor.jump_to(selection_start)
        elif key.right:
            self.cursor.jump_to(selection_end)
        elif key.up:
            self.cursor.jump_to(selection_start)
            self.cursor_movement(key)
        elif key.down:
            self.cursor.jump_to(selection_end)
            self.cursor_movement(key)

    def ctrl_cursor(self, key, shift=False):
        self.log_input("key_escape", arrow_keys[key.key])

        if shift and not self.hasSelection():
            self.start_new_selection()

        if key.left:
            self.cursor.jump_left()
        elif key.right:
            self.cursor.jump_right()

        if shift:
            self.selection_end = self.cursor.copy()

    def doubleclick_select(self):
        self.selection_start = self.cursor.copy()
        self.selection_start.node = self.cursor.find_previous_visible(self.cursor.node)
        self.selection_start.pos = len(self.selection_start.node.symbol.name)
        self.selection_end = self.cursor.copy()
        self.selection_end.pos = len(self.selection_end.node.symbol.name)
        self.cursor.pos = self.selection_end.pos
        self.cursor.node = self.selection_end.node

    def select_all(self):
        self.selection_start = Cursor(self.get_bos(), -1, 0, self.lines)
        self.cursor.node = self.get_eos()
        self.cursor.jump_left() # for now ignore invisible nodes
        self.cursor.pos = len(self.cursor.node.symbol.name)
        self.cursor.line = len(self.lines) - 1
        self.selection_end = self.cursor.copy()

    def get_all_annotations_with_hint(self, hint):
        """Return all annotations (optionally of a specific type).
        Call sparingly as this runs over the whole tree.
        """
        node = self.lines[0].node
        annotations = list()
        while True:
            for annote in node.get_annotations_with_hint(hint):
                annotations.append(annote.annotation)
            node = node.next_term
            if isinstance(node, EOS):
                lbnode = self.get_languagebox(node)
                if lbnode:
                    node = lbnode
                else:
                    break
        return annotations

    def unselect(self):
        self.selection_start = self.cursor.copy()
        self.selection_end = self.cursor.copy()

    def add_languagebox(self, language):
        if isinstance(language, str):
            # coming from apply_inputlog
            language = lang_dict[language]
        self.log_input("add_languagebox", repr(language.name))
        node = self.get_node_from_cursor()
        newnode = self.create_languagebox(language)
        root = self.cursor.node.get_root()
        newnode.parent_lbox = root
        if not self.cursor.inside():
            node.insert_after(newnode)
            self.relex(newnode)
        else:
            node = node
            internal_position = self.cursor.pos
            text1 = node.symbol.name[:internal_position]
            text2 = node.symbol.name[internal_position:]
            node.symbol.name = text1
            node.insert_after(newnode)

            node2 = TextNode(Terminal(text2))
            newnode.insert_after(node2)

            self.relex(node)
            #self.relex(node2)
        self.edit_rightnode = True # writes next char into magic ast
        self.cursor.node = newnode.symbol.ast.children[0]
        self.cursor.pos = 0
        self.reparse(newnode)
        self.changed = True

    def leave_languagebox(self):
        self.log_input("leave_languagebox")
        if isinstance(self.cursor.node.next_term.symbol, MagicTerminal) and self.cursor.isend():
            self.cursor.node = self.cursor.node.next_term.symbol.ast.children[0]
            self.cursor.pos = 0
        else:
            lbox = self.get_languagebox(self.cursor.node)
            if lbox:
                self.cursor.node = lbox
                self.cursor.pos = 0

    def create_languagebox(self, language):
        lbox = self.create_node("<%s>" % language.name, lbox=True)

        # Create parser, priorities and lexer
        incparser, inclexer = self.get_parser_lexer_for_language(language, True)
        root = incparser.previous_version.parent
        root.magic_backpointer = lbox
        self.add_parser(incparser, inclexer, language.name)

        lbox.symbol.parser = root
        lbox.symbol.ast = root
        lbox.plain_mode = True
        return lbox

    def surround_with_languagebox(self, language):
        self.log_input("surround_with_languagebox", repr(language.name))
        #XXX if partly selected node, need to split it
        nodes, _, _ = self.get_nodes_from_selection()
        self.edit_rightnode = False
        # cut text
        text = self.copySelection()
        self.deleteSelection()
        self.add_languagebox(language)
        self.pasteText(text)
        self.input_log.pop()
        self.input_log.pop()
        self.input_log.pop()
        return

    def change_languagebox(self, language):
        self.log_input("change_languagebox", repr(language.name))
        node = self.cursor.node
        root = node.get_root()
        lbox = root.get_magicterminal()
        if lbox:
            self.save_current_version()
            self.delete_parser(root)

            incparser, inclexer = self.get_parser_lexer_for_language(language, True)
            incparser.previous_version.parent = root
            self.add_parser(incparser, inclexer, language.name)
            lbox.symbol.name = "<%s>" % language

            # reparse outer and inner box
            node = root.children[0].next_term
            while not isinstance(node, EOS):
                if isinstance(node.symbol, IndentationTerminal):
                    node.parent.remove_child(node)
                else:
                    self.relex(node)
                node = node.next_term
            self.post_keypress("")
            self.reparse(root.children[0], True)
            self.reparse(lbox, True)

    def clean_empty_lbox(self, node):
        root = node.get_root()
        magic = root.get_magicterminal()
        next_node = node.next_terminal(skip_indent=True)
        previous_node = node.previous_terminal(skip_indent=True)
        if magic and isinstance(next_node, EOS) and isinstance(previous_node, BOS):
            # language box is empty -> delete it and all references
            self.cursor.node = self.cursor.find_previous_visible(previous_node)
            self.cursor.pos = len(self.cursor.node.symbol.name)
            magic.parent.remove_child(magic)
            self.delete_parser(root)
            return True
        return False

    def create_node(self, text, lbox=False):
        if lbox:
            symbol = MagicTerminal(text)
        else:
            symbol = Terminal(text)
        node = TextNode(symbol, -1, [], -1)
        return node

    def post_keypress(self, text):
        self.tool_data_is_dirty = True
        lines_before = len(self.lines)
        self.rescan_linebreaks(self.cursor.line)

        # repair indentations
        new_lines = len(self.lines) - lines_before
        node = self.cursor.node
        changed = False
        root = node.get_root()
        im = self.get_indentmanager(root)
        if im:
            if type(node.parent) is not MultiTextNode:
                for i in range(new_lines+1):
                    changed |= im.repair(node)
                    node = im.next_line(node)
            else:
                changed |= im.repair(node.parent)

        if text != "" and text[0] == "\r":
            self.cursor.line += 1
        return changed

    def copySelection(self):
        self.log_input("copySelection")
        result = self.get_nodes_from_selection()
        if not result:
            return None

        nodes, diff_start, diff_end = result
        if len(nodes) == 1:
            text = nodes[0].symbol.name[diff_start:diff_end]
            return text
        new_nodes = []
        for node in nodes:
            if not isinstance(node.symbol, IndentationTerminal):
                new_nodes.append(node)
        nodes = new_nodes

        text = []
        start = nodes.pop(0)
        end = nodes.pop(-1)

        text.append(start.symbol.name[diff_start:])
        for node in nodes:
            if node.lookup == "<return>":
                text.append("\n")
            else:
                text.append(node.symbol.name)
        text.append(end.symbol.name[:diff_end])
        return "".join(text)

    def pasteCompletion(self, text):
        self.log_input("pasteCompletion", repr(text))
        node = self.cursor.node
        if text.startswith(node.symbol.name):
            node.symbol.name = text
            self.cursor.pos = len(text)
        else:
            self.pasteText(text)

    def pasteText(self, text):
        self.log_input("pasteText", repr(str(text)))
        self.tool_data_is_dirty = True

        if self.hasSelection():
            self.deleteSelection()

        node = self.get_node_from_cursor()

        text = text.replace("\r\n","\r")
        text = text.replace("\n","\r")

        if self.cursor.inside():
            internal_position = self.cursor.pos
            node.insert(text, internal_position)
            self.cursor.pos += len(text)
        else:
            #XXX same code as in key_normal
            pos = 0
            if isinstance(node, BOS) or node.symbol.name == "\r" or isinstance(node.symbol, MagicTerminal):
                # insert new node: [bos] [newtext] [next node]
                old = node
                node = TextNode(Terminal(""))
                old.insert_after(node)
                self.cursor.pos = len(text)
            else:
                pos = len(node.symbol.name)
                self.cursor.pos += len(text)
            node.insert(text, pos)
            self.cursor.node = node

        self.relex(node)
        self.post_keypress("")
        self.reparse(node)

        self.cursor.fix()
        self.cursor.line += text.count("\r")
        self.changed = True

    def cutSelection(self):
        self.log_input("cutSelection")
        self.tool_data_is_dirty = True
        if self.hasSelection():
            text = self.copySelection()
            self.input_log.pop()
            self.deleteSelection()
            self.changed = True
            return text

    def deleteSelection(self):
        #XXX simple version: later we might want to modify the nodes directly
        self.tool_data_is_dirty = True
        nodes, diff_start, diff_end = self.get_nodes_from_selection()
        if nodes == []:
            return
        if isinstance(nodes[0], BOS):
            del nodes[0]
        repair_node = self.cursor.find_previous_visible(nodes[0])
        if len(nodes) == 1:
            s = nodes[0].symbol.name
            s = s[:diff_start] + s[diff_end:]
            nodes[0].symbol.name = s
            self.delete_if_empty(nodes[0])
            self.clean_empty_lbox(nodes[0])
        else:
            nodes[0].symbol.name = nodes[0].symbol.name[:diff_start]
            nodes[-1].symbol.name = nodes[-1].symbol.name[diff_end:]
            self.delete_if_empty(nodes[0])
            self.delete_if_empty(nodes[-1])
            self.clean_empty_lbox(nodes[0])
            self.clean_empty_lbox(nodes[-1])
        for node in nodes[1:-1]:
            if isinstance(node, BOS) or isinstance(node, EOS):
                continue
            node.parent.remove_child(node)
            self.clean_empty_lbox(node)
        while True: # in case first node was deleted
            if isinstance(repair_node.next_term, EOS):
                break
            if isinstance(repair_node.next_term.symbol, IndentationTerminal):
                repair_node = repair_node.next_term
                continue
            repair_node = repair_node.next_term
            break
        self.relex(repair_node)
        cur_start = min(self.selection_start, self.selection_end)
        cur_end = max(self.selection_start, self.selection_end)
        self.cursor.node = cur_start.node
        self.cursor.line = cur_start.line
        self.cursor.pos  = cur_start.pos
        self.selection_end = cur_start.copy()
        del self.lines[cur_start.line+1:cur_end.line+1]
        self.selection_start = self.cursor.copy()
        self.selection_end = self.cursor.copy()
        self.changed = True
        self.reparse(nodes[-1])

    def delete_if_empty(self, node):
        if node.symbol.name == "":
            node.parent.remove_child(node)

    def cursor_movement(self, key):
        if key.up:
            self.cursor.up()
        elif key.down:
            self.cursor.down()
        elif key.left:
            self.cursor.left()
        elif key.right:
            self.cursor.right()

    def cursor_reset(self):
        self.cursor.line = 0
        self.cursor.move_to_x(0)

    def fix_cursor_on_image(self):
        return
        node, _, x = self.get_node_from_cursor()
        if node.image and not node.plain_mode:
            self.cursor.x = x

    def rescan_linebreaks(self, y):
        """ Scan all nodes between this return node and the next lines return
        node. All other return nodes you find that are not the next lines
        return node are new and must be inserted into self.lines """

        current = self.lines[y].node
        try:
            next = self.lines[y+1].node
        except IndexError:
            next = self.get_eos()

        current = current.next_terminal()
        while current is not next:
            if current.symbol.name == "\r":
                y += 1
                self.lines.insert(y, Line(current))
            if isinstance(current.symbol, MagicTerminal):
                current = current.symbol.ast.children[0]
            elif isinstance(current, MultiTextNode):
                current = current.children[0]
            elif isinstance(current, EOS):
                root = current.get_root()
                lbox = root.get_magicterminal()
                if lbox:
                    current = lbox.next_terminal()
                else:
                    assert False
            else:
                current = current.next_terminal()

    def delete_linebreak(self, y, node):
        deleted = self.lines[y+1].node
        assert deleted is node
        del self.lines[y+1]

    # ============================ INDENTATIONS ============================= #

    def remove_indentation_nodes(self, node):
        if node is None:
            return
        while isinstance(node.symbol, IndentationTerminal):
            node.parent.remove_child(node)
            node = node.next_term
        return node


    # ============================ FILE OPERATIONS ============================= #

    def import_file(self, text):
        self.log_input("import_file", repr(text))
        TreeManager.version = 0
        self.version = 0
        # init
        self.cursor.node = self.get_bos()
        self.cursor.pos = 0
        self.cursor.line = 0
        for p in self.parsers[1:]:
            del p
        # convert linebreaks
        text = text.replace("\r\n","\r")
        text = text.replace("\n","\r")
        parser = self.parsers[0][0]
        lexer = self.parsers[0][1]
        # lex text into tokens
        bos = parser.previous_version.parent.children[0]
        new = TextNode(Terminal(text))
        bos.insert_after(new)
        lexer.relex_import(new, self.version+1)
        self.rescan_linebreaks(0)
        im = self.parsers[0][4]
        if im:
            im.repair_full()
        self.reparse(bos)
        self.undo_snapshot()
        self.changed = True
        return

    def fast_export(self, language_boxes, path, source=None):
        # fix languagebox pointers
        for root, language, whitespaces in language_boxes:
            try:
                lbox = root.magic_backpointer
                lbox.parent_lbox = lbox.get_root()
            except:
                bos = root.children[0]
                class X:
                    last_status = True
                self.parsers = [[X, None, language, None]]
        def x():
            return bos
        self.get_bos = x
        return self.export(path, source=source)

    def load_file(self, language_boxes, reparse=True):
        # setup language boxes
        TreeManager.version = 0
        for root, language, whitespaces in language_boxes:
            grammar = lang_dict[language]
            incparser, inclexer = self.get_parser_lexer_for_language(grammar, whitespaces)
            incparser.previous_version.parent = root
            try:
                lbox = root.magic_backpointer
                lbox.parent_lbox = lbox.get_root()
            except:
                pass # first language doesn't have parent

            self.add_parser(incparser, inclexer, grammar.name)

        self.rescan_linebreaks(0)

        self.savenextparse = True
        self.version = 1
        self.last_saved_version = 1
        self.full_reparse()
        self.save()
        TreeManager.version = 1
        self.changed = False

    def get_parser_lexer_for_language(self, grammar, whitespaces):
        if isinstance(grammar, Language):
            incparser = IncParser(grammar.grammar, 1, whitespaces)
            incparser.init_ast()
            inclexer = IncrementalLexer(grammar.priorities)
            return incparser, inclexer
        elif isinstance(grammar, EcoFile):
            incparser, inclexer = grammar.load()
            return incparser, inclexer
        else:
            print("Grammar Error: could not determine grammar type")
            return

    def export(self, path=None, run=False, profile=False, source=None, debug=False):
        for p, _, _, _ in self.parsers:
            if p.last_status == False:
                print("Cannot export a syntactically incorrect grammar")
                return False

        if str(path).endswith(".aterms"):
            return self.export_aterms(path)

        lang = self.parsers[0][2]
        if lang == "Python + Prolog":
            self.export_unipycation(path)
            return True
        elif lang == "HTML + Python + SQL":
            self.export_html_python_sql(path)
            return True
        elif lang == "PHP + Python" or lang == "PHP":
            return self.export_php_python(path, run, source=source)
        elif lang == "Python 2.7.5":
            return CPythonExporter(self).export(path=path, run=run, profile=profile, debug=debug)
        elif lang == "SimpleLanguage":
            return SimpleLanguageExporter(self).export(path=path, run=run)
        elif lang == "Ruby":
            return JRubyExporter(self).export(path=path, run=run, profile=profile)
        elif lang == "Ruby + SimpleLanguage":
            return JRubySimpleLanguageExporter(self).export(path=path, run=run, profile=profile)
        elif lang == "Ruby + JavaScript":
            return JRubyJavaScriptExporter(self).export(path=path, run=run, profile=profile)
        else:
            return self.export_as_text(path)

    def export_unipycation(self, path=None):
        import subprocess, sys
        import os
        import tempfile
        node = self.lines[0].node # first node
        output = []
        while True:
            if isinstance(node.symbol, IndentationTerminal):
                node = node.next_term
                continue
            if isinstance(node.symbol, MagicTerminal):
                output.append('"""')
                node = node.symbol.ast.children[0]
                node = node.next_term
                continue
            if isinstance(node, EOS):
                lbox = self.get_languagebox(node)
                if lbox:
                    output.append('"""')
                    node = lbox.next_term
                    continue
                else:
                    break
            output.append(node.symbol.name)
            node = node.next_term
        if path:
            with open(path, "w") as f:
                f.write("".join(output))
        else:
            f = tempfile.mkstemp()
            os.write(f[0],"".join(output))
            os.close(f[0])

            settings = QSettings("softdev", "Eco")
            unipath = str(settings.value("env_unipycation", "").toString())
            if unipath:
                return subprocess.Popen([unipath, f[1]], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, bufsize=0)
            else:
                sys.stderr.write("Unipycation executable not set")

    def export_html_python_sql(self, path):
        with open(path, "w") as f:
            f.write(HTMLPythonSQL.export(self.get_bos()))

    def export_php_python(self, path, run=False, source=None):
        import os
        if run:
            import tempfile
            import sys, subprocess
            d = tempfile.mkdtemp()
            if source:
                f = os.path.basename(source)
                f = (os.open(d + "/" + f, os.O_RDWR|os.O_CREAT), d + "/" + f)
            else:
                f = tempfile.mkstemp(dir=d)
            os.write(f[0], PHPPython.export(self.get_bos(), os.path.basename(source)))
            settings = QSettings("softdev", "Eco")
            prefixpath = str(settings.value("env_pypyprefix", "").toString())
            pyhyppath = str(settings.value("env_pyhyp", "").toString())
            if pyhyppath:
                if prefixpath:
                    env = os.environ.copy()
                    env["PYPY_PREFIX"] = prefixpath
                    return subprocess.Popen([pyhyppath, os.path.basename(f[1])], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, bufsize=0, env=env, cwd=os.path.dirname(f[1]))
                else:
                    sys.stderr.write("PYPY_PREFIX path not set")
            else:
                sys.stderr.write("PyHyp executable not set")
        else:
            with open(path, "w") as f:
                if source:
                    source = os.path.basename(str(source))
                text = PHPPython.export(self.get_bos(), source)
                f.write(text)
                return text

    def export_as_text(self, path=None):
        node = self.lines[0].node # first node
        text = []
        while True:
            node = node.next_term
            if isinstance(node.symbol, IndentationTerminal):
                continue
            if isinstance(node, EOS):
                lbnode = self.get_languagebox(node)
                if lbnode:
                    node = lbnode
                    continue
                else:
                    break
            if isinstance(node.symbol, MagicTerminal):
                node = node.symbol.ast.children[0]
                continue
            if node.symbol.name == "\r":
                text.append("\n")
            else:
                text.append(node.symbol.name)

        if path:
            with open(path, "w") as f:
                f.write("".join(text))
        return "".join(text)

    def export_aterms(self, path):
        start = self.get_bos().parent
        with open(path, "w") as f:
            text = ATerms.export(start)
            f.write(text)
            return text

    def relex(self, node):
        if node is None:
            return
        if type(node.parent) is MultiTextNode:
            return self.relex(node.parent)
        if isinstance(node, BOS) or isinstance(node, EOS):
            return
       #if isinstance(node.symbol, MagicTerminal):
       #    return
        root = node.get_root()
        lexer = self.get_lexer(root)
        try:
            return lexer.relex(node)
        except LexingError:
            # XXX do something here to let the user know a lexing error has
            # occured
            print "LEXING ERROR"
            return False

    def savestate(self):
        self.savenextparse = True
        if self.last_saved_version < self.version:
            self.reparse(self.get_bos(), True)

    def reparse(self, node, changed=True):
        if self.version < self.get_max_version():
            # we changed stuff after one or more undos
            # later versions are void -> delete
            self.clean_versions(self.version)
            self.last_saved_version = self.version
        if changed:
            root = node.get_root()
            parser = self.get_parser(root)
            parser.inc_parse()
        self.save_current_version()
        TreeManager.version = self.version

    def undo_snapshot(self):
        if self.undo_snapshots and self.undo_snapshots[-1] == self.version:
            # Snapshot already taken (this can happen in fuzzy tests where
            # undo_snapshot is called without any changes)
            return
        self.undo_snapshots.append(self.version)

    def save_current_version(self):
        self.log_input("save_current_version")
        self.version += 1
        self.save()
        TreeManager.version = self.version

    def full_reparse(self):
        for p in self.parsers:
            p[0].reparse()

    def apply_inputlog(self, inputlog):
        for l in inputlog.split("\n"):
            l = l.replace("\r", "\\r")
            if l.startswith("#"):
                continue
            try:
                eval(l) # expressions
            except SyntaxError:
                exec(l) # statements
