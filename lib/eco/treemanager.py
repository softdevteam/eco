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
from treelexer.lexer import LexingError
from incparser.astree import TextNode, BOS, EOS, MultiTextNode
from grammar_parser.gparser import Terminal, MagicTerminal, IndentationTerminal, Nonterminal
try:
    import __pypy__
except ImportError:
    from PyQt4.QtGui import QApplication
    from PyQt4.QtCore import QSettings
    from export.jruby import JRubyExporter
    from export.jruby_simple_language import JRubySimpleLanguageExporter
    from export.jruby_javascript import JRubyJavaScriptExporter
    from export.simple_language import SimpleLanguageExporter
    from utils import arrow_keys, KEY_UP, KEY_DOWN, KEY_LEFT, KEY_RIGHT
from grammars.grammars import lang_dict, Language, EcoFile
from indentmanager import IndentationManager
from export import HTMLPythonSQL, PHPPython, ATerms
from export.cpython import CPythonExporter

import math, os

def debug_trace():
  '''Set a tracepoint in the Python debugger that works with Qt'''
  from PyQt4.QtCore import pyqtRemoveInputHook

  # Or for Qt5
  #from PyQt5.QtCore import pyqtRemoveInputHook

  from pdb import set_trace
  pyqtRemoveInputHook()
  set_trace()

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
    """Representation of a source code line.

    Has a reference to the node at the beginning of that line and stores the
    lines width and height values.
    """
    def __init__(self, node, height=1):
        self.node = node        # this lines newline node
        self.height = height    # line height
        self.width = 0          # line width
        self.indent = 0         # line indentation
        self.ws = 0

    def __repr__(self):
        return "Line(%s, width=%s, height=%s)" % (self.node, self.width, self.height)

class Cursor(object):
    """Represents the text cursor in the sourcecode view.

    Stores the current node next to the cursor, the cursors offset within this
    node and the current line number. Can be manipulated by the user through key
    presses."""

    def __init__(self, node, pos, line, lines):
        self.node = node
        self.pos = pos
        self.line = line
        self.lines = lines
        self.last_x = 0
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

    def store_last_x(self):
        self.last_x = self.get_x()

    def restore_last_x(self, text=""):
        if text != "" and text[0] == "\r":
            self.line += 1
            self.move_to_x(len(text) - 1)
        else:
            self.move_to_x(self.last_x)

    def left(self):
        node = self.node
        if type(node.symbol) is MagicTerminal:
            node = node.symbol.ast.children[-1]
        if not self.is_visible(node):
            node = self.find_previous_visible(node)
        if node.symbol.name == "\r":
            self.line -= 1
        if isinstance(node, BOS):
            root = node.get_root()
            lbox = root.get_magicterminal()
            if lbox:
                node = lbox.previous_terminal()
            else:
                self.node = node
                return
        if not node is self.node:
            self.node = node
            self.pos = len(node.symbol.name)
        if self.pos > 1 and (not node.image or node.plain_mode):
            self.pos -= 1
        else:
            # if neighbouring node is BOS, stay in box
            if type(node.previous_terminal()) is BOS:
                self.node = node.previous_terminal()
                self.pos = 0
                return
            node = self.find_previous_visible(node)
            self.node = node
            self.pos = len(node.symbol.name)

    def right(self):
        node = self.node
        if not self.is_visible(node):
            node = self.find_next_visible(self.node)
            if type(node.symbol) is MagicTerminal:
                node = node.symbol.ast.children[0]
        if isinstance(node, EOS):
            return
        if not node is self.node:
            self.node = node
            self.pos = 0
            if node.symbol.name == "\r":
                self.line += 1
        if self.pos < len(node.symbol.name):
            self.pos += 1
        else:
            node = self.find_next_visible(node)
            if node.symbol.name == "\r":
                self.line += 1
            if isinstance(node, EOS):
                self.node = self.find_previous_visible(node)
                self.pos = len(self.node.symbol.name)
                return
            if type(node.symbol) is MagicTerminal:
                node = node.symbol.ast.children[0]
                node = self.find_next_visible(node)
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
        """Returns the next visible node in the parse tree.

        Skips over invisible nodes like IndentationTerminals and crosses
        languagebox boundaries.
        """
        if self.is_visible(node) or isinstance(node.symbol, MagicTerminal):
            node = node.next_terminal()
        while not self.is_visible(node):
            if isinstance(node, EOS):
                # Leave language box
                root = node.get_root()
                lbox = root.get_magicterminal()
                if lbox:
                    node = lbox.next_terminal()
                    continue
                else:
                    return node
            elif isinstance(node.symbol, MagicTerminal):
                # Enter language box
                node = node.symbol.ast.children[0]
                continue
            elif isinstance(node, MultiTextNode):
                node = node.children[0]
                continue
            node = node.next_terminal()
        return node

    def find_previous_visible(self, node, cross_lang=True):
        """Return the previous visible node in the parse tree."""
        if self.is_visible(node):
            if type(node.symbol) is MagicTerminal and cross_lang:
                node = node.symbol.ast.children[-1]
            else:
                node = node.previous_terminal()
        while True:
            if isinstance(node, BOS):
                if not cross_lang: # don't cross language border
                    return node
                # leave lbox
                root = node.get_root()
                lbox = root.get_magicterminal()
                if lbox:
                    node = lbox.previous_terminal()
                    continue
                else:
                    return node
            elif isinstance(node.symbol, MagicTerminal):
                node = node.symbol.ast.children[-1]
                continue
            elif isinstance(node, MultiTextNode):
                node = node.children[-1]
                continue
            if self.is_visible(node):
                break
            node = node.previous_terminal()
        return node

    def is_visible(self, node):
        """Checks whether a given node is visible in the source code view."""
        if isinstance(node.symbol, IndentationTerminal):
            return False
        if isinstance(node, BOS):
            return False
        if isinstance(node, EOS):
            return False
        if isinstance(node.symbol, MultiTextNode):
            return False
        return True

    def up(self):
        """Move the cursor a line up."""
        if self.line > 0:
            x = self.get_x()
            self.line -= 1
            self.move_to_x(x)

    def down(self):
        """Move the cursor a line down."""
        if self.line < len(self.lines) - 1:
            x = self.get_x()
            self.line += 1
            self.move_to_x(x)

    def home(self):
        """Jump to the beginning of the current line."""
        self.node = self.lines[self.line].node
        self.pos = len(self.node.symbol.name)

    def end(self):
        """Jump to the end of the current line."""
        if self.line < len(self.lines)-1:
            self.node = self.find_previous_visible(self.lines[self.line+1].node)
        else:
            while not isinstance(self.node, EOS):
                self.node = self.node.next_terminal()
            self.node = self.find_previous_visible(self.node)
        self.pos = len(self.node.symbol.name)

    def move_to_x(self, x):
        """Jump to the x-th character/column position in the current line."""
        node = self.lines[self.line].node
        while x > 0:
            newnode = self.find_next_visible(node)
            if newnode is node:
                self.node = node
                self.pos = len(node.symbol.name)
                return
            node = newnode
            if type(node.symbol) is MagicTerminal:
                node = node.symbol.ast.children[0]
                continue
            if node.image and not node.plain_mode:
                x -= self.get_nodesize_in_chars(node).w
            else:
                x -= len(node.symbol.name)
            if node.symbol.name == "\r":
                self.node = self.find_previous_visible(node)
                self.pos = len(self.node.symbol.name)
                return
            if isinstance(node, EOS):
                root = node.get_root()
                lbox = root.get_magicterminal()
                if lbox:
                    node = lbox
                    continue
                else:
                    self.node = self.find_previous_visible(node)
                    self.pos = len(self.node.symbol.name)
                    return
        self.pos = len(node.symbol.name) + x
        self.node = node

    def get_x(self):
        """Get the current character/column position of the cursor."""
        if self.node.symbol.name == "\r":
            return 0
        if isinstance(self.node, BOS):
            if not self.node.get_root().get_magicterminal():
                return 0

        if self.node.image and not self.node.plain_mode:
            x = self.get_nodesize_in_chars(self.node).w
        else:
            x = self.pos
        node = self.find_previous_visible(self.node)
        while node.symbol.name != "\r":
            if isinstance(node, BOS):
                if not node.get_root().get_magicterminal():
                    break
            if node.image and not node.plain_mode:
                x += self.get_nodesize_in_chars(node).w
            else:
                x += len(node.symbol.name)
            node = self.find_previous_visible(node)
        return x

    def move_to_node(self, node, after=False):
        tmp = node
        while tmp.symbol.name != "\r" and not isinstance(tmp, BOS):
            tmp = self.find_previous_visible(tmp)
        line = self.get_line_from_node(tmp)
        self.line = line
        self.node = node
        if after:
            self.pos = len(node.symbol.name)
        else:
            self.node = self.find_previous_visible(node)
            self.pos = len(self.node.symbol.name)

    def get_line_from_node(self, node):
        i = 0
        for l in self.lines:
            if l.node is node:
                return i
            i += 1

    def get_nodesize_in_chars(self, node):
        """Calculate the size in characters of a non-textual node."""
        gfont = QApplication.instance().gfont
        if node.image:
            w = math.ceil(node.image.width() * 1.0 / gfont.fontwt)
            h = math.ceil(node.image.height() * 1.0 / gfont.fontht)
            return NodeSize(w, h)
        else:
            return NodeSize(len(node.symbol.name), 1)

    def inside(self):
        """Check if the cursor position is strictly within a node and not
        between two nodes."""
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
        self.version = self.global_version = 1
        self.reference_version = 0
        TreeManager.version = 1
        self.last_saved_version = 1
        self.savenextparse = False
        self.saved_lines = {}
        self.saved_parsers = {}
        self.undo_snapshots = []
        self.min_version = 1

        self.tool_data_is_dirty = False
        self.autolboxdetector = None
        self.option_autolbox_find = True
        self.option_autolbox_insert = False

        self.skipautolbox = False

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
        """Checks if there is any selection in the source code view."""
        return self.selection_start != self.selection_end

    def get_bos(self):
        return self.parsers[0][0].previous_version.parent.children[0]

    def get_eos(self):
        return self.parsers[0][0].previous_version.parent.children[-1]

    def get_mainparser(self):
        """Return the parser of the root language."""
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
        parser.reference_version = 0
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
            if os.path.exists(lang.nb_file):
                from astanalyser import AstAnalyser
                return AstAnalyser(lang.nb_file)
            else:
                print("Namebinding file '%s' not found." % (lang.nb_file))


    def get_selected_languagebox(self):
        return self.get_languagebox(self.cursor.node)

    def get_languagebox(self, node):
        root = node.get_root()
        lbox = root.get_magicterminal()
        return lbox

    def is_typeerror(self, node):
        for p in self.parsers:
            if p[3] and p[3].has_error(node):
                return True
        return False

    def is_syntaxerror(self, node):
        for p in self.parsers:
            if p[0]:
                for n in p[0].error_nodes:
                    if n is node:
                        return True
        return False

    def get_all_syntaxerrors(self):
        l = []
        for p in self.parsers:
            if p[0]:
                l.extend(p[0].error_nodes)
        return l

    def get_error(self, node):
        if self.is_syntaxerror(node):
            return "Syntax error on token '%s' (%s)." % (node.symbol.name, node.lookup)

        for p in self.parsers:
            # check for namebinding error
            if p[3]:
                error = p[3].get_error(node)
                if error != "":
                    return error
        return ""

    def has_error_presentation(self, node):
        for p in self.parsers:
            if p[0]:
                for n, pres in p[0].error_pres:
                    if n is node:
                        return True
        return False

    def get_error_presentation(self, node):
        for p in self.parsers:
            if p[0]:
                for n, pres in p[0].error_pres:
                      if n is node:
                          return "'%s' was changed to '%s'" % (pres, node.symbol.name)
        return None

    def analyse(self):
        # for now only do cross-scope analysing for certain grammars
        crossscope = ["PHP + Python", "Java + Python"]
        lang = self.parsers[0][2]
        parser = self.parsers[0][0]
        analyser = self.parsers[0][3]

        if not analyser:
            return False

        if lang in crossscope:
            analyser.analyse(parser.previous_version.parent, self.parsers)
            return

        # analyse all parsers individually
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

        if type(cur_end.node.symbol) is MagicTerminal:
            cur_end = cur_end.copy()
            cur_end.node = cur_end.node.symbol.ast.children[-1]
            cur_end.pos = 0
            cur_end.jump_left()
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
        if type(node) is not EOS:
            nodes.append(end)

        return (nodes, diff_start, diff_end)

    def is_logical_line(self, y):
        newline_node = self.lines[y].node
        node = newline_node.next_terminal()
        while True:
            if isinstance(node, EOS):
                return False
            if node.lookup == "<return>": # reached next line
                return False
            if node.lookup == "<ws>":
                node = node.next_terminal()
                continue
            if  isinstance(node.symbol, IndentationTerminal):
                node = node.next_terminal()
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
        node = self.cursor.node.next_terminal()
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
            node = node.next_terminal()
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
            if node is parser.error_nodes[0]:
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
        for u in range(undo_amount):
            self.version += 1
            self.recover_version("redo", self.version - 1)
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
        if not self.undo_snapshots or self.version == self.min_version:
            # min_version is needed so we can't undo importing/loading files
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
        for u in range(undo_amount):
            self.version -= 1
            self.recover_version("undo", self.version + 1)
            self.cursor.load(self.version, self.lines)

    def recover_version(self, direction, _from):
        self.load_lines()
        self.load_parsers()
        for l in self.parsers:
            parser = l[0]
            parser.load_status(self.version)
            root = parser.previous_version.parent
            if direction == "undo":
                self.undo(root)
            elif direction == "redo":
                self.redo(root, _from)

    def undo(self, node):
        if not node.log:
            # Node was never integrated during parsing and thus hasn't been
            # saved. Continue with its children. This could be also solved by
            # having nodes version themselves as soon as their attributes
            # changes. Requires rethinking the versioning system.
            for c in node.children:
                self.undo(c)
            return
        if node.version <= self.version and not node.has_unsaved_changes():
            # node is already at this or an even earlier version and has no
            # unsaved changes
            return
        for c in node.children:
            self.undo(c)
        if not node.is_new(node.version):
            if node.autobox and len(node.autobox) == 1:
                # block this node for autolboxes in the future
                node.autobox = False
            node.load(self.version)
            for c in node.children:
                self.undo(c)

    def redo(self, node, _from):
        node.load(self.version)
        if node.version > _from:
            for c in node.children:
                self.redo(c, _from)

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

    def save(self, postparse=False):
        """Recursive version of save used to calculate textlength on the fly"""
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
            self.save_and_textlen_rec(root, postparse)

    def save_and_textlen_rec(self, node, postparse):
        if node.has_changes() or node.new:
            if postparse:
                node.changed = False
                node.nested_changes = False
            for c in node.children:
                self.save_and_textlen_rec(c, postparse)
            node.calc_textlength()
            node.save(self.version)
            # Make sure that all nodes are always marked as non-existent before
            # a new parse. This way only parsed subtrees are marked as exists,
            # and we avoid retaining not yet parsed subtrees. However, not yet
            # marked subtrees shouldn't end up in the retain part in the first
            # place. But due to Wagner using current_version instead of
            # previous_version in pass1 this can happen.
            node.exists = False

    def key_home(self, shift=False):
        self.log_input("key_home", str(shift))
        self.unselect()
        lbox = self.get_languagebox(self.cursor.node)
        self.cursor.home()
        self.update_tbd(lbox)
        if shift:
            self.selection_end = self.cursor.copy()

    def key_end(self, shift=False):
        self.log_input("key_end", str(shift))
        self.unselect()
        lbox = self.get_languagebox(self.cursor.node)
        self.cursor.end()
        self.update_tbd(lbox)
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

        if text == "\n":
            text = "\r"

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
        self.fix_cursor_on_image()
        temp = self.cursor.node
        self.cursor.node = edited_node
        need_reparse |= self.post_keypress(text)
        self.cursor.node = temp
        self.cursor.restore_last_x(text)
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
            return

        need_reparse = False

        if self.cursor.inside(): # cursor inside a node
            internal_position = self.cursor.pos
            self.last_delchar = node.backspace(internal_position)
            repairnode = node
        else: # between two nodes
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
                if node.ismultichild():
                    repairnode = node.parent
                else:
                    repairnode = self.cursor.find_previous_visible(node, cross_lang=False)
                    repairnode.mark_changed()

                if not self.clean_empty_lbox(node):
                    # normal node is empty -> remove it from AST
                    node.parent.remove_child(node)
                    need_reparse = True
                if node.ismultichild():
                    node.parent.update_children()

        need_reparse |= self.relex(repairnode)
        need_reparse |= self.post_keypress("")
        self.cursor.restore_last_x()
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

        lbox = self.get_languagebox(self.cursor.node)

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

        self.update_tbd(lbox)

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

    def select_from_to(self, _from, _to, split):
        self.cursor.move_to_node(_from)
        self.selection_start = self.cursor.copy()
        self.cursor.move_to_node(_to, after=True)
        self.selection_end = self.cursor.copy()
        self.selection_end.pos += split

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
            self.relex(node2)
        self.edit_rightnode = True # writes next char into magic ast
        self.cursor.node = newnode.symbol.ast.children[0]
        self.cursor.pos = 0
        self.reparse(newnode)
        self.changed = True
        return newnode

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
        incparser.setup_autolbox(language.name, inclexer)
        root = incparser.previous_version.parent
        root.magic_backpointer = lbox
        self.add_parser(incparser, inclexer, language.name)

        lbox.symbol.parser = root
        lbox.symbol.ast = root
        lbox.plain_mode = True
        return lbox

    def surround_with_languagebox(self, language, auto=False):
        self.log_input("surround_with_languagebox", repr(language.name))
        #XXX if partly selected node, need to split it
        nodes, _, _ = self.get_nodes_from_selection()
        self.edit_rightnode = False
        # cut text
        text = self.copySelection()
        self.deleteSelection(reparse=False)
        lbox = self.add_languagebox(language)
        self.pasteText(text)
        lbox.tbd = auto
        self.input_log.pop()
        self.input_log.pop()
        self.input_log.pop()
        return

    def remove_selected_lbox(self):
        root = self.cursor.node.get_root()
        if hasattr(root, "magic_backpointer"):
            lbox = root.magic_backpointer
            if lbox:
                self.remove_languagebox(lbox)

    def remove_languagebox(self, lbox):
        if lbox.deleted:
            # Language box was already removed by an earlier error
            return
        parent = lbox.parent
        root = lbox.symbol.ast
        bos = root.children[0]
        eos = root.children[-1]
        left = lbox.prev_term

        # move all nodes from lbox to the outside
        node = bos.next_term
        top = []
        while node is not eos:
            if type(node.symbol) is not IndentationTerminal:
                top.append(node)
            node = node.next_term

        for n in reversed(top):
            lbox.insert_after(n)

        # remove language box and parser
        lbox.remove(True)
        self.delete_parser(root)

        # relex
        for t in top:
            #XXX add method to relex a range, e.g. relex(start, end)
            self.relex(t)
        self.relex(left)
        self.cursor.restore_last_x()
        # reparse
        self.reparse(top[0], skipautolbox = True)

    def toggle_lock_languagebox(self):
        root = self.cursor.node.get_root()
        if hasattr(root, "magic_backpointer"):
            lbox = root.magic_backpointer
            if lbox:
                lbox.tbd = not lbox.tbd

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

    def expand_languagebox(self, lbox, newend, manual=False):
        last_x = self.cursor.get_x() # Remember cursor position

        # Remove nodes from outer box and copy their content
        l = []
        n = lbox.next_term
        while n is not newend:
            l.append(n.symbol.name)
            n.remove()
            n = n.next_term
        l.append(newend.symbol.name)
        newend.remove()
        self.reparse(lbox, True, skipautolbox=True)

        # Insert copied content at the end of the lbox
        eos = lbox.symbol.ast.children[-1]
        prev = eos.prev_term
        prev.insert_after(TextNode(Terminal("".join(l))))

        if manual:
            lbox.autobox = None
            lbox.tbd = False

        # Relex and reparse changes
        self.relex(prev.next_term)
        self.post_keypress("")
        self.cursor.last_x = last_x
        self.cursor.restore_last_x()
        self.reparse(lbox.symbol.ast.children[0], True)

    def shrink_languagebox(self, lbox, newend):
        last_x = self.cursor.get_x() # Remember cursor position

        # Remove nodes from language box and copy their content
        l = []
        n = newend
        while type(n) is not EOS:
            if isinstance(n, MultiTextNode):
                for c in list(n.children):
                    l.append(c.symbol.name)
                    c.remove()
                    c.deleted = True
            else:
                l.append(n.symbol.name)
            n.remove()
            n = n.next_term

        for i in reversed(range(len(self.lines))):
            if self.lines[i].node.deleted:
                del self.lines[i]

        self.skipautolbox = True
        self.reparse(lbox.symbol.ast.children[0], True)

        # Insert copied content after lbox
        lbox.insert_after(TextNode(Terminal("".join(l))))

        # Relex and reparse changes
        self.relex(lbox.next_term)
        self.post_keypress("")
        self.cursor.last_x = last_x
        self.cursor.restore_last_x()
        self.reparse(lbox, True, skipautolbox=True)
        self.skipautolbox = False

    def update_tbd(self, lbox):
        if lbox is None:
            return
        newlbox = self.get_languagebox(self.cursor.node)
        if lbox is not newlbox:
            lbox.tbd = False

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
        changed = self.repair_indentations()

        return changed

    def repair_indentations(self):
        node = self.cursor.node
        root = node.get_root()
        im = self.get_indentmanager(root)
        changed = False
        if im:
            # traverse parsetree for changes
            # for every node that has changes, find it's newline and run
            # im.repair if it hasn't already been repaired
            node = root.children[1] # skip BOS
            while type(node) is not EOS:
                if node.deleted:
                    node = self.next_node(node)
                    continue
                if node.has_changes() and isinstance(node.symbol, Nonterminal) and node.children:
                    node = node.children[0]
                    continue
                # XXX This code currently repairs any line that has changes.
                # However, we only need to repair lines where the changed node
                # is a newline or the first terminal (excluding indentation
                # nodes and whitespace) after a newline
                if node.has_changes() and type(node.symbol) is Terminal:
                    changed |= im.repair(node)
                node = self.next_node(node)
        return changed

    def next_node(self, node):
        while(node.right_sibling() is None):
            node = node.parent
        return node.right_sibling()


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
        # while tabs are not supported, replace them with spaces
        text = text.replace("\t", "    ")

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
        self.cursor.line += text.count("\r")
        self.cursor.restore_last_x()
        self.reparse(node)

        self.changed = True #XXX needed?

    def select_nodes(self, start, end):
        self.cursor.move_to_node(start)
        self.selection_start = self.cursor.copy()
        self.cursor.move_to_node(end, True)
        self.selection_end = self.cursor.copy()

    def cutSelection(self):
        self.log_input("cutSelection")
        self.tool_data_is_dirty = True
        if self.hasSelection():
            text = self.copySelection()
            self.input_log.pop()
            self.deleteSelection()
            self.changed = True
            return text

    def deleteSelection(self, reparse=True):
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
        else:
            nodes[0].symbol.name = nodes[0].symbol.name[:diff_start]
            nodes[-1].symbol.name = nodes[-1].symbol.name[diff_end:]
            self.delete_if_empty(nodes[0])
            self.delete_if_empty(nodes[-1])
        for node in nodes[1:-1]:
            if isinstance(node, BOS) or isinstance(node, EOS):
                continue
            node.parent.remove_child(node)
            # Remove MultiNode if all children have been deleted
            if node.ismultichild():
                if node.parent.children == []:
                    node.parent.remove()
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
        # are we still inside an empty lbox
        if isinstance(self.cursor.node, BOS):
            magic = self.cursor.node.get_root().get_magicterminal()
            if magic and magic.deleted:
                self.cursor.node = self.cursor.find_previous_visible(self.cursor.node)
                self.cursor.pos = len(self.cursor.node.symbol.name)
        self.selection_start = self.cursor.copy()
        self.selection_end = self.cursor.copy()
        self.changed = True
        self.repair_indentations()
        repairnode = nodes[-1]
        if repairnode.deleted:
            repairnode = self.cursor.find_previous_visible(repairnode, cross_lang=True)
        if reparse:
            self.reparse(repairnode)

    def delete_if_empty(self, node):
        if node.symbol.name == "":
            self.clean_empty_lbox(node)
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
        self.version = self.global_version = 0
        text = text.replace("\r\n","\r")
        text = text.replace("\n","\r")
        text = text.replace("\t","    ")
        parser = self.parsers[0][0]
        lexer = self.parsers[0][1]
        # lex text into tokens
        bos = parser.previous_version.parent.children[0]
        new = TextNode(Terminal(text))
        bos.insert_after(new)
        new.changed = True
        self.relex(new)
        self.rescan_linebreaks(0)
        im = self.parsers[0][4]
        if im:
            im.repair_full()
        self.reparse(bos)
        self.undo_snapshot()
        self.changed = True
        self.reparse(bos)
        self.undo_snapshots = [self.version]
        self.min_version = self.version
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
                self.parsers = [[X, None, language, None, None]]
        def x():
            return bos
        self.get_bos = x
        self.lines.append(X())
        self.lines[0].node = bos
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
        self.version = self.global_version = 1
        self.last_saved_version = 1
        self.reference_version = 1
        self.full_reparse() # needed to recreate AST nodes
        self.save(True)
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
        for p, _, _, _, _ in self.parsers:
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
                raise ExecutionError("Unipycation executable not set")

    def export_html_python_sql(self, path):
        with open(path, "w") as f:
            f.write(HTMLPythonSQL.export(self.get_bos()))

    def export_php_python(self, path, run=False, source=None):
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
                    raise ExecutionError("PYPY_PREFIX path not set")
            else:
                raise ExecutionError("PyHyp executable not set")
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
        self.cursor.store_last_x()
        if node is None:
            return False
        if isinstance(node, BOS) or isinstance(node, EOS):
            return False
        if isinstance(node.symbol, MagicTerminal):
            return False
        try:
            return self.relex_node(node)
        except LexingError:
            #XXX show LexingError message somwhere in the UI
            return True

    def relex_node(self, node):
        # XXX start from top, only relex former lexingerror nodes
        # if there are changes within their lookahead
        root = node.get_root()
        lexer = self.get_lexer(root)
        return lexer.relex(node)

    def reparse(self, node, changed=True, skipautolbox=False):
        if self.version < self.global_version:
            # we changed stuff after one or more undos
            # later versions are void -> delete
            for l in self.parsers:
                root = l[0].previous_version.parent
                for v in reversed(range(self.version+1, self.global_version+1)):
                    self.delete_version(v, root)
                    try:
                        self.undo_snapshots.remove(v)
                    except ValueError:
                        pass
            self.global_version = self.version
        if changed:
            self.save_current_version() # save current changes
            root = node.get_root()
            parser = self.get_parser(root)
            self.previous_version = self.version
            parser.prev_version = self.version
            parser.reference_version = self.reference_version
            parser.option_autolbox_find = self.option_autolbox_find
            parser.inc_parse()
            parser.top_down_reuse()
            self.save_current_version(postparse=True) # save post parse tree
            if parser.last_status == True:
                self.reference_version = self.version
        else:
            # save changes without reparse (e.g. when a value has changed but
            # the type remains the same)
            self.save_current_version(postparse=True)
        TreeManager.version = self.version

        # Now check for auto language boxes
        if self.skipautolbox or skipautolbox or self.option_autolbox_insert is False:
            return

        parsers = list(self.parsers) # copy to avoid processing newly added parsers
        for temp in parsers:
            # remove language boxes that are not valid anymore
            p = temp[0]
            lbox = p.previous_version.parent.get_magicterminal()
            if lbox and lbox.tbd and not lbox.deleted:
                if lbox.tbd == "remove" or self.lbox_autoremove_test(lbox, p.last_status):
                    self.remove_languagebox(lbox)
                else:
                    # try to expand language boxes
                    if not self.lbox_expand_test(lbox):
                        self.lbox_shrink_test(lbox)

            # apply language boxes if there is only one choice
            for n in p.error_nodes:
                if not n.deleted and n.autobox and len(n.autobox) == 1:
                    s, e, l, split = n.autobox[0]
                    self.undo_snapshot()
                    ctemp = self.cursor.get_x()
                    ltemp = self.cursor.line
                    self.select_from_to(s, e, split)
                    self.skipautolbox = True # block automatic lboxes during automatic insertion
                    self.surround_with_languagebox(lang_dict[l], True)
                    self.cursor.line = ltemp
                    self.cursor.move_to_x(ctemp)
                    self.undo_snapshot()
                    self.skipautolbox = False

    def lbox_expand_test(self, lbox):
        """Checks if the language box can be expanded by moving following
        tokens from the outer language into the language box."""
        from autolboxdetector import IncrementalRecognizer
        outer_root = lbox.get_root()
        outer_lang = outer_root.name
        p = self.get_parser(lbox.symbol.ast)
        l = self.get_lexer(lbox.symbol.ast)
        langname = self.get_language(lbox.symbol.ast)
        eos = lbox.symbol.ast.children[-1]
        r = IncrementalRecognizer(p.syntaxtable, l.lexer, langname, None)
        r.mode_limit_tokens_new = lang_dict[outer_lang].auto_limit_new
        r.preparse(lbox.symbol.ast, eos.prev_term) # Preparse lbox contents...
        r.parse_single(eos.prev_term) # ... up to (but excluding) EOS
        r.orig_parse(lbox.next_term) # Parse tokens following lbox
        # Check that we can continue parsing the outer language for each
        # extension option
        op = self.get_parser(outer_root)
        ol = self.get_lexer(outer_root)
        r2 = IncrementalRecognizer(op.syntaxtable, ol.lexer, outer_lang, None)
        r2.mode_limit_tokens_new = False
        r2.preparse(outer_root, lbox)
        r2.parse_after(lbox)
        filtered = []
        for e, _, _ in r.possible_ends:
            if e.lookup == "<ws>" or e.lookup == "<return>":
                continue
            tmp = r2.state[:]
            if r2.parse_after(e.next_term):
                filtered.append(e)
            r2.state = tmp
        # If there's only one expansion option apply it, otherwise show the
        # options in the editor
        if len(filtered) == 1:
            self.expand_languagebox(lbox, filtered[0])
            return True
        elif len(filtered) > 1:
            lbox.autobox = [(lbox, f, None) for f in filtered]
        return False

    def lbox_shrink_test(self, lbox):
        """Checks if an invalid language box can be shrunken by moving the
        error (and following tokens) within the box into the outer language."""
        from autolboxdetector import IncrementalRecognizer
        outer_lang = lbox.get_root().name
        p = self.get_parser(lbox.symbol.ast)
        l = self.get_lexer(lbox.symbol.ast)
        langname = self.get_language(lbox.symbol.ast)
        eos = lbox.symbol.ast.children[-1]
        if len(p.error_nodes) == 0:
            return False
        error = p.error_nodes[0]
        r = IncrementalRecognizer(p.syntaxtable, l.lexer, langname, None)
        r.mode_limit_tokens_new = lang_dict[outer_lang].auto_limit_new
        r.preparse(lbox.symbol.ast, error) # Preparse lbox contents up to the error
        if r.is_finished(): # if code up to error is valid
            root = lbox.get_root()
            p = self.get_parser(root) # outer parser
            l = self.get_lexer(root) # outer lexer
            r = IncrementalRecognizer(p.syntaxtable, l.lexer, outer_lang, None)
            r.mode_limit_tokens_new = lang_dict[outer_lang].auto_limit_new
            r.preparse(root, lbox)
            r.temp_parse(r.state, lbox.symbol)
            if r.parse_lex_single(error):
                self.shrink_languagebox(lbox, error)
                return True
        return False

    def lbox_autoremove_test(self, lbox, status):
        """An automatically inserted languagebox can be automatically removed if
        one of the following is true (if in doubt always prioritise the outer language):
        1) The languagebox contents are valid in the outside language's context (i.e.
        the contents can be parsed as well as the nodes following the old box)
        2) The languagebox is invalid and its contents can be parsed in the
        outside language (note: the context doesn't have to be valid)"""
        from autolboxdetector import IncrementalRecognizer
        outer_root = lbox.get_root()
        outer_lang = outer_root.name
        outer_parser, outer_lexer = lang_dict[outer_lang].load() # get preloaded one
        r = IncrementalRecognizer(outer_parser.syntaxtable, outer_lexer.lexer, outer_lang, None)
        r.preparse(outer_root, lbox)
        result =  r.parse(lbox.symbol.ast.children[0].next_term, lbox.next_term, status)
        return result

    def delete_version(self, version, node):
        if ("parent", version) in node.log:
            children = node.log["children", version]
            node.delete_version(version)
            for c in children:
                self.delete_version(version, c)

    def undo_snapshot(self):
        if self.undo_snapshots and self.undo_snapshots[-1] == self.version:
            # Snapshot already taken (this can happen in fuzzy tests where
            # undo_snapshot is called without any changes)
            return
        self.undo_snapshots.append(self.version)

    def save_current_version(self, postparse=False):
        self.log_input("save_current_version")
        self.global_version += 1
        self.version = self.global_version
        self.save(postparse=postparse)
        TreeManager.version = self.version

    def full_reparse(self):
        for p in self.parsers:
            p[0].prev_version = self.version
            p[0].reference_version = self.reference_version
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

    def get_langdef_from_string(self, lang):
        return lang_dict[lang]

class ExecutionError(Exception):
  pass
