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
from inclexer import IncrementalLexer
from viewer import Viewer

from gparser import Terminal, MagicTerminal
from astree import TextNode, BOS, EOS, ImageNode

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

def print_var(name, value):
    print("%s: %s" % (name, value))

class StyleNode(object):
    def __init__(self, mode, bgcolor):
        self.mode = mode
        self.bgcolor = bgcolor

class NodeSize(object):
    def __init__(self, w, h):
        self.w = w
        self.h = h

class Line(object):
    def __init__(self, node, height=1):
        self.node = node
        self.height = height
        self.width = 0

    def __repr__(self):
        return "Line(%s, width=%s, height=%s)" % (self.node, self.width, self.height)

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
        self.line_heights = []
        self.line_indents = []
        self.node_list = []
        self.node_map = {}
        self.max_cols = []
        self.line_widths = {}

        self.lines = []

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
        self.line_widths = {}
        self.node_map = {}
        self.cursor = Cursor(0,0)
        self.update()
        self.line_info = []
        self.line_heights = []
        self.line_indents = []
        self.lines = []

    def set_mainlanguage(self, parser, lexer, lang_name):
        self.parsers = {}
        self.lexers = {}
        self.priorities = {}
        self.lrp = parser
        self.ast = parser.previous_version
        self.parsers[parser.previous_version.parent] = parser
        self.lexers[parser.previous_version.parent] = lexer
        self.parser_langs[parser.previous_version.parent] = lang_name
        self.magic_tokens = []

        self.node_list = []
        self.node_list.append(self.ast.parent.children[0]) # bos is first terminal in first line

        self.line_info.append([self.ast.parent.children[0], self.ast.parent.children[1]]) # start with BOS and EOS
        self.line_heights.append(1)
        self.line_indents.append(None)

        self.lines.append(Line(self.ast.parent.children[0], 1))
        self.eos = self.ast.parent.children[1]

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

       #if self.hasFocus() and self.show_cursor:
       #    if self.cursor.x > self.max_cols[self.cursor.y]:
       #        self.cursor.x = self.max_cols[self.cursor.y]
       #    #paint.drawRect(3 + self.cursor[0] * self.fontwt, 2 + self.cursor[1] * self.fontht, self.fontwt-1, self.fontht)
       #    paint.drawRect(0 + self.cursor.x * self.fontwt, 5 + self.cursor.y * self.fontht, 0, self.fontht - 3)

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
        total_lines = sum(self.line_heights)#len(self.line_info)
        max_visible_lines = self.geometry().height() / self.fontht
        vmax = max(0, total_lines - max_visible_lines)
        self.getWindow().ui.scrollArea.verticalScrollBar().setMaximum(vmax)
        self.getWindow().ui.scrollArea.verticalScrollBar().setPageStep(1)

    def get_nodesize_in_chars(self, node):
        if node.image:
            w = math.ceil(node.image.width() * 1.0 / self.fontwt)
            h = math.ceil(node.image.height() * 1.0 / self.fontht)
            return NodeSize(w, h)
        else:
            return NodeSize(len(node.symbol.name), 1)

    def paintLinesOld(self, paint, startline):
        import os

        # find proper startline
        total = 0
        real_line = 0
        for h in self.line_heights:
            if total+h > startline:
                break
            total += h
            real_line += 1

        # get all selected magic tokens
        node = self.get_nodes_at_position()[0][0]
        selected_magic = node.magic_parent
        node = node.get_root().get_magicterminal()

        r = min(sum(self.line_heights)-self.viewport_y, (self.geometry().height()/self.fontht))

        # check if the line starts with a partial image
        y = total - startline
        self.paint_start = (real_line, y)
        startline = real_line

        r = min(len(self.line_info)-startline, (self.geometry().height()/self.fontht))

        draw_cursor_at = QRect(0,0,0,0)

        line_range = range(0, r)
        #y = 0
        for i in line_range:
            line = self.line_info[startline + i]
            line_str = []
            styles = []
            x = 0
            y_inc = 1
            # draw cursor
            if (startline + i) == self.cursor.y:
                draw_cursor_at = QRect(0 + self.cursor.x * self.fontwt, 5 + y * self.fontht, 0, self.fontht - 3)
            for node in line:
                if isinstance(node, BOS):
                    continue
                if isinstance(node, EOS):
                    continue
                if node.lookup == "<return>":
                    y += y_inc
                    continue
                text = node.symbol.name
                if isinstance(node, ImageNode):
                    node = node.node
                    paint.drawImage(QPoint(x, 3 + y * self.fontht), node.image)
                    x += math.ceil(node.image.width() * 1.0 / self.fontwt) * self.fontwt
                    y_inc = max(y_inc, math.ceil(node.image.height() * 1.0 / self.fontht))
                    continue
                if self.getWindow().ui.cbShowLangBoxes.isChecked() or node.magic_parent is selected_magic:
                    try:
                        color_id = self.magic_tokens.index(id(node.magic_parent))
                        paint.fillRect(QRectF(x,3 + self.fontht + y*self.fontht, len(text)*self.fontwt, -self.fontht+2), self.nesting_colors[color_id % 5])
                    except ValueError:
                        pass
                paint.drawText(QtCore.QPointF(x, self.fontht + y*self.fontht), text)
                x += len(text)*self.fontwt
            if i >= 0:
                self.max_cols.append(x/self.fontwt)
                self.line_widths[startline + i] = x / self.fontwt
        paint.drawRect(draw_cursor_at)


    # paint lines using new line manager
    def paintLines(self, paint, startline):

        # find internal line corresponding to visual line
        visual_line = 0
        internal_line = 0
        for l in self.lines:
            if visual_line + l.height > startline:
                break
            visual_line += l.height
            internal_line += 1

        x = 0
        y = -visual_line # start drawing outside of viewport to display partial images
        node = self.lines[visual_line].node

        self.paint_start = (internal_line, y)

        max_y = self.geometry().height()/self.fontht

        line = internal_line

        self.paint_nodes(paint, node, x, y, line, max_y)

    def paint_nodes(self, paint, node, x, y, line, max_y, lbox=0):
        self.lines[line].height = 1 # reset height
        while y < max_y:

            # draw language boxes
            if lbox > 0:
                color = self.nesting_colors[lbox % 5]
                paint.fillRect(QRectF(x,3 + self.fontht + y*self.fontht, len(node.symbol.name)*self.fontwt, -self.fontht+2), color)

            # draw node
            dx, dy = self.paint_node(paint, node, x, y)
            x += dx
            #y += dy
            self.lines[line].height = max(self.lines[line].height, dy)

            # after we drew a return, update line width
            if node.lookup == "<return>":
                self.lines[line].width = x / self.fontwt
                x = 0
                y += self.lines[line].height
                line += 1
                self.lines[line].height = 1 # reset height

            # draw cursor
            if line == self.cursor.y:
                draw_cursor_at = QRect(0 + self.cursor.x * self.fontwt, 5 + y * self.fontht, 0, self.fontht - 3)
                paint.drawRect(draw_cursor_at)

            node = node.next_term

            # if we found a language box, continue drawing inside of it
            if isinstance(node.symbol, MagicTerminal):
                x, y, line = self.paint_nodes(paint, node.symbol.ast.children[0], x, y, line, max_y, lbox+1)
                node = node.next_term

            # if we reached EOS we can stop drawing
            if isinstance(node, EOS):
                self.lines[line].width = x / self.fontwt
                break
        return x, y, line

    def paint_node(self, paint, node, x, y):
        dx, dy = (0, 0)
        if node.symbol.name == "\r" or isinstance(node, EOS):
            return dx, dy
        if node.image is not None and not node.plain_mode:
            paint.drawImage(QPoint(x, 3 + y * self.fontht), node.image)
            dx = math.ceil(node.image.width() * 1.0 / self.fontwt) * self.fontwt
            dy = math.ceil(node.image.height() * 1.0 / self.fontht)
        elif isinstance(node, TextNode):
            text = node.symbol.name
            paint.drawText(QtCore.QPointF(x, self.fontht + y*self.fontht), text)
            dx = len(text) * self.fontwt
            dy = 0
        return dx, dy

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
            width = end.self.cursor.x, self.curspr.y - self.viewport_sx
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

    def get_relative_cursor(self):
        return Cursor(self.cursor.x, self.cursor.y - self.viewport_y)

    def document_y(self):
        return self.cursor.y
        #return self.get_real_line(self.viewport_y + self.cursor.y)

    def get_real_line(self, y):
        total = 0
        real_line = 0
        for i in self.line_heights:
            if total+i > y:
                break
            total += i
            real_line += 1
        return real_line

    def get_selected_node(self):
        node, _, _ = self.get_nodes_at_position()
        return node

    def get_nodes_at_position(self):
        node = self.lines[self.cursor.y].node
        x = 0
        node, x = self.find_node_at_position(x, node)

        if self.edit_rightnode:
            node = node.next_term
            # node is last in language box -> select next node outside magic box
            if isinstance(node, EOS):
                root = node.get_root()
                lbox = root.get_magicterminal()
                if lbox:
                    node = lbox
            # node is language box
            elif isinstance(node.symbol, MagicTerminal):
                node = node.symbol.ast.children[0]
        if x == self.cursor.x:
            inside = False
        else:
            inside = True
        return node, inside, x

    def find_node_at_position(self, x, node):
        while x < self.cursor.x:
            node = node.next_term
            if isinstance(node, EOS):
                return None, x
            if isinstance(node.symbol, MagicTerminal):
                found, x = self.find_node_at_position(x, node.symbol.ast.children[0])
                if found is not None:
                    node = found
                    break
                else:
                    continue
            if node.image is None or node.plain_mode:
                x += len(node.symbol.name)
            else:
                x += math.ceil(node.image.width() * 1.0 / self.fontwt)
        return node, x

    def get_nodes_at_position_line_representation(self):
        y = self.cursor.y#self.document_y()
        line = self.line_info[y]
        inbetween = False
        x = 0
        if self.cursor.x == 0 and y > 0:# and not isinstance(line[0], BOS):
            node = self.line_info[y-1][-1]
            i = 2
            while isinstance(node, ImageNode):
                node = self.line_info[y-i][-1]
                i+=1
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
        return ([node, node.next_terminal()], inbetween, x)

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
            self.fix_cursor_on_image()
            self.selection_start = self.cursor.copy()
            self.selection_end = self.cursor.copy()

            selected_node, _, _ = self.get_nodes_at_position()
            self.getWindow().btReparse(selected_node)

            root = selected_node.get_root()
            lrp = self.parsers[root]
            self.getWindow().showLookahead(lrp)
            self.update()

    def mouseDoubleClickEvent(self, e):
        if e.button() == Qt.LeftButton:
            self.cursor = self.coordinate_to_cursor(e.x(), e.y())
            selected_node, _, _ = self.get_nodes_at_position()
            if selected_node.image is None:
                return

            self.fix_cursor_on_image()
            if selected_node.image is not None:
                selected_node.plain_mode = True
                self.cursor.x -= math.ceil(selected_node.image.width() * 1.0 / self.fontwt)
                self.cursor.x += len(selected_node.symbol.name)
                self.update()


    def fix_cursor_on_image(self):
        node, _, x = self.get_nodes_at_position()
        if node.image and not node.plain_mode:
            self.cursor.x = x

    def coordinate_to_cursor(self, x, y):
        result = Cursor(0,0)

        mouse_y = y / self.fontht
        first_line = self.paint_start[0]
        y_offset = self.paint_start[1]

        y = y_offset
        line = first_line
        while line < len(self.lines) - 1:
            y += self.lines[line].height
            if y > mouse_y:
                break
            line += 1
        result.y = line

        cursor_x = x / self.fontwt

        if cursor_x < 0:
            result.x = 0
        elif cursor_x <= self.lines[result.y].width:
            result.x = cursor_x
        else:
            result.x = self.lines[result.y].width

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

        if e.key() in [Qt.Key_Shift, Qt.Key_Alt, Qt.Key_Control, Qt.Key_Meta]:
            return

        selected_node, inbetween, x = self.get_nodes_at_position()

        text = e.text()
        self.changed_line = self.document_y()

        self.edit_rightnode = False # has been processes in get_nodes_at_pos -> reset

        if e.key() == Qt.Key_Escape:
            self.key_escape(e, selected_node)
        elif e.key() == Qt.Key_Backspace:
            self.key_backspace(e)
        elif e.key() in [Qt.Key_Up, Qt.Key_Down, Qt.Key_Left, Qt.Key_Right]:
            self.key_cursors(e)
        elif e.key() == Qt.Key_Home:
            self.cursor.x = 0
        elif e.key() == Qt.Key_End:
            self.cursor.x = self.lines[self.cursor.y].width
        elif e.key() == Qt.Key_C and e.modifiers() == Qt.ControlModifier:
            self.copySelection()
        elif e.key() == Qt.Key_V and e.modifiers() == Qt.ControlModifier:
            self.pasteSelection()
        elif e.key() == Qt.Key_X and e.modifiers() == Qt.ControlModifier:
            if self.hasSelection():
                self.copySelection()
                self.deleteSelection()
        elif e.key() == Qt.Key_Space and e.modifiers() == Qt.ControlModifier:
            self.key_ctrl_space(e, selected_node, inbetween, x)
        elif e.key() == Qt.Key_Space and e.modifiers() == Qt.ControlModifier | Qt.ShiftModifier:
            self.edit_rightnode = True # writes next char into magic ast
            self.update()
            return
        elif e.key() == Qt.Key_Delete:
            self.key_delete(e, selected_node, inbetween, x)
        else:
            indentation = self.key_normal(e, selected_node, inbetween, x)

        #self.rescan_line(self.changed_line)
        self.rescan_linebreaks(self.changed_line)
        self.getWindow().btReparse([])
        self.repaint() # this recalculates self.max_cols

        if e.key() == Qt.Key_Return:
            self.cursor_movement(Qt.Key_Down)
            self.cursor.x = indentation

        self.fix_cursor_on_image()

        root = selected_node.get_root()
        lrp = self.parsers[root]
        self.getWindow().showLookahead(lrp)
        self.update()

    def key_escape(self, e, node):
        if node.plain_mode:
            node.plain_mode = False
            self.fix_cursor_on_image()
            self.update()

    def key_ctrl_space(self, e, node, inside, x):
        self.showSubgrammarMenu()
        if self.sublanguage:
            newnode = self.add_magic()
            self.edit_rightnode = True # writes next char into magic ast
            if not inside:
                node.insert_after(newnode)
            else:
                node = node
                internal_position = len(node.symbol.name) - (x - self.cursor.x)
                text1 = node.symbol.name[:internal_position]
                text2 = node.symbol.name[internal_position:]
                node.symbol.name = text1
                node.insert_after(newnode)

                node2 = TextNode(Terminal(text2))
                newnode.insert_after(node2)

                self.relex(node)
                self.relex(node2)

    def key_backspace(self, e):
        if self.document_y() > 0 and self.cursor.x == 0:
            self.cursor_movement(Qt.Key_Up)
            self.repaint() # XXX store line width in line_info to avoid unnecessary redrawing
            self.cursor.x = self.lines[self.cursor.y].width
        elif self.cursor.x > 0:
            self.cursor.x -= 1
        event = QKeyEvent(QEvent.KeyPress, Qt.Key_Delete, e.modifiers(), e.text())
        self.keyPressEvent(event)


    def key_delete(self, e, node, inside, x):
        if self.hasSelection():
            self.deleteSelection()
            return

        if inside: # cursor inside a node
            internal_position = len(node.symbol.name) - (x - self.cursor.x)
            self.last_delchar = node.backspace(internal_position)
            self.relex(node)
        else: # between two nodes
            node = node.next_terminal() # delete should edit the node to the right from the selected node
            # if lbox is selected, select first node in lbox
            if isinstance(node.symbol, MagicTerminal) or isinstance(node, EOS):
                bos = node.symbol.ast.children[0]
                self.key_delete(e, bos, inside, x)
                return
            if node.image and not node.plain_mode:
                return
            if node.symbol.name == "\r":
                self.delete_linebreak(self.changed_line, node)
            self.last_delchar = node.backspace(0)

            # if node is empty, delete it and repair previous/next node
            if node.symbol.name == "" and not isinstance(node, BOS):
               # for all current languages we are using, deleting a node
               # shouldn't change how nodes are lexed

                root = node.get_root()
                magic = root.get_magicterminal()
                next_node = node.next_terminal()
                previous_node = node.previous_terminal()
                if magic and isinstance(next_node, EOS) and isinstance(previous_node, BOS):
                    # language box is empty -> delete it and all references
                    magic.parent.remove_child(magic)
                    self.magic_tokens.remove(id(magic))
                    del self.parsers[root]
                    del self.lexers[root]
                else:
                    # normal node is empty -> remove it from AST
                    node.parent.remove_child(node)

    def key_cursors(self, e):
        self.edit_rightnode = False
        self.cursor_movement(e.key())
        self.update()
        selected_node, _, _ = self.get_nodes_at_position()
        self.getWindow().showAst(selected_node)

        # update lookahead when moving cursors
        root = selected_node.get_root()
        lrp = self.parsers[root]
        self.getWindow().showLookahead(lrp)

    def key_home(self, e):
        self.cursor.x = 0

    def key_end(self, e):
        self.cursor.x = self.line_widths[self.cursor.y]

    def key_normal(self, e, node, inside, x):
        indentation = 0
        # modify text
        if e.key() == Qt.Key_Tab:
            text = "    "
        else:
            text = e.text()
            if self.hasSelection():
                self.deleteSelection()
            if e.key() == Qt.Key_Return:
                if self.indentation:
                    indentation = self.get_indentation(self.document_y())
                    text += " " * indentation
        # edit node
        if inside:
            internal_position = len(node.symbol.name) - (x - self.cursor.x)
            node.insert(text, internal_position)
        else:
            # append to node: [node newtext] [next node]
            pos = 0
            if isinstance(node, BOS) or node.symbol.name == "\r" or isinstance(node.symbol, MagicTerminal):
                # insert new node: [bos] [newtext] [next node]
                old = node
                node = TextNode(Terminal(""))
                old.insert_after(node)
            else:
                pos = len(node.symbol.name)
            node.insert(text, pos)

        if e.key() == Qt.Key_Tab:
            self.cursor.x += 4
        else:
            self.cursor.x += 1

        self.relex(node)
        return indentation

    def delete_linebreak(self, y, node):
        current = self.lines[y].node
        deleted = self.lines[y+1].node
        assert deleted is node
        del self.lines[y+1]

        # XXX adjust line_height

    def rescan_linebreaks(self, y):
        """ Scan all nodes between this return node and the next lines return
        node. All other return nodes you find that are not the next lines
        return node are new and must be inserted into self.lines """

        current = self.lines[y].node
        try:
            next = self.lines[y+1].node #XXX last line has eos -> create line manager class
        except IndexError:
            next = self.eos

        current = current.next_term
        while current is not next:
            if current.symbol.name == "\r":
                y += 1
                self.lines.insert(y, Line(current))
            current = current.next_term

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

       #while not isinstance(endnode, EOS) and endnode.symbol.name != "\r":
       #    print("go one")
       #    endnode = endnode.next_term
       #    print(endnode)

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
                del self.line_heights[y+i]
            except IndexError:
                endnode = self.ast.parent.children[-1]

        # last line -> endnode = EOS
        if y == len(self.line_info)-1:
            endnode = self.ast.parent.children[-1]

        node = startnode

        new_list = []
        line_height = 1

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
                if node.image:
                    node = ImageNode(node, 0)
                    image_line_height = int(math.ceil(node.image.height() * 1.0 / self.fontht))
                    line_height = max(line_height, image_line_height)

            new_list.append(node)
            if node.lookup == "<return>":
                self.line_info[y] = new_list
                self.fix_indentation(y)
                self.line_heights[y] = line_height
                new_list = []
                line_height = 1
                y += 1
                self.line_info.insert(y, [])
                self.line_heights.insert(y, 1)
                self.line_indents.insert(y, None)
            node = node.next_terminal()
        new_list.append(endnode)
        self.line_info[y] = new_list
        self.fix_indentation(y)
        self.line_heights[y] = line_height

    def relex(self, startnode):
        # XXX when typing to not create new node but insert char into old node
        #     (saves a few insertions and is easier to lex)

        root = startnode.get_root()
        lexer = self.lexers[root]
        lexer.relex(startnode)
        return

    def fix_indentation(self, y):
        line = self.line_info[y]
        first_token = line[0]
        last_token = line[-1]
        last_token.linenr = y

        if first_token.lookup == "<return>":
            self.line_indents[y] = None
        elif first_token.lookup == "<ws>":
            next_token = first_token.next_term
            if next_token.lookup not in ["<return>","<ws>"]:
                self.line_indents[y] = len(first_token.symbol.name)
            else:
                self.line_indents[y] = None
        else:
            self.line_indents[y] = 0

        return
        # old stuff
        last_token = self.line_info[y] # is either a newline or eos
        assert isinstance(last_token, EOS) or last_token.lookup == "<return>"

        if isinstance(last_token, EOS):
            # dedent everything
            return

        next_token = last_token.next_term
        if next_token.lookup == "<ws>" and next_token.next_term.lookup not in ["<ws>", "<return>"]:
            spaces = len(next_token.symbol.name)
            indentation = space - sum(last_token.indent_stack)
            # copy
        return

        if first_token.lookup == "<ws>":
            next_token = first_token.next_term
            if next_token.lookup not in ["<ws>", "<return>"]:
                first_token.lookup = "INDENT"

    def add_magic(self):
        # Create magic token
        magictoken = self.create_node("<%s>" % self.sublanguage.name, magic=True)

        # Create parser, priorities and lexer
        parser = IncParser(self.sublanguage.grammar, 1, True)
        parser.init_ast(magictoken)
        lexer = IncrementalLexer(self.sublanguage.priorities, self.sublanguage.name)
        self.magic_tokens.append(id(magictoken))
        root = parser.previous_version.parent
        root.magic_backpointer = magictoken
        self.parsers[root] = parser
        self.lexers[root] = lexer
        self.parser_langs[root] = self.sublanguage.name

        magictoken.symbol.parser = root
        magictoken.symbol.ast = root
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
            lexer = self.lexers[root]
            text = new_node.symbol.name
            match = lexer.lex(text)[0]
            new_node.lookup = match[1]
            #new_node.regex = pl.regex(text)
            #new_node.priority = pl.priority(text)
            #new_node.lookup = pl.name(text)

    def cursor_movement(self, key):
        cur = self.cursor

        if key == QtCore.Qt.Key_Up:
            if self.cursor.y > 0:
                self.cursor.y -= 1
                if self.cursor.x > self.lines[cur.y].width:
                    self.cursor.x = self.lines[cur.y].width
            else:
                self.getWindow().ui.scrollArea.decVSlider()
        elif key == QtCore.Qt.Key_Down:
            if self.cursor.y < len(self.lines) - 1:
                self.cursor.y += 1
                if self.cursor.x > self.lines[cur.y].width:
                    self.cursor.x = self.lines[cur.y].width
            else:
                self.getWindow().ui.scrollArea.incVSlider()
        elif key == QtCore.Qt.Key_Left:
            if self.cursor.x > 0:
                node = self.get_selected_node()
                if node.image and not node.plain_mode:
                    s = self.get_nodesize_in_chars(node)
                    self.cursor.x -= s.w
                else:
                    self.cursor.x -= 1
        elif key == QtCore.Qt.Key_Right:
            if self.cursor.x < self.lines[cur.y].width:
                self.cursor.x += 1
                node = self.get_selected_node()
                if node.image and not node.plain_mode:
                    s = self.get_nodesize_in_chars(node)
                    self.cursor.x += s.w - 1
        self.fix_cursor_on_image()

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
        self.line_heights = []
        self.cursor = Cursor(0,0)
        self.viewport_y = 0
        for node in list(self.parsers):
            if node is not self.ast.parent:
                del self.parsers[node]
                del self.lexers[node]
                del self.parser_langs[node]
                self.magic_tokens = []
        # convert linebreaks
        text = text.replace("\r\n","\r")
        parser = list(self.parsers.values())[0]
        lexer = list(self.lexers.values())[0]
        # lex text into tokens
        new = TextNode(Terminal("text"))
        lexer.relex(new)
        return
        assert False
        success = lexer.lex(text)
        # reset tree
        bos = parser.previous_version.parent.children[0]
        eos = parser.previous_version.parent.children[-1]
        parser.previous_version.parent.children = [bos, eos]
        # insert tokens into tree
        parent = parser.previous_version.parent
        eos = parent.children.pop()
        last_node = parser.previous_version.get_bos()
        line_nodes = [last_node]
        for match in success:
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
                self.line_heights.append(1)
                line_nodes = []
                self.node_list.insert(1, node)

            last_node = node
        self.line_info.append(line_nodes) #add last line
        self.line_heights.append(1)
        self.line_info[-1].append(eos)
        parent.children.append(eos)
        node.right = eos # link to eos
        node.next_term = eos
        eos.left = node
        eos.prev_term = node
        node.mark_changed()

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
            # create tokenlexer
            lexer = IncrementalLexer(lang.priorities)
            self.lexers[node] = lexer
            # load language
            self.parser_langs[node] = p[node]
            if node is main_lang:
                self.ast = parser.previous_version
            if node.get_magicterminal():
                self.magic_tokens.append(id(node.get_magicterminal()))
        node = self.ast.parent
        self.line_info.append([node.children[0], node.children[-1]])
        self.line_heights.append(1)
        self.rescan_line(0)

class Cursor(object):
    def __init__(self, pos, line):
        self.x = pos
        self.y = line

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
        lexer = IncrementalLexer(new_priorities)
        self.ui.frame.reset()
        self.ui.frame.set_mainlanguage(self.lrp, lexer, self.main_language)
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
            status = self.ui.frame.parsers[key].inc_parse(self.ui.frame.line_indents)
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
