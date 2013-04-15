from __future__ import print_function

import sys
sys.path.append("../")
sys.path.append("../lr-parser/")

from PyQt4 import QtCore
from PyQt4.QtCore import *
from PyQt4 import QtGui
from PyQt4.QtGui import *


from gui import Ui_MainWindow

from plexer import PriorityLexer
from incparser import IncParser
from viewer import Viewer

from gparser import Terminal, MagicTerminal
from astree import TextNode, BOS, EOS

from languages import languages

from token_lexer import TokenLexer

from time import time

grammar = """
    E ::= T
        | E "+" T
    T ::= P
        | T "*" P
    P ::= "INT"
"""

priorities = """
    "[0-9]+":INT
    "[+]":+
    "[*]":*
"""


grammar = """
    S ::= "a" | "abc" | "bc"
"""

priorities = """
    "abc":abc
    "bc":bc
    "a":a
"""

class NodeEditor(QFrame):

    # ========================== init stuff ========================== #

    def __init__(self, parent=None):
        QtGui.QWidget.__init__(self, parent)

        self.font = QtGui.QFont('Courier', 9)
        self.fontm = QtGui.QFontMetrics(self.font)
        self.fontht = self.fontm.height() + 3
        self.fontwt = self.fontm.width(" ")
        self.cursor = [0,0]

        # make cursor blink
        self.show_cursor = 1
        self.ctimer = QtCore.QTimer()
        #QtCore.QObject.connect(self.ctimer, QtCore.SIGNAL("timeout()"), self.blink)
        self.ctimer.start(500)

        self.position = 0
        self.selection_start = Cursor(0,0)
        self.selection_end = Cursor(0,0)

        self.node_map = {}
        self.max_cols = []
        self.indentations = {}

        self.parsers = {}
        self.lexers = {}
        self.priorities = {}
        self.parser_langs = {}

        self.edit_rightnode = False
        self.indentation = True

        self.last_delchar = ""
        self.lbox_nesting = 0
        self.nesting_colors = {0: QColor(255,0,0), 1: QColor(0,200,0), 2:QColor(0,0,255)}

    def reset(self):
        self.indentations = {}
        self.max_cols = []
        self.node_map = {}
        self.cursor = Cursor(0,0)
        self.update()

    def set_lrparser(self, lrp, lang_name):
        self.parsers = {}
        self.lexers = {}
        self.priorities = {}
        self.lrp = lrp
        self.ast = lrp.previous_version
        self.parsers[lrp.previous_version.parent] = self.lrp
        self.lexers[lrp.previous_version.parent] = self.getTL()
        self.priorities[lrp.previous_version.parent] = self.getPL()
        self.parser_langs[lrp.previous_version.parent] = lang_name

    def set_sublanguage(self, language):
        self.sublanguage = language

    # ========================== GUI related stuff ========================== #

    def blink(self):
        if self.show_cursor:
            self.show_cursor = 0
        else:
            self.show_cursor = 1
        self.update()

    def paintEvent(self, event):
        QtGui.QFrame.paintEvent(self, event)
        paint = QtGui.QPainter()
        paint.begin(self)
        paint.setFont(self.font)

        y = 0
        x = 0

        bos = self.ast.parent.children[0]
        self.indentations = {}
        self.node_map.clear()
        self.node_map[(x,y)] = bos
        self.max_cols = []

        x, y = self.paintAST(paint, bos, x, y)
        self.max_cols.append(x) # last line

        if self.hasFocus() and self.show_cursor:
            #paint.drawRect(3 + self.cursor[0] * self.fontwt, 2 + self.cursor[1] * self.fontht, self.fontwt-1, self.fontht)
            paint.drawRect(3 + self.cursor.x * self.fontwt, 5 + self.cursor.y * self.fontht, 0, self.fontht - 3)

        self.paintSelection(paint)
        paint.end()

        width = (max(self.max_cols)+1) * self.fontwt
        height = len(self.max_cols) * self.fontht + 3
        geom = self.geometry()
        geom.setWidth(width)
        geom.setHeight(height)
        self.setMinimumSize(QSize(width, height))
        if self.hasFocus():
            self.getWindow().ui.scrollArea.ensureVisible (self.cursor.x * self.fontwt, self.cursor.y * self.fontht, self.fontwt, self.fontht+3 )

    def paintAST(self, paint, bos, x, y):
        node = bos.next_terminal()
        parser = self.parsers[bos.parent]
        while node and not isinstance(node, EOS):
            if node.symbol.name in ["\n", "\r"]:
                self.max_cols.append(x)
                y += 1
                x = 0
                self.node_map[(x,y)] = node
            else:
                if node.lookup == "<ws>" and x == 0:
                    self.indentations[y] = len(node.symbol.name)
                if isinstance(node.symbol, MagicTerminal):
                    #paint.drawText(QtCore.QPointF(3 + x*self.fontwt, self.fontht + y*self.fontht), "<")
                    #x += 1
                    lbox_start = Cursor(x,y)
                    self.lbox_nesting += 1
                    x, y = self.paintAST(paint, node.symbol.parser.previous_version.get_bos(), x, y)
                    lbox_end = Cursor(x,y)
                    self.lbox_nesting -= 1
                    if self.getWindow().ui.cbShowLangBoxes.isChecked():
                        self.paintLanguageBox(paint, lbox_start, lbox_end)
                    elif lbox_start < self.cursor < lbox_end or (self.cursor == lbox_end and not self.edit_rightnode):
                        self.paintLanguageBox(paint, lbox_start, lbox_end)
                    elif lbox_start < self.cursor < lbox_end or (self.cursor == lbox_start and self.edit_rightnode):
                        self.paintLanguageBox(paint, lbox_start, lbox_end)
                    #paint.drawText(QtCore.QPointF(3 + x*self.fontwt, self.fontht + y*self.fontht), ">")
                    #x += 1
                    #self.node_map[(x,y)] = node
                else:
                    paint.drawText(QtCore.QPointF(3 + x*self.fontwt, self.fontht + y*self.fontht), node.symbol.name)
                    if node is parser.error_node:
                        paint.setPen(QColor(255,0,0))
                        x1 = 3 + x*self.fontwt
                        x2 = x1 + len(node.symbol.name)*self.fontwt
                        y12 = self.fontht + y * self.fontht + 1
                        i = 0
                        while x1 < x2:
                            paint.drawLine(x1, y12 + (i%2), x1+2, y12 + (i%2))
                            x1 += 2
                            i += 1
                        paint.setPen(QColor(0,0,0))
                    x += len(node.symbol.name)
                    self.node_map[(x,y)] = node

            node = node.next_terminal()
        return x,y

    def paintLanguageBox(self, paint, start, end):
        paint.setPen(self.nesting_colors[self.lbox_nesting % 3])
        if start.y == end.y:
            width = end.x - start. x
            paint.drawRect(3 + start.x * self.fontwt, 3 + self.lbox_nesting + start.y * self.fontht, width * self.fontwt, self.fontht - 2*(self.lbox_nesting))
        else:
            # paint start to line end
            width = self.max_cols[start.y] - start.x
            paint.drawRect(3 + start.x * self.fontwt, 3 + self.lbox_nesting + start.y * self.fontht, width * self.fontwt, self.fontht - 2*(self.lbox_nesting))

            # paint lines in between
            for y in range(start.y+1, end.y):
                width = self.max_cols[y]
                paint.drawRect(3 + 0 * self.fontwt,   3 + self.lbox_nesting + y       * self.fontht, width * self.fontwt, self.fontht - 2*(self.lbox_nesting))

            # paint line start to end
            width = end.x
            paint.drawRect(3 + 0 * self.fontwt,       3 + self.lbox_nesting + end.y   * self.fontht, width * self.fontwt, self.fontht - 2*(self.lbox_nesting))
        paint.setPen(QColor(0,0,0,255))

    def paintSelection(self, paint):
        start = min(self.selection_start, self.selection_end)
        end = max(self.selection_start, self.selection_end)
        if start.y == end.y:
            width = end.x - start.x
            paint.fillRect(3 + start.x * self.fontwt, 2+start.y * self.fontht, width * self.fontwt, self.fontht, QColor(0,0,255,100))
        else:
            # paint start to line end
            width = self.max_cols[start.y] - start.x
            paint.fillRect(3 + start.x * self.fontwt, 2+start.y * self.fontht, width * self.fontwt, self.fontht, QColor(0,0,255,100))

            # paint lines in between
            for y in range(start.y+1, end.y):
                width = self.max_cols[y]
                paint.fillRect(3 + 0 * self.fontwt, 2+y * self.fontht, width * self.fontwt, self.fontht, QColor(0,0,255,100))

            # paint line start to end
            width = end.x
            paint.fillRect(3 + 0 * self.fontwt, 2+end.y * self.fontht, width * self.fontwt, self.fontht, QColor(0,0,255,100))

    def recalculate_positions(self): # without painting
        y = 0
        x = 0

        bos = self.ast.parent.children[0]
        self.node_map.clear()
        self.node_map[(x,y)] = bos
        self.max_cols = []

        x, y = self.recalculate_positions_rec(bos, x, y)
        self.max_cols.append(x) # last line

    def recalculate_positions_rec(self, bos, x, y):
        node = bos.next_terminal()
        while node and not isinstance(node, EOS):
            if node.symbol.name in ["\n", "\r"]:
                self.max_cols.append(x)
                y += 1
                x = 0
                self.node_map[(x,y)] = node
            else:
                if isinstance(node.symbol, MagicTerminal):
                    #x+=1
                    bos = node.symbol.parser.previous_version.get_bos()
                    x, y = self.recalculate_positions_rec(bos, x, y)
                    #x+=1
                    #self.node_map[(x,y)] = node
                else:
                    x += len(node.symbol.name)
                    self.node_map[(x,y)] = node

            node = node.next_terminal()

        return x, y


    def get_indentation(self, y):
        try:
            return self.indentations[y]
        except KeyError:
            return 0

    def get_nodes_at_position(self):
        print("==================== Get nodes at pos ====================== ")
        print("Position:", self.cursor)
        # Look up node in position map (if there is no direct match, i.e. inbetween node, try to find end of node)
        node_at_pos = None
        x = self.cursor.x
        y = self.cursor.y
        inbetween = False
        while not node_at_pos and x <= self.max_cols[y]:
            try:
                node_at_pos = self.node_map[(x, y)]
                break
            except KeyError:
                x += 1
                inbetween = True
        #print(self.node_map)
        print("node at pos:", node_at_pos)
        selected_nodes = [node_at_pos, node_at_pos.next_terminal()]
        print("Selected Nodes:", selected_nodes)
        #if isinstance(selected_nodes[1].symbol, MagicTerminal) and self.edit_rightnode:
        if self.edit_rightnode:
            print("edit right", selected_nodes)
            if isinstance(selected_nodes[1], EOS):
                root = selected_nodes[1].get_root()
                magic = root.get_magicterminal()
                if magic:
                    selected_nodes = [magic, magic.next_terminal()]
            if isinstance(selected_nodes[1].symbol, MagicTerminal):
                bos = selected_nodes[1].symbol.parser.previous_version.get_bos()
                selected_nodes = [bos, bos.next_terminal()]

        print("Final selected nodes", selected_nodes)
        print("==================== END (get_nodes_at_pos) ====================== ")
        return (selected_nodes, inbetween, x)

    def get_nodes_from_selection(self):
        cur_start = min(self.selection_start, self.selection_end)
        cur_end = max(self.selection_start, self.selection_end)
        start = None
        include_start = False
        x = cur_start.x
        y = cur_start.y
        while not start and x <= self.max_cols[y]:
            try:
                start = self.node_map[(x, y)]
                break
            except KeyError:
                include_start = True
                x += 1

        if include_start:
            diff_start = len(start.symbol.name) - (x - cur_start.x)
        else:
            diff_start = 0

        end = None
        x = cur_end.x
        y = cur_end.y
        while not end and x <= self.max_cols[y]:
            try:
                end = self.node_map[(x, y)]
                break
            except KeyError:
                x += 1

        diff_end = len(end.symbol.name) - (x - cur_end.x)

        nodes = []
        node = start
        if include_start:
            nodes.append(start)
        while node is not end:
            node = node.next_terminal()
            # extend search into magic tree
            if isinstance(node.symbol, MagicTerminal):
                node = node.symbol.parser.previous_version.get_bos()
                continue
            # extend search outside magic tree
            if isinstance(node, EOS):
                root = node.get_root()
                magic = root.get_magicterminal()
                if magic:
                    node = magic
                    continue
            nodes.append(node)

        return (nodes, diff_start, diff_end)

    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton:
            self.cursor = self.coordinate_to_cursor(e.x(), e.y())
            self.selection_start = self.cursor.copy()
            self.selection_end = self.cursor.copy()

            selected_nodes, _, _ = self.get_nodes_at_position()
            self.getWindow().btReparse(selected_nodes)

            root = selected_nodes[0].get_root()
            lrp = self.parsers[root]
            self.getWindow().showLookahead(lrp)
            self.update()

    def coordinate_to_cursor(self, x, y):
        cursor_x = x / self.fontwt
        cursor_y = y / self.fontht

        result = Cursor(0,0)
        if cursor_y < 0:
            result.y = 0
        elif cursor_y < len(self.max_cols):
            result.y = cursor_y
        else:
            result.y = len(self.max_cols) - 1

        if cursor_x < 0:
            result.x = 0
        elif cursor_x <= self.max_cols[result.y]:
            result.x = cursor_x
        else:
            result.x = self.max_cols[result.y]
        return result

    def mouseMoveEvent(self, e):
        # apparaently this is only called when a mouse button is clicked while
        # the mouse is moving
        self.selection_end = self.coordinate_to_cursor(e.x(), e.y())
        self.get_nodes_from_selection()
        self.update()

    def focusNextPrevChild(self, b):
        # don't switch to next widget on TAB
        return False

    def keyPressEvent(self, e):
        print("====================== KEYPRESS (>>%s<<) ============================" % (repr(e.text()),))
        print("first get_nodes_at_pos")
        selected_nodes, inbetween, x = self.get_nodes_at_position()

        text = e.text()

        if e.key() == Qt.Key_Tab:
            text = "    "
        if e.key() in [Qt.Key_Up, Qt.Key_Down, Qt.Key_Left, Qt.Key_Right]:
            self.edit_rightnode = False
            self.cursor_movement(e.key())
            self.update()
            selected_nodes, _, _ = self.get_nodes_at_position()
            self.getWindow().showAst(selected_nodes)
            return
        elif e.key() in [Qt.Key_End, Qt.Key_Home]:
            if e.key() == Qt.Key_Home:
                self.cursor.x = 0
            else:
                self.cursor.x = self.max_cols[self.cursor.y]
        elif text != "":
            if e.key() == Qt.Key_C and e.modifiers() == Qt.ControlModifier:
                self.copySelection()
                return
            elif e.key() == Qt.Key_V and e.modifiers() == Qt.ControlModifier:
                self.pasteSelection()
                return
            elif e.key() == Qt.Key_X and e.modifiers() == Qt.ControlModifier:
                if self.hasSelection():
                    self.copySelection()
                    self.deleteSelection()
                return
            self.edit_rightnode = False
            if e.key() in [Qt.Key_Delete, Qt.Key_Backspace]:
                if self.hasSelection():
                    self.deleteSelection()
                    return
                if e.key() == Qt.Key_Backspace:
                    if self.cursor.x > 0:
                        self.cursor.x -= 1
                    else:
                        # if at beginning of line: move to previous line
                        if self.cursor.y > 0:
                            self.cursor.y -= 1
                            self.cursor.x = self.max_cols[self.cursor.y]
                if inbetween:   # inside node
                    internal_position = len(selected_nodes[0].symbol.name) - (x - self.cursor.x)
                    self.last_delchar = selected_nodes[0].backspace(internal_position)
                    repairnode = selected_nodes[0]
                else: # between two nodes
                    if e.key() == Qt.Key_Delete: # delete
                        if isinstance(selected_nodes[1].symbol, MagicTerminal) or isinstance(selected_nodes[1], EOS):
                            self.edit_rightnode = True
                            selected_nodes, _, _ = self.get_nodes_at_position()
                            self.edit_rightnode = False
                        node = selected_nodes[1]
                        other = selected_nodes[0]
                        self.last_delchar = node.backspace(0)
                    else: # backspace
                        node = selected_nodes[0]
                        other = selected_nodes[1]
                        self.last_delchar = node.backspace(-1)
                    if node.symbol.name == "" and not isinstance(node, BOS): # if node is empty, delete it and repair previous/next node
                        if isinstance(other, BOS):
                            repairnode = node.next_terminal()
                        elif isinstance(other, EOS):
                            repairnode = node.previous_terminal()
                        else:
                            repairnode = other
                        # check if magic terminal is empty
                        root = node.get_root()
                        magic = root.get_magicterminal()
                        next_node = node.next_terminal()
                        previous_node = node.previous_terminal()
                        if magic and isinstance(next_node, EOS) and isinstance(previous_node, BOS):
                            magic.parent.remove_child(magic)
                            del self.parsers[root]
                            del self.lexers[root]
                            del self.priorities[root]
                        else:
                            node.parent.remove_child(node)

                    else:
                        repairnode = node
            else:
                if self.hasSelection():
                    self.deleteSelection()
                if e.key() == Qt.Key_Space and e.modifiers() == Qt.ControlModifier:
                    self.showSubgrammarMenu()
                    if self.sublanguage:
                        newnode = self.add_magic()
                        self.edit_rightnode = True # writes next char into magic ast
                elif e.key() == Qt.Key_Space and e.modifiers() == Qt.ControlModifier | Qt.ShiftModifier:
                    self.edit_rightnode = True # writes next char into magic ast
                    self.update()
                    return
                else:
                    if e.key() == Qt.Key_Return:
                        if self.indentation:
                            indentation = self.get_indentation(self.cursor.y)
                            text += " " * indentation
                        else:
                            indentation = 0
                    newnode = self.create_node(str(text))
                if inbetween:
                    print("BETWEEN")
                    node = selected_nodes[0]
                    # split, insert new node, repair
                    internal_position = len(node.symbol.name) - (x - self.cursor.x)
                    node2 = newnode
                    node3 = self.create_node(node.symbol.name[internal_position:])
                    node.symbol.name = node.symbol.name[:internal_position]
                    print("node1", node)
                    print("node2", node2)
                    print("node3", node3)
                    self.add_node(node, node2)
                    self.add_node(node2, node3)
                    self.repair(node2)
                    if not node3.deleted:
                        self.repair(node3)
                    if not node2.deleted:
                        self.repair(node2)
                    #node.parent.insert_after_node(node, node2)
                    #node.parent.insert_after_node(node2, node3)
                    repairnode = None
                else:
                    # insert node, repair
                    node = selected_nodes[0]
                    self.add_node(node, newnode)
                    #node.parent.insert_after_node(node, newnode)
                    repairnode = newnode
                if e.key() == Qt.Key_Space and e.modifiers() == Qt.ControlModifier:
                    pass # do nothing
                elif e.key() == Qt.Key_Return:
                    self.cursor.x = indentation
                    self.cursor.y += 1
                elif e.key() == Qt.Key_Tab:
                    self.cursor.x += 4
                else:
                    self.cursor.x += 1
            self.repair(repairnode)

        self.recalculate_positions() # XXX ensures that positions are up to date before next keypress is called
        print("second get_nodes_at_pos")
        selected_nodes, _, _ = self.get_nodes_at_position()
        self.getWindow().btReparse(selected_nodes)

        root = selected_nodes[0].get_root()
        lrp = self.parsers[root]
        self.getWindow().showLookahead(lrp)
        self.update()

    def add_magic(self):
        # Create magic token
        magictoken = self.create_node("<%s>" % self.sublanguage.name, magic=True)

        # Create parser, priorities and lexer
        parser = IncParser(self.sublanguage.grammar, 1, True)
        parser.init_ast()
        root = parser.previous_version.parent
        root.magic_backpointer = magictoken
        pl = PriorityLexer(self.sublanguage.priorities)
        tl = TokenLexer(pl.rules)
        self.parsers[root] = parser
        self.lexers[root] = tl
        self.priorities[root] = pl
        self.parser_langs[root] = self.sublanguage.name
        # Add starting token to new tree
        #starting_node = self.create_node("")
        #self.add_node(parser.previous_version.get_bos(), starting_node)
        #self.node_map[(self.cursor[0], self.cursor[1])] = root.children[0]

        magictoken.symbol.parser = parser
        return magictoken

    def create_node(self, text, magic=False):
        if magic:
            symbol = MagicTerminal(text)
        else:
            symbol = Terminal(text)
        node = TextNode(symbol, -1, [], -1)
        return node

    def add_node(self, previous_node, new_node):
        previous_node.parent.insert_after_node(previous_node, new_node)
        root = new_node.get_root()
        if not isinstance(new_node.symbol, MagicTerminal):
            pl = self.priorities[root]
            tl = self.lexers[root]
            text = new_node.symbol.name
            match = tl.match(text)[0]
            assert match[0] == text
            new_node.lookup = match[1]
            new_node.priority = match[2]
            #new_node.regex = pl.regex(text)
            #new_node.priority = pl.priority(text)
            #new_node.lookup = pl.name(text)

    def cursor_movement(self, key):
        if key == QtCore.Qt.Key_Up:
            if self.cursor.y > 0:
                self.cursor.y -= 1
                if self.cursor.x > self.max_cols[self.cursor.y]:
                    self.cursor.x = self.max_cols[self.cursor.y]
        elif key == QtCore.Qt.Key_Down:
            if self.cursor.y < len(self.max_cols)-1:
                self.cursor.y += 1
                if self.cursor.x > self.max_cols[self.cursor.y]:
                    self.cursor.x = self.max_cols[self.cursor.y]
        elif key == QtCore.Qt.Key_Left:
            if self.cursor.x > 0:
                self.cursor.x -= 1
        elif key == QtCore.Qt.Key_Right:
            if self.cursor.x < self.max_cols[self.cursor.y]:
                self.cursor.x += 1

    # ========================== AST modification stuff ========================== #

    def char_difference(self, cursor1, cursor2):
        if cursor1.y == cursor2.y:
            return abs(cursor1.x - cursor2.x)

        start = min(cursor1, cursor2)
        end = max(cursor1, cursor2)

        chars = 0
        chars += self.max_cols[start.y] - start.x
        chars += 1 # return
        chars += end.x

        for y in range(start.y+1, end.y):
            chars += self.max_cols[y]
            chars += 1 # return

        return chars

    def hasSelection(self):
        return self.selection_start != self.selection_end

    def deleteSelection(self):
        #XXX simple version: later we might want to modify the nodes directly
        #nodes, diff_start, diff_end = self.get_nodes_from_selection()
        chars = self.char_difference(self.selection_start, self.selection_end)
        self.cursor = min(self.selection_start, self.selection_end)
        self.selection_start = Cursor(0,0)
        self.selection_end = Cursor(0,0)
        for i in range(chars):
            #XXX this draws the AST (if selected) in every iteration
            event = QKeyEvent(QEvent.KeyPress, Qt.Key_Delete, Qt.NoModifier, "delete")
            QCoreApplication.postEvent(self, event)

    def copySelection(self):
        nodes, diff_start, diff_end = self.get_nodes_from_selection()
        if len(nodes) == 1:
            QApplication.clipboard().setText(nodes[0].symbol.name[diff_start:])
            return
        text = []
        start = nodes.pop(0)
        end = nodes.pop(-1)

        text.append(start.symbol.name[diff_start:])
        for node in nodes:
            text.append(node.symbol.name)
        text.append(end.symbol.name[:diff_end])
        QApplication.clipboard().setText("".join(text))

    def pasteSelection(self):
        text = QApplication.clipboard().text()
        self.insertText(text)

    def insertText(self, text):
        self.indentation = False
        for c in str(text):
            if c == "\n" or c == "\r":
                key = Qt.Key_Return
                modifier = Qt.NoModifier
            elif ord(c) in range(97, 122): # a-z
                key = ord(c) - 32
                modifier = Qt.NoModifier
            elif ord(c) in range(65, 90): # A-Z
                key = ord(c)
                modifier = Qt.ShiftModifier
            else:   # !, {, }, ...
                key = ord(c)
                modifier = Qt.NoModifier
            event = QKeyEvent(QEvent.KeyPress, key, modifier, c)
            #QCoreApplication.postEvent(self, event)
            self.keyPressEvent(event)
        self.indentation = True

    def insertTextNoSim(self, text):
        parser = list(self.parsers.values())[0]
        lexer = list(self.lexers.values())[0]
        # lex text into tokens
        success = lexer.match(text)
        # insert tokens into tree
        parent = parser.previous_version.parent
        bos = parser.previous_version.get_bos()
        success.reverse()
        for match in success:#lex.tokens:
            symbol = Terminal(match[0])
            node = TextNode(symbol, -1, [], -1)
            node.lookup = match[1]
            parent.insert_after_node(bos, node)

    def repair(self, startnode):
        if startnode is None:
            return
        if isinstance(startnode, BOS) or isinstance(startnode, EOS):
            return
        if isinstance(startnode.symbol, MagicTerminal):
            return
        print("========== Starting Repair procedure ==========")
        print("Startnode", startnode.symbol)
        root = startnode.get_root()
        regex_list = []
        # find all regexs that include the new input string
        for regex in self.lexers[root].regexlist.keys():
            if self.in_regex(startnode.symbol.name, regex):
                regex_list.append(regex)
        print("    Possible regex:", regex_list)

        # expand to the left as long as all chars of those tokens are inside one of the regexs
        left_tokens = self.get_matching_tokens(startnode, regex_list, "left")
        left_tokens.reverse()
        # expand to the right as long as tokens may match
        right_tokens = self.get_matching_tokens(startnode, regex_list, "right")

        # merge all tokens together
        print("    Tokenlist:", left_tokens, right_tokens)
        newtoken_text = []
        for token in left_tokens:
            newtoken_text.append(token.symbol.name)
        newtoken_text.append(startnode.symbol.name)
        for token in right_tokens:
            newtoken_text.append(token.symbol.name)
        print("    Relexing:", repr("".join(newtoken_text)))


        tl = self.lexers[root]
        success = tl.match("".join(newtoken_text))
        #return

        # relex token
       #from lexer import Lexer
       #lex = Lexer("".join(newtoken_text))
       #regex_dict = {}
       #i = 0
       #print("creating groups")
       #for regex in self.getPL().rules.keys():
       #    regex_dict["Group_" + str(i)] = regex
       #    print(i, regex)
       #    i += 1
       #lex.set_regex(regex_dict)
       #print("check for valid lex")
       #success = lex.lex()
       #print(lex.tokens)
       #print("relexing done")

        # if relexing successfull, replace old tokens with new ones
        if success: #XXX is this false at any time?
            print("success", success)
            parent = startnode.parent
            # remove old tokens
            # XXX this removes the first appearance of that token (which isn't always the one relexed)
            for token in left_tokens:
                #print("left remove", token)
                token.parent.remove_child(token)
            for token in right_tokens:
                #print("right remove", token)
                token.parent.remove_child(token) #XXX maybe invoke mark_changed here
            # create and insert new tokens
            #print("parent children before", parent.children)
            #lex.tokens.reverse()
            success.reverse()
            for match in success:#lex.tokens:
                symbol = Terminal(match[0])
                node = TextNode(symbol, -1, [], -1)
                node.lookup = match[1]
                #node = self.create_new_node(token)#token.value)
                parent.insert_after_node(startnode, node)
                print("adding", node)
            parent.remove_child(startnode)
            #print("parent children after", parent.children)
            parent.mark_changed() # XXX changed or not changed? if it fits this hasn't really changed. only the removed nodes have changed
        print("Repaired to", startnode)
        print("============== End Repair ================")

    def get_matching_tokens(self, startnode, regex_list, direction):
        token_list = []
        done = False
        token = startnode
        while not done:
            if direction == "left":
                token = token.previous_terminal()
            elif direction == "right":
                token = token.next_terminal()
            if token is None:
                break
            if token.symbol.name == "":
                break
            if isinstance(token.symbol, MagicTerminal):
                break
            if isinstance(token, BOS) or isinstance(token, EOS):
                break
            for c in token.symbol.name:
                match = False
                for regex in regex_list:
                    if self.in_regex(c, regex):
                        match = True
                        break
                if not match:
                    done = True # reached a character that matches no regex
                    break
            if not done:
                token_list.append(token)
        return token_list

    def in_regex(self, c, regex):
        #XXX write regex parser that returns all possible tokens
        import string, re
        # support java comments
        if c not in ["\r", "\n", "r", "n"] and regex == "//[^\\r\\n]*":
            return True
        # support strings
        if c not in ["\r","\n", "r", "n"] and regex == "\"[^\"]*\"":
            return True
        # support chars
        if c not in ["\r","\n", "r", "n"] and regex == "\'[^\']*\'":
            return True
        # fix to avoid relexing whole program on typing 'r' or 'n'
        if c in "[\\n\\r]" and regex == "[\\n\\r]":
            return False
        if c in regex:
            if c not in ["+", "*", ".", "\\"]:
                return True

            if c == "+" and regex.find("\+") != -1:
                return True
            if c == "*" and regex.find("\*") != -1:
                return True
            if c == "." and regex.find("\.") != -1:
                return True
            if c == "\\" and regex == "\"([a-zA-Z0-9 ]|\\\\\")*\"":
                return True
            return False
        if c in string.lowercase and re.findall("\[.*a-z.*\]", regex):
            return True
        if c in string.uppercase and re.findall("\[.*A-Z.*\]", regex):
            return True
        if c in string.digits and re.findall("\[.*0-9.*\]", regex):
            return True
        if regex == "[ \\n\\t\\r]+" and re.findall(regex, c):
            return True
        #if c in [" ", "\n", "\t", "\r"] and regex == "[ \\n\\t\\r]+":
        #    return True
        if re.match("^" + regex + "$", c):
            return True
        return False

    def dead_create_new_node(self, text, magic=False):
        if magic:
            symbol = MagicTerminal(text)
        else:
            symbol = Terminal(text)
        node = TextNode(symbol, -1, [], -1)
        node.regex = self.getPL().regex(text)
        node.priority = self.getPL().priority(text)
        node.lookup = self.getPL().name(text)
        return node

    def getTL(self):
        return self.getWindow().tl

    def getPL(self):
        return self.getWindow().pl

    def getLRP(self):
        return self.getWindow().lrp

    def getWindow(self):
        return self.window()

    def showSubgrammarMenu(self):
        self.sublanguage = None
        # Create menu
        menu = QtGui.QMenu( self )
        # Create actions
        toolbar = QtGui.QToolBar()
        for l in languages:
            item = toolbar.addAction(str(l), self.createMenuFunction(l))
            menu.addAction(item)
        menu.exec_(self.mapToGlobal(QPoint(0,0)) + QPoint(3 + self.cursor.x*self.fontwt, 3 + (self.cursor.y+1)*self.fontht))

    def createMenuFunction(self, l):
        def action():
            self.sublanguage = l
            self.edit_rightnode = True
        return action

    def selectSubgrammar(self, item):
        print("SELECTED GRAMMAR", item)

    def randomDeletion(self):
        import random
        from time import sleep
        deleted = []
        for i in range(30):
            # choose random line
            y = random.randint(0, len(self.max_cols)-1)
            if self.max_cols[y] > 0:
                x = random.randint(0, self.max_cols[y])
                self.cursor = Cursor(x,y)

                event = QKeyEvent(QEvent.KeyPress, Qt.Key_Delete, Qt.NoModifier, "delete")
                #QCoreApplication.postEvent(self, event)
                self.keyPressEvent(event)

                if self.last_delchar: # might be none if delete at end of file
                    deleted.append((self.cursor.copy(), self.last_delchar))
        self.deleted_chars = deleted

    def undoDeletion(self):
        self.indentation = False
        for cursor, c in reversed(self.deleted_chars):
            self.cursor = cursor
            if c == "\n":
                key = Qt.Key_Return
                modifier = Qt.NoModifier
            elif ord(c) in range(97, 122): # a-z
                key = ord(c) - 32
                modifier = Qt.NoModifier
            elif ord(c) in range(65, 90): # A-Z
                key = ord(c)
                modifier = Qt.ShiftModifier
            else:   # !, {, }, ...
                key = ord(c)
                modifier = Qt.NoModifier
            event = QKeyEvent(QEvent.KeyPress, key, modifier, c)
            self.keyPressEvent(event)
        self.indentation = True


class Cursor(object):
    def __init__(self, x, y):
        self.x = x
        self.y = y

    def copy(self):
        return Cursor(self.x, self.y)

    def __le__(self, other):
        return self < other or self == other

    def __ge__(self, other):
        return self > other or self == other

    def __lt__(self, other):
        if isinstance(other, Cursor):
            if self.y < other.y:
                return True
            elif self.y == other.y and self.x < other.x:
                return True
        return False

    def __gt__(self, other):
        if isinstance(other, Cursor):
            if self.y > other.y:
                return True
            elif self.y == other.y and self.x > other.x:
                return True
        return False

    def __eq__(self, other):
        if isinstance(other, Cursor):
            return self.x == other.x and self.y == other.y
        return False

    def __ne__(self, other):
        return not self == other

    def __repr__(self):
        return "Cursor(%s, %s)" % (self.x, self.y)


class Window(QtGui.QMainWindow):
    def __init__(self):
        QtGui.QMainWindow.__init__(self)
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)

        #self.connect(self.ui.pushButton, SIGNAL("clicked()"), self.btReparse)

        # init with a grammar and priorities
        self.ui.teGrammar.document().setPlainText(grammar)
        self.ui.tePriorities.document().setPlainText(priorities)
        self.connect(self.ui.btUpdate, SIGNAL("clicked()"), self.btUpdateGrammar)

        self.connect(self.ui.cb_toggle_ws, SIGNAL("clicked()"), self.btRefresh)
        self.connect(self.ui.cb_toggle_ast, SIGNAL("clicked()"), self.btRefresh)
        self.connect(self.ui.cbShowLangBoxes, SIGNAL("clicked()"), self.ui.frame.update)
        self.connect(self.ui.cb_fit_ast, SIGNAL("clicked()"), self.btRefresh)

        self.connect(self.ui.btShowSingleState, SIGNAL("clicked()"), self.showSingleState)
        self.connect(self.ui.btShowWholeGraph, SIGNAL("clicked()"), self.showWholeGraph)
        self.connect(self.ui.bt_show_sel_ast, SIGNAL("clicked()"), self.showAstSelection)

        for l in languages:
            self.ui.listWidget.addItem(str(l))

        self.ui.listWidget.item(0).setSelected(True)

        self.loadLanguage(self.ui.listWidget.item(5))

        self.connect(self.ui.listWidget, SIGNAL("itemClicked(QListWidgetItem *)"), self.loadLanguage)
        self.connect(self.ui.actionOpen, SIGNAL("triggered()"), self.openfile)
        self.connect(self.ui.actionRandomDel, SIGNAL("triggered()"), self.ui.frame.randomDeletion)
        self.connect(self.ui.actionUndoRandomDel, SIGNAL("triggered()"), self.ui.frame.undoDeletion)

        self.ui.graphicsView.setRenderHints(QPainter.Antialiasing | QPainter.SmoothPixmapTransform | QPainter.TextAntialiasing)

        self.ui.frame.setFocus(True)

    def openfile(self):
        filename = QFileDialog.getOpenFileName()#"Open File", "", "Files (*.*)")
        text = open(filename, "r").read()
        if text[:-1] in ["\n", "\r"]:
            text = text[:-1]
        # key simulated opening
        #self.ui.frame.insertText(text)
        self.ui.frame.insertTextNoSim(text)
        self.btReparse(None)

    def loadLanguage(self, item):
        print("Loading Language...")
        language = languages[self.ui.listWidget.row(item)]
        self.ui.teGrammar.document().setPlainText(language.grammar)
        self.ui.tePriorities.document().setPlainText(language.priorities)
        self.main_language = language.name
        self.btUpdateGrammar()

    def btUpdateGrammar(self):
        new_grammar = str(self.ui.teGrammar.document().toPlainText())
        new_priorities = str(self.ui.tePriorities.document().toPlainText())
        whitespaces = self.ui.cb_add_implicit_ws.isChecked()
        print("Creating Incremental Parser")
        self.lrp = IncParser(new_grammar, 1, whitespaces)
        self.lrp.init_ast()
        self.pl = PriorityLexer(new_priorities)
        self.tl = TokenLexer(self.pl.rules)
        self.ui.frame.set_lrparser(self.lrp, self.main_language)
        self.ui.frame.reset()
        self.ui.graphicsView.setScene(QGraphicsScene())
        print("Done.")

    def showWholeGraph(self):
        img = Viewer("pydot").create_pydot_graph(self.lrp.graph)
        self.showImage(self.ui.gvStategraph, img)

    def showSingleState(self):
        img = Viewer("pydot").show_single_state(self.lrp.graph, int(self.ui.leSingleState.text()))
        self.showImage(self.ui.gvStategraph, img)

    def btRefresh(self):
        whitespaces = self.ui.cb_toggle_ws.isChecked()
        image = Viewer('pydot').get_tree_image(self.lrp.previous_version.parent, [], whitespaces)
        self.showImage(self.ui.graphicsView, image)

    def btReparse(self, selected_node):
        whitespaces = self.ui.cb_toggle_ws.isChecked()
        results = []
        for key in self.ui.frame.parsers:
            lang = self.ui.frame.parser_langs[key]
            status = self.ui.frame.parsers[key].inc_parse()
            qlabel = QLabel(lang)
            if status:
                results.append("<span style='background-color: #00ff00'>" + lang + "</span>")
            else:
                results.append("<span style='background-color: #ff0000; color: #ffffff;'>" + lang + "</span>")
        self.ui.te_pstatus.setHtml(" | ".join(results))
        self.showAst(selected_node)

    def showAst(self, selected_node):
        whitespaces = self.ui.cb_toggle_ws.isChecked()
        if self.ui.cb_toggle_ast.isChecked():
            image = Viewer('pydot').get_tree_image(self.lrp.previous_version.parent, selected_node, whitespaces)
            self.showImage(self.ui.graphicsView, image)

    def showAstSelection(self):
        whitespaces = self.ui.cb_toggle_ws.isChecked()
        nodes, _, _ = self.ui.frame.get_nodes_from_selection()
        if len(nodes) == 0:
            return
        start = nodes[0]
        end = nodes[-1]
        ast = self.lrp.previous_version
        parent = ast.find_common_parent(start, end)
        for node in nodes:
            p = node.get_parent()
            if p and p is not parent:
                nodes.append(p)
        nodes.append(parent)
        if parent:
            image = Viewer('pydot').get_tree_image(parent, [start, end], whitespaces, nodes)
            self.showImage(self.ui.graphicsView, image)


    def showLookahead(self, lrp=None):
        la = lrp.get_next_symbols_string()
        self.ui.lineEdit.setText(la)

    def showImage(self, graphicsview, imagefile):
        scene = QGraphicsScene()
        item = QGraphicsPixmapItem(QPixmap(imagefile))
        scene.addItem(item);
        graphicsview.setScene(scene)
        graphicsview.resetMatrix()
        if self.ui.cb_fit_ast.isChecked():
            self.fitInView(graphicsview)

    def fitInView(self, graphicsview):
        graphicsview.fitInView(graphicsview.sceneRect(), Qt.KeepAspectRatio)

def main():
    app = QtGui.QApplication(sys.argv)
    app.setStyle('gtk')
    window=Window()

    window.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
