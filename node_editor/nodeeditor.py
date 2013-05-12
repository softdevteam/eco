from __future__ import print_function

import sys
sys.path.append("../")
sys.path.append("../lr-parser/")

from PyQt4 import QtCore
from PyQt4.QtCore import *
from PyQt4 import QtGui
from PyQt4.QtGui import *

try:
    import cPickle as pickle
except:
    import pickle

from gui import Ui_MainWindow

from plexer import PriorityLexer
from incparser import IncParser
from viewer import Viewer

from gparser import Terminal, MagicTerminal
from astree import TextNode, BOS, EOS

from languages import languages, lang_dict

from token_lexer import TokenLexer

from time import time
import os
import math

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

class StyleNode(object):
    def __init__(self, mode, bgcolor):
        self.mode = mode
        self.bgcolor = bgcolor

class ImageNode(object):
    def __init__(self, node, y):
        self.node = node
        self.y = y

    def __getattr__(self, name):
        return self.node.__getattribute__(name)

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

        self.viewport_x = 0
        self.viewport_y = 0

        self.changed_line = -1
        self.line_info = []
        self.node_list = []
        self.node_map = {}
        self.max_cols = []
        self.indentations = {}

        self.parsers = {}
        self.lexers = {}
        self.priorities = {}
        self.parser_langs = {}
        self.magic_tokens = []

        self.edit_rightnode = False
        self.indentation = True

        self.last_delchar = ""
        self.lbox_nesting = 0
        self.nesting_colors = {
            0: QColor("#a4c6cf"), # light blue
            1: QColor("#dd9d9d"), # light red
            2: QColor("#caffcc"), # light green
            3: QColor("#f4e790"), # light yellow
            4: QColor("#dccee4"), # light purple
        }

    def reset(self):
        self.indentations = {}
        self.max_cols = []
        self.node_map = {}
        self.cursor = Cursor(0,0)
        self.update()
        self.line_info = []

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

        self.node_list = []
        self.node_list.append(self.ast.parent.children[0]) # bos is first terminal in first line

        self.line_info.append([self.ast.parent.children[0], self.ast.parent.children[1]]) # start with BOS and EOS

    def set_sublanguage(self, language):
        self.sublanguage = language

    # ========================== GUI related stuff ========================== #

    def blink(self):
        if self.show_cursor:
            self.show_cursor = 0
        else:
            self.show_cursor = 1
        self.update()

    def sliderChanged(self, value):
        change = self.viewport_y - value
        self.viewport_y = value
        #if (change < 0 and 0 < self.cursor.y):
        if (change > 0 and self.cursor.y < len(self.max_cols)-1):
            self.cursor.y += change
        self.update()

    def sliderXChanged(self, value):
        self.update()
        self.viewport_x = value

    def paintEvent(self, event):
        QtGui.QFrame.paintEvent(self, event)
        paint = QtGui.QPainter()
        paint.begin(self)
        paint.setFont(self.font)

        y = 0
        x = 0

        bos = self.ast.parent.children[0]
        #bos = self.node_list[self.viewport_y]
        self.indentations = {}
        self.node_map.clear()
        self.node_map[(x,y)] = bos
        self.max_cols = []
        self.longest_column = 0

        # calculate how many lines we need to show
        self.init_height = self.geometry().height()

        #x, y = self.paintAST(paint, bos, -self.viewport_x, y)
        self.paintLines(paint, self.viewport_y)

        if self.hasFocus() and self.show_cursor:
            if self.cursor.x > self.max_cols[self.cursor.y]:
                self.cursor.x = self.max_cols[self.cursor.y]
            #paint.drawRect(3 + self.cursor[0] * self.fontwt, 2 + self.cursor[1] * self.fontht, self.fontwt-1, self.fontht)
            paint.drawRect(0 + self.cursor.x * self.fontwt, 5 + self.cursor.y * self.fontht, 0, self.fontht - 3)

        self.paintSelection(paint)
        paint.end()

       #width = (max(self.max_cols)+1) * self.fontwt
       #print("width:", width)
       #print(self.geometry())
       #print("viewport", self.getWindow().ui.scrollArea.viewport().geometry())
       #height = len(self.max_cols) * self.fontht + 3
       #geom = self.geometry()
       #geom.setWidth(width)
       #geom.setHeight(height)
       #self.setMinimumWidth(width)
       #if self.hasFocus():
       #    pass
       #    #self.getWindow().ui.scrollArea.ensureVisible (self.cursor.x * self.fontwt, self.cursor.y * self.fontht, self.fontwt, self.fontht+3 )

       ##self.getWindow().ui.scrollArea.horizontalScrollBar().setMinimum(0)
       ##self.getWindow().ui.scrollArea.horizontalScrollBar().setMaximum((width - self.getWindow().ui.scrollArea.viewport().size().width())/self.fontwt)
       ##self.getWindow().ui.scrollArea.horizontalScrollBar().setPageStep(1)
        self.getWindow().ui.scrollArea.verticalScrollBar().setMinimum(0)
        total_lines = len(self.line_info)
        max_visible_lines = self.geometry().height() / self.fontht
        vmax = max(0, total_lines - max_visible_lines)
        self.getWindow().ui.scrollArea.verticalScrollBar().setMaximum(vmax)
        self.getWindow().ui.scrollArea.verticalScrollBar().setPageStep(1)


    def paintLines(self, paint, startline):
        import os
        # get all selected magic tokens
        node = self.get_nodes_at_position()[0][0]
        selected_magic = node.magic_parent
        node = node.get_root().get_magicterminal()

        r = min(len(self.line_info)-self.viewport_y, (self.geometry().height()/self.fontht))

        # check if the line starts with a partial image
        y = startline
        line = self.line_info[y]
        while len(line) == 1 and isinstance(line[0], ImageNode) and line[0].y > 0:
            y -= 1
            line = self.line_info[y]

        line_range = range(y - startline, r)
        for i in line_range:
            line = self.line_info[startline + i]
            line_str = []
            styles = []
            x = 0
            for node in line:
                if isinstance(node, ImageNode) and node.y > 0:
                    continue
                if isinstance(node, BOS):
                    continue
                if isinstance(node, EOS):
                    continue
                if node.lookup == "<return>":
                    continue
                text = node.symbol.name
                if isinstance(node, ImageNode):
                    node = node.node
                    paint.drawImage(QPoint(x, 3 + i * self.fontht), node.image)
                    x += math.ceil(node.image.width() * 1.0 / self.fontwt) * self.fontwt
                    continue
                if self.getWindow().ui.cbShowLangBoxes.isChecked() or node.magic_parent is selected_magic:
                    try:
                        color_id = self.magic_tokens.index(id(node.magic_parent))
                        paint.fillRect(QRectF(x,3 + self.fontht + i*self.fontht, len(text)*self.fontwt, -self.fontht+2), self.nesting_colors[color_id])
                    except ValueError:
                        pass
                paint.drawText(QtCore.QPointF(x, self.fontht + i*self.fontht), text)
                x += len(text)*self.fontwt
            if i >= 0:
                self.max_cols.append(x/self.fontwt)

    def paintAST(self, paint, bos, x, y):
        node = bos.next_terminal()
        parser = self.parsers[bos.get_root()]
        while node and not isinstance(node, EOS):
            if node.symbol.name in ["\n", "\r"]:
                self.max_cols.append(x)
                y += 1
                x = -self.viewport_x
                self.node_map[(x,y)] = node

                if len(self.max_cols) * self.fontht > self.init_height:
                    break

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
            paint.fillRect(start.x * self.fontwt, 4+start.y * self.fontht, width * self.fontwt, self.fontht, QColor(0,0,255,100))
        else:
            # paint start to line end
            width = self.max_cols[start.y] - start.x
            paint.fillRect(start.x * self.fontwt, 4+start.y * self.fontht, width * self.fontwt, self.fontht, QColor(0,0,255,100))

            # paint lines in between
            for y in range(start.y+1, end.y):
                width = self.max_cols[y]
                paint.fillRect(0 * self.fontwt, 4+y * self.fontht, width * self.fontwt, self.fontht, QColor(0,0,255,100))

            # paint line start to end
            width = end.x
            paint.fillRect(0 * self.fontwt, 4+end.y * self.fontht, width * self.fontwt, self.fontht, QColor(0,0,255,100))


    def recalculate_positions(self): # without painting
        return
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
            firstnode = self.line_info[y][0]
            if firstnode.lookup == "<ws>":
                return len(firstnode.symbol.name)
            return 0
        except IndexError:
            return 0

    def document_y(self):
        return self.viewport_y + self.cursor.y

    def get_nodes_at_position(self):
        y = self.document_y()
        line = self.line_info[y]
        #print("=== GETTING NODES ====")
        inbetween = False
        x = 0
        if self.cursor.x == 0 and y > 0:# and not isinstance(line[0], BOS):
            node = self.line_info[y-1][-1]
            i = 2
            while isinstance(node, ImageNode):
                node = self.line_info[y-i][-1]
                i+=1
            #print("x=0: got nodes from pos", node, node.next_terminal())
            #return ([node, node.next_terminal()], False, 0)
        else:
            x = 0
            for node in line:
                if isinstance(node, EOS):
                    continue
                if isinstance(node, StyleNode):
                    continue
                if node.image:
                    x += math.ceil(node.image.width() * 1.0 / self.fontwt)
                else:
                    x += len(node.symbol.name) # XXX: later store line length in line_info as well
                if x >= self.cursor.x:
                    break
            if x > self.cursor.x:
                inbetween = True
        if not inbetween and self.edit_rightnode:
            if isinstance(node.next_terminal().symbol, MagicTerminal):
                node = node.next_terminal().symbol.parser.children[0]
            elif isinstance(node.next_terminal(), EOS):
                root = node.next_terminal().get_root()
                magic = root.get_magicterminal()
                if magic:
                    node = magic
        #print("got nodes from pos", node, node.next_terminal(), inbetween, x, self.cursor.x)
        return ([node, node.next_terminal()], inbetween, x)

    def OLD2get_nodes_at_position(self):
        print("cursor", self.cursor)
        node = self.node_list[self.cursor.y + self.viewport_y]
        x = 0#len(node.symbol.name)
        inbetween = False
        while x < self.cursor.x:
            node = node.next_terminal()
            x += len(node.symbol.name)
        if x > self.cursor.x:
            inbetween = True
        print("got nodes from pos", node, inbetween, x, self.cursor.x)
        return ([node, node.next_terminal()], inbetween, x)

    def OLDget_nodes_at_position(self):
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

        temp = self.cursor

        self.cursor = cur_start
        start_node, start_inbetween, start_x = self.get_nodes_at_position()
        diff_start = 0
        if start_inbetween:
            diff_start = len(start_node[0].symbol.name) - (start_x - self.cursor.x)
        include_start = True

        self.cursor = cur_end
        end_node, end_inbetween, end_x = self.get_nodes_at_position()
        diff_end = 0
        if end_inbetween:
            diff_end = len(end_node[0].symbol.name) - (end_x - self.cursor.x)

        self.cursor = temp

        start = start_node[0]
        end = end_node[0]


        nodes = []
        node = start
        if include_start:
            nodes.append(start)
        while node is not end:
            node = node.next_terminal()
            # extend search into magic tree
            if isinstance(node.symbol, MagicTerminal):
                node = node.symbol.parser.children[0]
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

    def XXXkeyPressEvent(self, e):
        import cProfile
        cProfile.runctx("self.linkkeyPressEvent(e)", globals(), locals())

    def keyPressEvent(self, e):
        print("====================== KEYPRESS (>>%s<<) ============================" % (repr(e.text()),))
        print("first get_nodes_at_pos")
        selected_nodes, inbetween, x = self.get_nodes_at_position()
        print(selected_nodes)

        text = e.text()
        self.changed_line = self.document_y()

        if e.key() == Qt.Key_Backspace:
            if self.document_y() > 0 and self.cursor.x == 0:
                self.cursor_movement(Qt.Key_Up)
                self.repaint() # XXX store line width in line_info to avoid unnecessary redrawing
                #self.changed_line = self.document_y()
                self.cursor.x = self.max_cols[self.cursor.y]
                event = QKeyEvent(QEvent.KeyPress, Qt.Key_Delete, e.modifiers(), e.text())
                self.keyPressEvent(event)
                return

        if e.key() == Qt.Key_Tab:
            text = "    "
        if e.key() in [Qt.Key_Up, Qt.Key_Down, Qt.Key_Left, Qt.Key_Right]:
            self.edit_rightnode = False
            self.cursor_movement(e.key())
            self.update()
            selected_nodes, _, _ = self.get_nodes_at_position()
            self.getWindow().showAst(selected_nodes)

            # update lookahead when moving cursors
            root = selected_nodes[0].get_root()
            lrp = self.parsers[root]
            self.getWindow().showLookahead(lrp)
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
                if isinstance(selected_nodes[0], ImageNode):
                    selected_nodes[0].backspace(-1)
                    # remove all related imagenodes
                    selected_nodes[0].image = None
                    # refresh
                    self.getWindow().btReparse([])
                    self.rescan_line(self.changed_line)
                    self.repaint() # this recalculates self.max_cols
                    return
                if self.hasSelection():
                    self.deleteSelection()
                    return
                if e.key() == Qt.Key_Backspace:
                    if self.cursor.x > 0:
                        self.cursor.x -= 1
                    else:
                        if self.document_y() > 0:
                            self.cursor_movement(Qt.Key_Up)
                            self.changed_line = self.document_y()
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
                            self.magic_tokens.remove(id(magic))
                            del self.parsers[root]
                            del self.lexers[root]
                            del self.priorities[root]

                            selected_nodes, inbetween, x = self.get_nodes_at_position()
                        else:
                            node.parent.remove_child(node)
                            if node.lookup == "<return>":
                                pass
                                #del self.node_list[self.viewport_y + self.cursor.y+1]

                    else:
                        repairnode = node
            # NORMAL KEY
            else:
                if self.hasSelection():
                    self.deleteSelection()
                if e.key() == Qt.Key_Space and e.modifiers() == Qt.ControlModifier:
                    self.showSubgrammarMenu()
                    if self.sublanguage:
                        newnode = self.add_magic()
                        self.edit_rightnode = True # writes next char into magic ast
                    else:
                        return
                elif e.key() == Qt.Key_Space and e.modifiers() == Qt.ControlModifier | Qt.ShiftModifier:
                    self.edit_rightnode = True # writes next char into magic ast
                    self.update()
                    return
                else:
                    if e.key() == Qt.Key_Return:
                        if self.indentation:
                            indentation = self.get_indentation(self.document_y())
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
                    if isinstance(node, ImageNode):
                        node = node.next_terminal()
                    self.add_node(node, newnode)
                    #node.parent.insert_after_node(node, newnode)
                    repairnode = newnode
                if e.key() == Qt.Key_Space and e.modifiers() == Qt.ControlModifier:
                    pass # do nothing
                elif e.key() == Qt.Key_Return:
                    #self.cursor_movement(Qt.Key_Down)
                    #self.cursor.x = indentation
                    pass
                elif e.key() == Qt.Key_Tab:
                    self.cursor.x += 4
                else:
                    self.cursor.x += 1
            self.repair(repairnode)

        self.getWindow().btReparse([])
        self.rescan_line(self.changed_line)
        self.repaint() # this recalculates self.max_cols

        if e.key() == Qt.Key_Return:
            self.cursor_movement(Qt.Key_Down)
            self.cursor.x = indentation

        root = selected_nodes[0].get_root()
        lrp = self.parsers[root]
        self.getWindow().showLookahead(lrp)
        self.update()

    def rescan_line(self, y):
        # Start at the first node and run until you find a newline
        # replace the current line with all nodes found on the way
        # if there are more nodes after the newline
        #     copy them into a new line
        #     rescan that line
        # if you reach the next lines node, a new line was deleted
        #     merge this and the next line
        #     delete the next line
        #     the next lines node is line[-1].next_terminal()
        line = self.line_info[y]
        if line == []:
            return
        startnode = line[0]
        endnode = line[-1]

        if startnode.deleted:
            i = 1
            node = self.line_info[y-i][-1]
            while isinstance(node, ImageNode): # last element should always be a newline
                i += 1
                node = self.line_info[y-i][-1]
            startnode = node.next_terminal()

        # newline in empty line was deleted -> delete current line
        if startnode is endnode and endnode.deleted:
            assert False
            del self.line_info[y]
            if self.line_info == []:
                self.line_info = [[]]
            return

        # a newline was deleted -> merge with next line
        if endnode.deleted:
            try:
                i = 1
                endnode = self.line_info[y+i][-1]
                while isinstance(endnode, ImageNode):
                    i += 1
                    endnode = self.line_info[y+i][-1]
                del self.line_info[y+i]
            except IndexError:
                endnode = self.ast.parent.children[-1]

        # last line -> endnode = EOS
        if y == len(self.line_info)-1:
            endnode = self.ast.parent.children[-1]

        node = startnode

        new_list = []

        next_token_after_magic = []
        while node is not endnode:
            if isinstance(node.symbol, MagicTerminal):
                bos = node.symbol.parser.children[0]
                new_list.append(bos)
                next_token_after_magic.append(node.next_terminal())
                node = bos.next_terminal()
                continue
            if isinstance(node, EOS):
                new_list.append(node)
                node = node.parent.get_parent().next_terminal() # magic terminal
                continue
            if node.magic_parent and node.magic_parent.symbol.name == "<Chemicals>":
                filename = "chemicals/" + node.symbol.name + ".png"
                if os.path.isfile(filename):
                    node.image = QImage(filename)
                else:
                    node.image = None
                    # delete subsequent imagenodes
                    while y+1 < len(self.line_info) and isinstance(self.line_info[y+1][0], ImageNode):
                        del self.line_info[y+1]
                if node.image:
                    empty_lines = int(math.ceil(node.image.height() * 1.0 / self.fontht))
                    empty_lines = max(0, empty_lines - 1)
                    for i in range(empty_lines):
                        # check if dummy lines exists, add if not
                        if y+1+i < len(self.line_info) and  isinstance(self.line_info[y+1+i][0], ImageNode):
                            break
                        else:
                            return_node = TextNode(Terminal("\n"), -1, [], -1)
                            return_node.lookup = "<return>"
                            self.line_info.insert(y+1, [ImageNode(node, i+1)])
                    node = ImageNode(node, 0)

            new_list.append(node)
            if node.lookup == "<return>":
                self.line_info[y] = new_list
                new_list = []
                y += 1
                while y < len(self.line_info) and isinstance(self.line_info[y][0], ImageNode):
                    y += 1
                self.line_info.insert(y, [])
            node = node.next_terminal()
        new_list.append(endnode)
        self.line_info[y] = new_list

    def repair_line(self, y):
        print("repair")

        line = self.line_info[y]
        print(line)
        startnode = line[0]
        endnode = line[-1]

        # update current line
        new_list = []
        node = startnode
        while node is not endnode:
            new_list.append(node)
            node = node.next_terminal()
        new_list.append(endnode)
        self.line_info[y] = new_list
        print("repaired to")
        print(new_list)
        return

        if node is not line[-1]: # if the found newline is not the last element
            self.line_info.insert(y+1, [node.next_terminal(), endnode])
            self.rescan_line(y+1)

       #while node is not endnode:
       #    print(node.symbol.name, id(node), node.next_terminal())

       #    if node is endnode:
       #        print("found endnode")
       #        new_list.append(endnode)
       #        break

       #    print("appending", node.symbol.name)
       #    new_list.append(node)

       #    # check for new newlines
       #    if node.lookup == "<return>":
       #        new_line = [node.next_terminal(), endnode]
       #        self.line_info.insert(y+1, new_line)
       #        self.rescan_line(y+1)
       #        break

       #    # XXX check for deleted newlines

       #    node = node.next_terminal()
       #self.line_info[y] = new_list
       #print(new_list)


    def add_magic(self):
        # Create magic token
        magictoken = self.create_node("<%s>" % self.sublanguage.name, magic=True)

        # Create parser, priorities and lexer
        parser = IncParser(self.sublanguage.grammar, 1, True)
        parser.init_ast(magictoken)
        self.magic_tokens.append(id(magictoken))
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

        magictoken.symbol.parser = root
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
        if self.cursor.x == 0:
            line = self.line_info[self.document_y()]
            if isinstance(line[0], BOS):
                line.insert(1, new_node)
            else:
                line.insert(0, new_node)
        root = new_node.get_root()
        if not isinstance(new_node.symbol, MagicTerminal):
            pl = self.priorities[root]
            tl = self.lexers[root]
            text = new_node.symbol.name
            match = tl.match(text)[0]
            new_node.lookup = match[1]
            new_node.priority = match[2]
            #new_node.regex = pl.regex(text)
            #new_node.priority = pl.priority(text)
            #new_node.lookup = pl.name(text)

    def cursor_movement(self, key):
        if key == QtCore.Qt.Key_Up:
            if self.cursor.y > 0:
                self.cursor.y -= 1
                while isinstance(self.line_info[self.document_y()][-1], ImageNode):
                    self.cursor.y -= 1
                if self.cursor.x > self.max_cols[self.cursor.y]:
                    self.cursor.x = self.max_cols[self.cursor.y]
            else:
                self.getWindow().ui.scrollArea.decVSlider()
        elif key == QtCore.Qt.Key_Down:
            if self.cursor.y < (self.geometry().height() / self.fontht) - 1 and self.document_y() < len(self.line_info)-1:
                self.cursor.y += 1
                while isinstance(self.line_info[self.document_y()][-1], ImageNode):
                    self.cursor.y += 1
                if self.cursor.x > self.max_cols[self.cursor.y]:
                    self.cursor.x = self.max_cols[self.cursor.y]
            else:
                self.getWindow().ui.scrollArea.incVSlider()
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
        # init
        self.line_info = []
        self.cursor = Cursor(0,0)
        self.viewport_y = 0
        for node in list(self.parsers):
            if node is not self.ast.parent:
                del self.parsers[node]
                del self.lexers[node]
                del self.priorities[node]
                del self.parser_langs[node]
                self.magic_tokens = []
        # convert linebreaks
        text = text.replace("\r\n","\r")
        parser = list(self.parsers.values())[0]
        lexer = list(self.lexers.values())[0]
        # lex text into tokens
        success = lexer.match(text)
        # reset tree
        bos = parser.previous_version.parent.children[0]
        eos = parser.previous_version.parent.children[-1]
        parser.previous_version.parent.children = [bos, eos]
        # insert tokens into tree
        parent = parser.previous_version.parent
        eos = parent.children.pop()
        last_node = parser.previous_version.get_bos()
        line_nodes = [last_node]
        for match in success:#lex.tokens:
            symbol = Terminal(match[0])
            node = TextNode(symbol, -1, [], -1)
            node.lookup = match[1]
            parent.children.append(node)
            last_node.next_term = node
            last_node.right = node
            node.left = last_node
            node.prev_term = last_node
            node.parent = parent

            line_nodes.append(node)

            if node.lookup == "<return>":
                self.line_info.append(line_nodes)
                line_nodes = []
                self.node_list.insert(1, node)

            last_node = node
        self.line_info.append(line_nodes) #add last line
        self.line_info[-1].append(eos)
        parent.children.append(eos)
        node.right = eos # link to eos
        node.next_term = eos
        eos.left = node
        eos.prev_term = node
        node.mark_changed()

    def repair(self, startnode):
        # XXX don't split nodes at once, but see if the relxing results in the same nodes
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
        print("    Tokenlist:", left_tokens, right_tokens)

        # merge all tokens together
        # do not repair return nodes since this destroys the mapping
        if startnode.symbol.name not in ["\n", "\r"]:
            #self.node_list.remove(startnode) # be sure you don't add it double
            newtoken_text = []
            for token in left_tokens:
                newtoken_text.append(token.symbol.name)
            newtoken_text.append(startnode.symbol.name)
            for token in right_tokens:
                newtoken_text.append(token.symbol.name)
            print("    Relexing:", repr("".join(newtoken_text)))
        else:
            startnode.symbol.name
            startnode.lookup == "<return>" # XXX use tl.match here
            left_tokens = []
            right_tokens = []
            return


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

        # NEW NODE INSERTION ALGORITHM THAT TRYS TO REUSE OLD OBJECTS
        if success:
            list_of_reusable_nodes = []
            list_of_reusable_nodes.extend(left_tokens)
            list_of_reusable_nodes.append(startnode)
            list_of_reusable_nodes.extend(right_tokens)

            print(len(success), len(list_of_reusable_nodes))
            for match in success:
                if len(list_of_reusable_nodes) > 0:
                    reusable_node = list_of_reusable_nodes.pop(0)
                    print("overwriting", reusable_node, "with", match)
                    reusable_node.symbol.name = match[0]
                    reusable_node.lookup = match[1]
                    reusable_node.mark_changed()
                    last_node = reusable_node
                else:
                    print("creating newnode", match)
                    newnode = TextNode(Terminal(match[0]), -1, [], -1)
                    newnode.lookup = match[1]
                    last_node.parent.insert_after_node(last_node, newnode)
                    newnode.mark_changed()
                    last_node = newnode

            # delete leftover nodes
            for node in list_of_reusable_nodes:
                node.mark_changed()
                node.parent.remove_child(node)

        return

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
                if node.lookup == "<return>":
                    self.node_list.insert(self.cursor.y + self.viewport_y, node)
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

                print("+++++++++++ DELETING", x, y)
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
            if c in ["\n","\r"]:
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

    def saveToFile(self, filename):
        f = open(filename, "w")

        # create pickle structure
        p = {}
        for node in self.parsers:
            p[node] = self.parser_langs[node]
        # remember main language root node
        main_lang = self.ast.parent
        pickle.dump((main_lang, p), f)

    def loadFromFile(self, filename):
        from astree import AST
        f = open(filename, "r")
        main_lang, p = pickle.load(f)

        #reset
        self.parsers = {}
        self.lexers = {}
        self.priorities = {}
        self.lexers = {}
        self.parser_langs = {}
        self.reset()
        self.magic_tokens = []

        for node in p:
            # load grammar
            lang_name = p[node]
            lang = lang_dict[lang_name]
            # create parser
            parser = IncParser(lang.grammar, 1, True) #XXX use whitespace checkbox
            parser.previous_version = AST(node)
            self.parsers[node] = parser
            # create priorities
            pl = PriorityLexer(lang.priorities)
            self.priorities[node] = pl
            # create tokenlexer
            tl = TokenLexer(pl.rules)
            self.lexers[node] = tl
            # load language
            self.parser_langs[node] = p[node]
            if node is main_lang:
                self.ast = parser.previous_version
            if node.get_magicterminal():
                self.magic_tokens.append(id(node.get_magicterminal()))
        node = self.ast.parent
        self.line_info.append([node.children[0], node.children[-1]])
        self.rescan_line(0)

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

class ScopeScrollArea(QtGui.QAbstractScrollArea):
    def setWidgetResizable(self, b):
        self.resizable = True

    def setAlignment(self, align):
        self.alignment = align

    def setWidget(self, widget):
        self.widget = widget
        self.viewport().setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        anotherbox = QtGui.QVBoxLayout(self.viewport())
        anotherbox.addWidget(widget)
        anotherbox.setSpacing(0)
        anotherbox.setContentsMargins(3,0,0,0)

    def incVSlider(self):
        self.verticalScrollBar().setSliderPosition(self.verticalScrollBar().sliderPosition() + self.verticalScrollBar().singleStep())

    def decVSlider(self):
        self.verticalScrollBar().setSliderPosition(self.verticalScrollBar().sliderPosition() - self.verticalScrollBar().singleStep())

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

        self.loadLanguage(self.ui.listWidget.item(0))

        self.connect(self.ui.listWidget, SIGNAL("itemClicked(QListWidgetItem *)"), self.loadLanguage)
        self.connect(self.ui.actionImport, SIGNAL("triggered()"), self.importfile)
        self.connect(self.ui.actionOpen, SIGNAL("triggered()"), self.openfile)
        self.connect(self.ui.actionSave, SIGNAL("triggered()"), self.savefile)
        self.connect(self.ui.actionRandomDel, SIGNAL("triggered()"), self.ui.frame.randomDeletion)
        self.connect(self.ui.actionUndoRandomDel, SIGNAL("triggered()"), self.ui.frame.undoDeletion)
        self.connect(self.ui.scrollArea.verticalScrollBar(), SIGNAL("valueChanged(int)"), self.ui.frame.sliderChanged)
        self.connect(self.ui.scrollArea.horizontalScrollBar(), SIGNAL("valueChanged(int)"), self.ui.frame.sliderXChanged)

        self.ui.graphicsView.setRenderHints(QPainter.Antialiasing | QPainter.SmoothPixmapTransform | QPainter.TextAntialiasing)

        self.ui.frame.setFocus(True)

    def importfile(self):
        filename = QFileDialog.getOpenFileName()#"Open File", "", "Files (*.*)")
        text = open(filename, "r").read()
        # for some reason text has an additional newline
        if text[-1] in ["\n", "\r"]:
            text = text[:-1]
        # key simulated opening
        #self.ui.frame.insertText(text)
        self.ui.frame.insertTextNoSim(text)
        self.btReparse(None)
        self.ui.frame.update()

    def savefile(self):
        filename = QFileDialog.getSaveFileName()
        self.ui.frame.saveToFile(filename)

    def openfile(self):
        filename = QFileDialog.getOpenFileName()
        self.ui.frame.loadFromFile(filename)

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
        self.ui.frame.reset()
        self.ui.frame.set_lrparser(self.lrp, self.main_language)
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
            #import cProfile
            #cProfile.runctx("status = self.ui.frame.parsers[key].inc_parse()", globals(), locals())
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
