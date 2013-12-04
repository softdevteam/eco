from incparser.incparser import IncParser
from inclexer.inclexer import IncrementalLexer
from incparser.astree import TextNode, BOS, EOS, ImageNode, FinishSymbol
from grammar_parser.gparser import Terminal, MagicTerminal, IndentationTerminal, Nonterminal
from PyQt4 import QtCore #XXX get rid of all QT references later

from grammars.grammars import lang_dict

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

    def __repr__(self):
        return "Line(%s, width=%s, height=%s)" % (self.node, self.width, self.height)

class Cursor(object):
    def __init__(self, node, pos, line):
        self.node = node
        self.pos = pos
        self.line = line

    def copy(self):
        return Cursor(self.node, self.pos, self.line)

    def fix(self):
        while self.pos > len(self.node.symbol.name):
            self.pos -= len(self.node.symbol.name)
            self.node = self.node.next_term

    def left(self):
        if isinstance(self.node, BOS):
            root = self.node.get_root()
            lbox = root.get_magicterminal()
            if lbox:
                node = self.prev(lbox)
                self.pos = len(node.symbol.name)
                self.node = node
            else:
                return

        if self.pos > 1 and (not self.node.image or self.node.plain_mode):
            self.pos -= 1
        else:
            if self.node.symbol.name == "\r":
                return
            node = self.prev(self.node)
            self.node = node
            self.pos = len(self.node.symbol.name)
            if isinstance(self.node.next_term, BOS):
                self.pos -= 1

    def right(self):
        if isinstance(self.node.symbol, MagicTerminal):
            self.node = self.next(self.node)
            self.pos = 1
            return
        if self.pos < len(self.node.symbol.name):
            self.pos += 1
        else:
            node = self.next(self.node)
            if node is self.node or node.symbol.name == "\r":
                return
            self.node = node
            if node.image and not node.plain_mode:
                self.pos = len(node.symbol.name)
            else:
                self.pos = 1

    def next(self, startnode): # next visisble node
        node = startnode.next_term
        while isinstance(node.symbol, IndentationTerminal):
            node = node.next_term

        if isinstance(node.symbol, MagicTerminal):
            node = self.next(node.symbol.ast.children[0])

        if isinstance(node, EOS):
            root = node.get_root()
            lbox = root.get_magicterminal()
            if lbox:
                node = self.next(lbox)
            else:
                return startnode

        # we can have indentation inside and outisde of a language box
        while isinstance(node.symbol, IndentationTerminal):
            node = node.next_term

        return node

    def prev(self, node): # previous visible node

        node = node.prev_term

        while isinstance(node.symbol, IndentationTerminal):
            node = node.prev_term

        if isinstance(node, BOS):
            root = node.get_root()
            lbox = root.get_magicterminal()
            if lbox:
                node = self.prev(lbox)

        if isinstance(node.symbol, MagicTerminal):
            node = self.prev(node.symbol.ast.children[-1])

        while isinstance(node.symbol, IndentationTerminal):
            node = node.prev_term

        return node

    def up(self, lines):
        if self.line > 0:
            x = self.get_x()
            self.line -= 1
            self.move_to_x(x, lines)

    def down(self, lines):
        if self.line < len(lines) - 1:
            x = self.get_x()
            self.line += 1
            self.move_to_x(x, lines)

    def move_to_x(self, x, lines):
        node = lines[self.line].node
        while x > 0:
            newnode = self.next(node)
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
                self.node = self.prev(node)
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
        node = self.prev(self.node)
        while node.symbol.name != "\r" and not isinstance(node, BOS):
            if node.image and not node.plain_mode:
                x += self.get_nodesize_in_chars(node).w
            else:
                x += len(node.symbol.name)
            node = self.prev(node)
        return x

    def get_nodesize_in_chars(self, node):
        if node.image:
            w = math.ceil(node.image.width() * 1.0 / fontmanager.fontwt)
            h = math.ceil(node.image.height() * 1.0 / fontmanager.fontht)
            return NodeSize(w, h)
        else:
            return NodeSize(len(node.symbol.name), 1)

    def inside(self):
        return self.pos > 0 and self.pos < len(self.node.symbol.name)

    def isend(self):
        return self.pos == len(self.node.symbol.name)

    def __eq__(self, other):
        if isinstance(other, Cursor):
            return self.node is other.node and self.pos == other.pos
        return False

    def __ne__(self, other):
        return not self == other

    def __repr__(self):
        return "Cursor(%s, %s)" % (self.node, self.pos)

class TreeManager(object):
    def __init__(self):
        self.lines = []             # storage for line objects
        self.mainroot = None        # root node (main language)
        #self.cursor = Cursor(0,0)
        #self.selection_start = Cursor(0,0)
        #self.selection_end = Cursor(0,0)
        self.parsers = []           # stores all currently used parsers
        self.edit_rightnode = False # changes which node to select when inbetween two nodes

    def set_font(self, fontm):
        #XXX obsolete when cursor is relative to nodes
        self.fontm = fontm
        self.fontht = self.fontm.height() + 3
        self.fontwt = self.fontm.width(" ")
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
        for parser, lexer, lang in self.parsers:
            if parser.previous_version.parent is root:
                return parser

    def get_lexer(self, root):
        for parser, lexer, lang in self.parsers:
            if parser.previous_version.parent is root:
                return lexer

    def get_language(self, root):
        for parser, lexer, lang in self.parsers:
            if parser.previous_version.parent is root:
                return lang

    def add_parser(self, parser, lexer, language):
        self.parsers.append((parser, lexer, language))
        parser.inc_parse()
        if len(self.parsers) == 1:
            self.lines.append(Line(parser.previous_version.parent.children[0]))
            self.mainroot = parser.previous_version.parent
            self.cursor = Cursor(self.mainroot.children[0], 0, 0)
            self.selection_start = self.cursor.copy()
            self.selection_end = self.cursor.copy()

    def get_languagebox(self, node):
        root = node.get_root()
        lbox = root.get_magicterminal()
        return lbox

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

        temp = self.cursor

        self.cursor = cur_start
        start_node, start_inbetween, start_x = self.get_node_from_cursor()
        diff_start = 0
        if start_inbetween:
            diff_start = len(start_node.symbol.name) - (start_x - self.cursor.x)
            include_start = True
        else:
            include_start = False

        self.cursor = cur_end
        end_node, end_inbetween, end_x = self.get_node_from_cursor()
        diff_end = len(end_node.symbol.name)

        if end_inbetween:
            diff_end = len(end_node.symbol.name) - (end_x - self.cursor.x)

        if not start_inbetween:
            start = start_node.next_term

        self.cursor = temp

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

    # ============================ MODIFICATIONS ============================= #

    def key_home(self):
        node = self.cursor.node
        while not (node.symbol.name == "\r" or isinstance(node, BOS)):
            node = node.prev_term
        self.cursor.node = node
        self.cursor.pos = len(node.symbol.name)

    def key_end(self):
        node = self.cursor.node.next_term
        while not (node.symbol.name == "\r" or isinstance(node, EOS)):
            node = node.next_term
        self.cursor.node = node.prev_term
        self.cursor.pos = len(self.cursor.node.symbol.name)

    def key_normal(self, text):
        indentation = 0

        if self.hasSelection():
            self.deleteSelection()

        if text == "\r":
            indentation = self.get_indentation(self.cursor.line)
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
            if isinstance(node, BOS) or node.symbol.name == "\r" or isinstance(node.symbol, MagicTerminal):
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
            else:
                pos = self.cursor.pos#len(node.symbol.name)
            node.insert(text, pos)
            self.cursor.node = node
        self.cursor.pos += len(text)

        self.relex(node)
        self.cursor.fix()
        self.fix_cursor_on_image()
        self.post_keypress(text)
        self.reparse(node)
        return indentation

    def key_backspace(self):
        node = self.get_selected_node()
        if node is self.mainroot.children[0]:
            return
        if node.image is not None and not node.plain_mode:
            return
        if self.cursor.node.symbol.name == "\r":
            #self.cursor.up()
            #self.key
            self.cursor.node = self.cursor.prev(self.cursor.node)
            self.cursor.line -= 1
        else:
            self.cursor.left()
        self.key_delete()

    def key_delete(self):
        node = self.get_node_from_cursor()

        if self.hasSelection():
            self.deleteSelection()
            return

        if self.cursor.inside(): # cursor inside a node
            internal_position = self.cursor.pos
            self.last_delchar = node.backspace(internal_position)
            self.relex(node)
            repairnode = node
        else: # between two nodes
            node = node.next_terminal() # delete should edit the node to the right from the selected node
            # if lbox is selected, select first node in lbox
            if isinstance(node, EOS):
                lbox = self.get_languagebox(node)
                if lbox:
                    node = lbox.next_term
                else:
                    return
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
                repairnode = node.prev_term

                root = node.get_root()
                magic = root.get_magicterminal()
                next_node = node.next_terminal()
                previous_node = node.previous_terminal()
                # XXX add function to tree to ast: is_empty
                if magic and isinstance(next_node, EOS) and isinstance(previous_node, BOS):
                    # language box is empty -> delete it and all references
                    self.cursor.node = self.cursor.prev(magic)
                    self.cursor.pos = len(self.cursor.node.symbol.name)
                    repairnode = self.cursor.node
                    magic.parent.remove_child(magic)
                    self.delete_parser(root)
                else:
                    # normal node is empty -> remove it from AST
                    node.parent.remove_child(node)

            if repairnode is not None and not isinstance(repairnode, BOS):
                self.relex(repairnode)

        self.post_keypress("")
        self.reparse(repairnode)

    def key_shift(self):
        self.selection_start = self.cursor.copy()
        self.selection_end = self.cursor.copy()

    def key_escape(self):
        node = self.get_selected_node()
        if node.plain_mode:
            node.plain_mode = False

    def key_cursors(self, key, mod_shift):
        self.edit_rightnode = False
        self.cursor_movement(key)
        if mod_shift:
            self.selection_end = self.cursor.copy()
        else:
            self.selection_start = self.cursor.copy()
            self.selection_end = self.cursor.copy()

    def add_languagebox(self, language):
        node = self.get_node_from_cursor()
        newnode = self.create_languagebox(language)
        if not self.cursor.inside():
            node.insert_after(newnode)
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

    def leave_languagebox(self):
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
        parser = IncParser(language.grammar, 1, True)
        parser.init_ast(lbox)
        lexer = IncrementalLexer(language.priorities, language.name)
        root = parser.previous_version.parent
        root.magic_backpointer = lbox
        self.add_parser(parser, lexer, language.name)

        lbox.symbol.parser = root
        lbox.symbol.ast = root
        return lbox

    def surround_with_languagebox(self, language):
        nodes, _, _ = self.get_nodes_from_selection()
        appendnode = nodes[0].prev_term
        self.edit_rightnode = False
        # cut text
        text = self.copySelection()
        self.deleteSelection()
        # create language box
        lbox = self.create_languagebox(language)
        # insert text
        newnode = TextNode(Terminal(text))
        lbox.symbol.ast.children[0].insert_after(newnode)
        self.relex(newnode)
        appendnode.insert_after(lbox)

    def create_node(self, text, lbox=False):
        if lbox:
            symbol = MagicTerminal(text)
        else:
            symbol = Terminal(text)
        node = TextNode(symbol, -1, [], -1)
        return node

    def post_keypress(self, text):
        lines_before = len(self.lines)
        self.rescan_linebreaks(self.cursor.line)
        new_lines = len(self.lines) - lines_before
        for i in range(new_lines+1):
            self.rescan_indentations(self.cursor.line+i)

        if text != "" and text[0] == "\r":
            self.cursor.line += 1

    def copySelection(self):
        nodes, diff_start, diff_end = self.get_nodes_from_selection()
        if len(nodes) == 1:
            text = nodes[0].symbol.name[diff_start:diff_end]
            QApplication.clipboard().setText(text)
            return
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
            text.append(node.symbol.name)
        text.append(end.symbol.name[:diff_end])
        return "".join(text)

    def pasteText(self, text):
        node, inside, x = self.get_node_from_cursor()

        if self.hasSelection():
            self.deleteSelection()

        text = text.replace("\r\n","\r")
        text = text.replace("\n","\r")

        if inside:
            internal_position = len(node.symbol.name) - (x - self.cursor.x)
            node.insert(text, internal_position)
        else:
            #XXX same code as in key_normal
            pos = 0
            if isinstance(node, BOS) or node.symbol.name == "\r" or isinstance(node.symbol, MagicTerminal):
                # insert new node: [bos] [newtext] [next node]
                old = node
                node = TextNode(Terminal(""))
                old.insert_after(node)
            else:
                pos = len(node.symbol.name)
            node.insert(text, pos)

        self.cursor.x += len(text)
        self.relex(node)

    def cutSelection(self):
        if self.hasSelection():
            self.copySelection()
            self.deleteSelection()

    def deleteSelection(self):
        #XXX simple version: later we might want to modify the nodes directly
        nodes, diff_start, diff_end = self.get_nodes_from_selection()
        repair_node = nodes[0].prev_term
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
            node.parent.remove_child(node)
        repair_node = repair_node.next_term # in case first node was deleted
        self.relex(repair_node)
        cur_start = min(self.selection_start, self.selection_end)
        cur_end = max(self.selection_start, self.selection_end)
        self.cursor = cur_start.copy()
        self.selection_end = cur_start.copy()
        self.changed_line = cur_start.y
        del self.lines[cur_start.y+1:cur_end.y+1]
        self.selection_start = self.cursor.copy()
        self.selection_end = self.cursor.copy()

    def delete_if_empty(self, node):
        if node.symbol.name == "":
            node.parent.remove_child(node)

    def cursor_movement(self, key):
        cur = self.cursor

        if key == QtCore.Qt.Key_Up:
            self.cursor.up(self.lines)
        elif key == QtCore.Qt.Key_Down:
            self.cursor.down(self.lines)
        elif key == QtCore.Qt.Key_Left:
            self.cursor.left()
        elif key == QtCore.Qt.Key_Right:
            self.cursor.right()
        #self.fix_cursor_on_image() #XXX refactor (obsolete after refactoring cursor)

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

        current = current.next_term
        while current is not next:
            if current.symbol.name == "\r":
                y += 1
                self.lines.insert(y, Line(current))
            if isinstance(current.symbol, MagicTerminal):
                current = current.symbol.ast.children[0]
            elif isinstance(current, EOS):
                root = current.get_root()
                lbox = root.get_magicterminal()
                if lbox:
                    current = lbox.next_term
            else:
                current = current.next_term

    def delete_linebreak(self, y, node):
        current = self.lines[y].node
        deleted = self.lines[y+1].node
        assert deleted is node
        del self.lines[y+1]

    # ============================ INDENTATIONS ============================= #

    def update_indentation_backwards(self, y):
        # find out lines indentation by scanning previous lines
        root = self.lines[y].node.get_root()
        ws = self.get_indentation(y)
        dy = y
        while dy > 0:
            dy = dy - 1
            if not self.is_logical_line(dy):
                continue
            other_root = self.lines[dy].node.get_root()
            if not self.is_same_language(root, other_root):
                continue
            prev_ws = self.get_indentation(dy)
            if ws == prev_ws:
                self.lines[y].indent = self.lines[dy].indent
                return
            if ws > prev_ws:
                self.lines[y].indent = self.lines[dy].indent + 1
                return

    def rescan_indentations(self, y):
        if not self.is_logical_line(y):
            return

        before = self.lines[y].indent
        self.update_indentation_backwards(y)
        after = self.lines[y].indent
        #if after != before:
        self.repair_indentation(y)

        search_threshold = min(before, after)

        current_indent = self.lines[y].indent
        current_ws = self.get_indentation(y)
        for i in range(y+1,len(self.lines)):
            ws = self.get_indentation(i)
            if ws is None:
                continue
            old = self.lines[i].indent
            if ws > current_ws:
                self.lines[i].indent = current_indent + 1
            if ws == current_ws:
                self.lines[i].indent = current_indent
            if ws < current_ws:
                self.update_indentation_backwards(i)

            self.repair_indentation(i)

            if self.lines[i].indent < search_threshold:
                # repair everything up to the line that has smaller indentation
                # than the changed line
                break
            current_ws = ws
            current_indent = self.lines[i].indent
        return

    def repair_indentation(self, y):
        if y == 0:
            self.lines[y].indent = 0
            return

        newline = self.lines[y].node

        # check if language is indentation based
        root = newline.get_root()
        lexer = self.get_lexer(root)
        if not lexer.is_indentation_based():
            return

        new_indent_nodes = []

        # check if line is logical (not comment/whitespace) (exception: last line)
        if self.is_logical_line(y):
            # XXX move indentation change check up here using indent values

            this_whitespace = self.get_indentation(y)
            dy = y - 1
            root = self.lines[y].node.get_root()
            other = self.lines[dy].node.get_root()
            while not self.is_logical_line(dy) or not self.is_same_language(root, other):
                dy -= 1
                other = self.lines[dy].node.get_root()
            prev_whitespace = self.get_indentation(dy)

            if prev_whitespace == this_whitespace:
                self.lines[y].indent = self.lines[dy].indent
                new_indent_nodes.append(TextNode(IndentationTerminal("NEWLINE")))
            elif prev_whitespace < this_whitespace:
                self.lines[y].indent = self.lines[dy].indent + 1
                new_indent_nodes.append(TextNode(IndentationTerminal("INDENT")))
                new_indent_nodes.append(TextNode(IndentationTerminal("NEWLINE")))
            elif prev_whitespace > this_whitespace:
                this_indent = self.find_indentation(y)
                if this_indent is None:
                    new_indent_nodes.append(TextNode(IndentationTerminal("UNBALANCED")))
                else:
                    self.lines[y].indent = this_indent
                    prev_indent = self.lines[dy].indent
                    indent_diff = prev_indent - this_indent
                    for i in range(indent_diff):
                        new_indent_nodes.append(TextNode(IndentationTerminal("DEDENT")))
                    new_indent_nodes.append(TextNode(IndentationTerminal("NEWLINE")))

        # check if indentation nodes have changed
        # if not keep old ones to avoid unnecessary reparsing
        as_before = self.indentation_nodes_changed(y, new_indent_nodes)
        if not as_before:

            # remove old indentation nodes
            node = self.remove_indentation_nodes(newline.next_term)
            for node in new_indent_nodes:
                newline.insert_after(node)

        # generate last lines dedent
        if y == len(self.lines) - 1:
            eos = newline.get_root().children[-1]
            node = eos.prev_term
            while isinstance(node.symbol, IndentationTerminal):
                node.parent.remove_child(node)
                node = node.prev_term
            this_indent = self.lines[y].indent
            for i in range(this_indent):
                node.insert_after(TextNode(IndentationTerminal("DEDENT")))
            node.insert_after(TextNode(IndentationTerminal("NEWLINE")))

    def indentation_nodes_changed(self, y, nodes):
        previous_nodes = []
        newline = self.lines[y].node
        node = newline.next_term
        while isinstance(node.symbol, IndentationTerminal):
            previous_nodes.append(node)
            node = node.next_term

        previous_nodes.reverse()
        if len(previous_nodes) != len(nodes):
            return False
        for i in range(len(nodes)):
            if nodes[i].symbol != previous_nodes[i].symbol:
                return False
        return True

    def find_indentation(self, y):
        # indentation level
        this_whitespace = self.get_indentation(y)
        dy = y
        while dy > 0:
            dy = dy - 1
            prev_whitespace = self.get_indentation(dy)
            if prev_whitespace is None:
                continue
            if prev_whitespace == this_whitespace:
                return self.lines[dy].indent
            if prev_whitespace < this_whitespace:
                return None
        return None

    def remove_indentation_nodes(self, node):
        if node is None:
            return
        while isinstance(node.symbol, IndentationTerminal):
            node.parent.remove_child(node)
            node = node.next_term
        return node


    # ============================ FILE OPERATIONS ============================= #

    def import_file(self, text):
        # init
        self.cursor = Cursor(self.get_bos(),0,0)
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
        root = new.get_root()
        lexer.relex_import(new)
        self.rescan_linebreaks(0)
        for y in range(len(self.lines)):
            self.repair_indentation(y)
        return

    def load_file(self, language_boxes):

        # setup language boxes
        for root, language, whitespaces in language_boxes:
            grammar = lang_dict[language]
            incparser = IncParser(grammar.grammar, 1, whitespaces)
            incparser.init_ast()
            incparser.previous_version.parent = root
            inclexer = IncrementalLexer(grammar.priorities)
            self.add_parser(incparser, inclexer, language)

        self.rescan_linebreaks(0)
        for i in range(len(self.lines)):
            self.rescan_indentations(i)

    def export_unipycation(self):
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
        f = tempfile.mkstemp()
        os.write(f[0],"".join(output))
        os.close(f[0])
        if os.environ.has_key("UNIPYCATION"):
            subprocess.Popen([os.path.join(os.environ["UNIPYCATION"], "pypy/goal/pypy-c"), f[1]])
        else:
            sys.stderr.write("UNIPYCATION environment not set")

    def relex(self, node):
        root = node.get_root()
        lexer = self.get_lexer(root)
        lexer.relex(node)
        return

    def reparse(self, node):
        root = node.get_root()
        parser = self.get_parser(root)
        parser.inc_parse()
