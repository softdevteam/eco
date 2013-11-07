# Copyright (c) 2012--2013 King's College London
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

from __future__ import print_function

import subprocess, sys
from PyQt4 import QtCore
from PyQt4.QtCore import *
from PyQt4 import QtGui
from PyQt4.QtGui import *

try:
    import cPickle as pickle
except:
    import pickle

from gui.gui import Ui_MainWindow
from gui.parsetree import Ui_MainWindow as Ui_ParseTree
from gui.stateview import Ui_MainWindow as Ui_StateView
from gui.about import Ui_Dialog as Ui_AboutDialog

from grammar_parser.plexer import PriorityLexer
from incparser.incparser import IncParser
from inclexer.inclexer import IncrementalLexer
from viewer import Viewer

from grammar_parser.gparser import Terminal, MagicTerminal, IndentationTerminal, Nonterminal

from incparser.astree import TextNode, BOS, EOS, ImageNode, FinishSymbol

from grammars.grammars import languages, lang_dict

from time import time
import os
import math

import syntaxhighlighter
from jsonmanager import JsonManager

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
        self.indent_stack = None
        self.indentation = 0

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

        self.infofont = QtGui.QFont('Courier', 6)
        self.infofontht = QtGui.QFontMetrics(self.infofont).height() + 3
        self.infofontwt = QtGui.QFontMetrics(self.infofont).width(" ")

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
        self.max_cols = []

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

        self.selected_lbox = None

    def reset(self):
        self.indentations = {}
        self.max_cols = []
        self.cursor = Cursor(0,0)
        self.update()
        self.line_info = []
        self.line_heights = []
        self.line_indents = []
        self.lines = []
        self.selected_lbox = None

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

        first_line = Line(self.ast.parent.children[0], 1)
        first_line.indent_stack = [0]
        self.lines.append(first_line)
        self.eos = self.ast.parent.children[-1]

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
        self.update()

    def sliderXChanged(self, value):
        self.move(-value*self.fontwt,0)
        self.resize(self.parentWidget().geometry().width() + value*self.fontwt, self.geometry().height())
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
        self.max_cols = []
        self.longest_column = 0

        # calculate how many lines we need to show
        self.init_height = self.geometry().height()

        self.paintLines(paint, self.viewport_y)

        paint.end()

        self.getWindow().ui.scrollArea.verticalScrollBar().setMinimum(0)
        total_lines = 0
        max_width = 0
        for l in self.lines:
            total_lines += l.height
            max_width = max(max_width, l.width)
        max_visible_lines = self.geometry().height() / self.fontht
        vmax = max(0, total_lines - max_visible_lines)
        self.getWindow().ui.scrollArea.verticalScrollBar().setMaximum(vmax)
        self.getWindow().ui.scrollArea.verticalScrollBar().setPageStep(1)

        current_width = self.parentWidget().geometry().width() / self.fontwt
        hmax = max(0, max_width - current_width)
        self.getWindow().ui.scrollArea.horizontalScrollBar().setMaximum(hmax)
        self.getWindow().ui.scrollArea.horizontalScrollBar().setPageStep(1)

    def get_nodesize_in_chars(self, node):
        if node.image:
            w = math.ceil(node.image.width() * 1.0 / self.fontwt)
            h = math.ceil(node.image.height() * 1.0 / self.fontht)
            return NodeSize(w, h)
        else:
            return NodeSize(len(node.symbol.name), 1)

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
        y = visual_line - startline # start drawing outside of viewport to display partial images
        self.paint_start = (internal_line, y)

        max_y = self.geometry().height()/self.fontht

        line = internal_line
        node = self.lines[line].node
        if node.symbol.name == "\r":
            node = node.next_term # ignore \r if it is startnode


        self.paint_nodes(paint, node, x, y, line, max_y)

        #self.paintSelection(paint, visual_line)

    #XXX if starting node is inside language box, init lbox with amout of languge boxes
    def paint_nodes(self, paint, node, x, y, line, max_y, lbox=0):
        selected_language = self.ast.parent

        highlighter = self.get_highlighter(node)
        selection_start = min(self.selection_start, self.selection_end)
        selection_end = max(self.selection_start, self.selection_end)
        start_lbox = self.get_languagebox(node)
        if start_lbox and self.selected_lbox is start_lbox:
            lbox += 1
            draw_lbox = True
        else:
            draw_lbox = False
        self.lines[line].height = 1 # reset height
        draw_cursor = True
        while y < max_y:

            # if we found a language box, continue drawing inside of it
            if isinstance(node.symbol, MagicTerminal):
                lbox += 1
                lbnode = node.symbol.ast
                if self.selected_lbox is node:
                    draw_lbox = True
                    selected_language = lbnode
                else:
                    draw_lbox = False
                node = lbnode.children[0]
                highlighter = self.get_highlighter(node)
                continue

            if isinstance(node, EOS):
                self.draw_selection(paint, node, line, selection_start, selection_end, y)
                lbnode = self.get_languagebox(node)
                if lbnode:
                    lbox -= 1
                    node = lbnode.next_term
                    highlighter = self.get_highlighter(node)
                    if self.selected_lbox is lbnode:
                        draw_lbox = False
                    lbnode = self.get_languagebox(node)
                    if lbnode and self.selected_lbox is lbnode:
                        draw_lbox = True
                    continue
                else:
                    self.lines[line].width = x / self.fontwt
                    break

            # draw language boxes
            if lbox > 0 and draw_lbox:
                #color = self.nesting_colors[lbox % 5]
                color = QColor(0,0,0,30)
                if node.symbol.name != "\r":
                    if not node.image or node.plain_mode:
                        paint.fillRect(QRectF(x,3 + y*self.fontht, len(node.symbol.name)*self.fontwt, self.fontht), color)

            # draw node
            dx, dy = self.paint_node(paint, node, x, y, highlighter)
            x += dx
            #y += dy
            self.lines[line].height = max(self.lines[line].height, dy)

            self.draw_selection(paint, node, line, selection_start, selection_end, y)

            # after we drew a return, update line information
            if node.lookup == "<return>":
                # draw lbox to end of line
                if draw_lbox:
                    paint.fillRect(QRectF(x,3+y*self.fontht, self.geometry().width()-x, self.fontht), color)

                self.lines[line].width = x / self.fontwt
                x = 0
                y += self.lines[line].height
                line += 1
                self.lines[line].height = 1 # reset height

            # draw cursor
            if line == self.cursor.y and x/self.fontwt >= self.cursor.x and draw_cursor:
                draw_cursor_at = QRect(0 + self.cursor.x * self.fontwt, 5 + y * self.fontht, 0, self.fontht - 3)
                paint.drawRect(draw_cursor_at)

                # set lbox info coordinates
                infobox_coordinates = (self.cursor.x * self.fontwt, (y+1) * self.fontht)
                draw_cursor = False

            node = node.next_term

        # paint infobox
        if False:
            lang_name = self.parser_langs[selected_language]
            lang_status = self.parsers[selected_language].last_status
            if lang_status is True:
                color = QColor(100,255,100)
            else:
                color = QColor(255,100,100)
            paint.setFont(self.infofont)
            paint.fillRect(QRect(infobox_coordinates[0], 5 + infobox_coordinates[1], len(lang_name)*self.infofontwt, self.infofontht), color)
            paint.drawText(QtCore.QPointF(infobox_coordinates[0], -3 + self.fontht + infobox_coordinates[1]), lang_name)
            paint.setFont(self.font)

        return x, y, line

    def draw_selection(self, paint, node, line, selection_start, selection_end, y):
        # draw selection
        if node.lookup == "<return>" or node is self.eos:
            if line >= selection_start.y and line <= selection_end.y:
                if line == selection_start.y:
                    draw_start = selection_start.x
                else:
                    draw_start = 0
                if line < selection_end.y:
                    draw_len = self.lines[line].width - draw_start
                else:
                    draw_len = selection_end.x - draw_start
                paint.fillRect(QRectF(draw_start*self.fontwt, 3+y*self.fontht, draw_len*self.fontwt, self.fontht), QColor(0,0,255,100))

    def paint_node(self, paint, node, x, y, highlighter):
        dx, dy = (0, 0)
        if node.symbol.name == "\r" or isinstance(node, EOS) or isinstance(node.symbol, IndentationTerminal):
            return dx, dy
        if node.image is not None and not node.plain_mode:
            paint.drawImage(QPoint(x, 3 + y * self.fontht), node.image)
            dx = int(math.ceil(node.image.width() * 1.0 / self.fontwt) * self.fontwt)
            dy = int(math.ceil(node.image.height() * 1.0 / self.fontht))
        elif isinstance(node, TextNode):
            paint.setPen(QPen(QColor(highlighter.get_color(node))))
            text = node.symbol.name
            paint.drawText(QtCore.QPointF(x, self.fontht + y*self.fontht), text)
            dx = len(text) * self.fontwt
            dy = 0
        return dx, dy

    def get_highlighter(self, node):
        root = node.get_root()
        base = lang_dict[self.parser_langs[root]].base
        return syntaxhighlighter.get_highlighter(base)

    def paintSelection(self, paint, offset):
        start = min(self.selection_start, self.selection_end).copy()
        end = max(self.selection_start, self.selection_end).copy()
        start.y -= offset
        end.y -= offset
        if start.y == end.y:
            width = end.x - start.x
            paint.fillRect(start.x * self.fontwt, 4+start.y * self.fontht, width * self.fontwt, self.fontht, QColor(0,0,255,100))
        else:
            # paint start to line end
            width = self.lines[start.y].width - start.x
            paint.fillRect(start.x * self.fontwt, 4+start.y * self.fontht, width * self.fontwt, self.fontht, QColor(0,0,255,100))

            # paint lines in between
            for y in range(start.y+1, end.y):
                width = self.lines[y].width
                paint.fillRect(0 * self.fontwt, 4+y * self.fontht, width * self.fontwt, self.fontht, QColor(0,0,255,100))

            # paint line start to end
            width = end.x
            paint.fillRect(0 * self.fontwt, 4+end.y * self.fontht, width * self.fontwt, self.fontht, QColor(0,0,255,100))


    def get_indentation(self, y):
        node = self.lines[y].node
        node = node.next_term
        while isinstance(node.symbol, IndentationTerminal):
            node = node.next_term
        if node.lookup == "<ws>":
            return len(node.symbol.name)
        return 0

    def document_y(self):
        return self.cursor.y

    def get_selected_node(self):
        node, _, _ = self.get_nodes_at_position()
        return node

    def get_languagebox(self, node):
        root = node.get_root()
        lbox = root.get_magicterminal()
        return lbox

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

        # check lbox
        self.selected_lbox = self.get_languagebox(node)

        return node, inside, x

    def find_node_at_position(self, x, node):
        while x < self.cursor.x:
            node = node.next_term
            if isinstance(node, EOS):
                root = node.get_root()
                lbox = root.get_magicterminal()
                if lbox:
                    node = lbox
                    continue
                else:
                    return None, x
            if isinstance(node.symbol, IndentationTerminal):
                continue
            if isinstance(node.symbol, MagicTerminal):
                node = node.symbol.ast.children[0]
            if node.image is None or node.plain_mode:
                x += len(node.symbol.name)
            else:
                x += math.ceil(node.image.width() * 1.0 / self.fontwt)

        return node, x

    def get_nodes_from_selection(self):
        cur_start = min(self.selection_start, self.selection_end)
        cur_end = max(self.selection_start, self.selection_end)

        if cur_start == cur_end:
            return

        temp = self.cursor

        self.cursor = cur_start
        start_node, start_inbetween, start_x = self.get_nodes_at_position()
        diff_start = 0
        if start_inbetween:
            diff_start = len(start_node.symbol.name) - (start_x - self.cursor.x)
            include_start = True
        else:
            include_start = False

        self.cursor = cur_end
        end_node, end_inbetween, end_x = self.get_nodes_at_position()
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

    def focusNextPrevChild(self, b):
        # don't switch to next widget on TAB
        return False

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
            if selected_node.plain_mode is False:
                selected_node.plain_mode = True
                self.cursor.x -= math.ceil(selected_node.image.width() * 1.0 / self.fontwt)
                self.cursor.x += len(selected_node.symbol.name)
                self.update()
            else:
                selected_node.plain_mode = False
                self.fix_cursor_on_image()
                self.update()


    def fix_cursor_on_image(self):
        node, _, x = self.get_nodes_at_position()
        if node.image and not node.plain_mode:
            self.cursor.x = x

    def cursor_to_coordinate(self):
        y = 0
        for l in self.lines[:self.cursor.y]:
            y += l.height * self.fontht
        x = self.cursor.x * self.fontwt
        y = y - self.getWindow().ui.scrollArea.verticalScrollBar().value() * self.fontht
        return (x,y)

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

    def XXXkeyPressEvent(self, e):
        import cProfile
        cProfile.runctx("self.linkkeyPressEvent(e)", globals(), locals())

    def keyPressEvent(self, e):

        if e.key() in [Qt.Key_Shift, Qt.Key_Alt, Qt.Key_Control, Qt.Key_Meta, Qt.Key_AltGr]:
            if e.key() == Qt.Key_Shift:
                # start selection
                self.selection_start = self.cursor.copy()
                self.selection_end = self.cursor.copy()
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
            if e.modifiers() == Qt.ShiftModifier:
                self.selection_end = self.cursor.copy()
            else:
                self.selection_start = self.cursor.copy()
                self.selection_end = self.cursor.copy()
        elif e.key() == Qt.Key_Home:
            self.cursor.x = 0
        elif e.key() == Qt.Key_End:
            self.cursor.x = self.lines[self.cursor.y].width
        elif e.key() == Qt.Key_C and e.modifiers() == Qt.ControlModifier:
            self.copySelection()
        elif e.key() == Qt.Key_V and e.modifiers() == Qt.ControlModifier:
            if self.hasSelection():
                self.deleteSelection()
            self.pasteSelection(selected_node, inbetween, x)
        elif e.key() == Qt.Key_X and e.modifiers() == Qt.ControlModifier:
            if self.hasSelection():
                self.copySelection()
                self.deleteSelection()
        elif e.key() == Qt.Key_Space and e.modifiers() == Qt.ControlModifier:
            if self.hasSelection():
                self.surround_with_lbox(e, selected_node, inbetween, x)
            else:
                self.key_ctrl_space(e, selected_node, inbetween, x)
        elif e.key() == Qt.Key_Space and e.modifiers() == Qt.ControlModifier | Qt.ShiftModifier:
            self.edit_rightnode = True # writes next char into magic ast
            self.get_nodes_at_position()
            self.update()
            return
        elif e.key() == Qt.Key_Delete:
            self.key_delete(e, selected_node, inbetween, x)
        else:
            indentation = self.key_normal(e, selected_node, inbetween, x)

        lines_before = len(self.lines)
        self.rescan_linebreaks(self.changed_line)
        new_lines = len(self.lines) - lines_before
        for i in range(new_lines+1):
            self.rescan_indentations(self.changed_line+i)
        self.getWindow().btReparse([])
        #self.repaint() # this recalculates self.max_cols #XXX deprecated!?

        if e.key() == Qt.Key_Return:
            self.cursor_movement(Qt.Key_Down)
            self.cursor.x = indentation

        self.fix_cursor_on_image()

        root = selected_node.get_root()
        if root in self.parsers:
            lrp = self.parsers[root]
        else:
            selected_node = self.get_selected_node()
            root = selected_node.get_root()
            lrp = self.parsers[root]
        self.getWindow().showLookahead(lrp)
        self.fix_scrollbars()
        self.update()

    def println(self, prestring, y):
        node = self.lines[y].node.next_term
        x = []
        while node is not None and node.symbol.name != "\r":
            x.append(node.symbol.name)
            node = node.next_term
        print(prestring, "".join(x))

    def key_escape(self, e, node):
        if node.plain_mode:
            node.plain_mode = False
            self.fix_cursor_on_image()
            self.update()

    def surround_with_lbox(self, e, node, inside, x):
        nodes, _, _ = self.get_nodes_from_selection()
        appendnode = nodes[0].prev_term
        self.showSubgrammarMenu()
        self.edit_rightnode = False
        if self.sublanguage:
            # cut text
            self.copySelection()
            self.deleteSelection()
            # create language box
            lbox = self.add_magic()
            # insert text
            newnode = TextNode(Terminal(str(QApplication.clipboard().text())))
            lbox.symbol.ast.children[0].insert_after(newnode)
            self.relex(newnode)
            appendnode.insert_after(lbox)

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
        node = self.get_selected_node()
        if node.image is not None and not node.plain_mode:
            return
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
            if isinstance(node, EOS):
                lbox = self.get_languagebox(node)
                if lbox:
                    node = lbox.next_term
                else:
                    return
            while isinstance(node.symbol, IndentationTerminal):
                node = node.next_term
            if isinstance(node.symbol, MagicTerminal) or isinstance(node, EOS):
                bos = node.symbol.ast.children[0]
                self.key_delete(e, bos, inside, x)
                return
            if node.image and not node.plain_mode:
                return
            if node.symbol.name == "\r":
                self.delete_linebreak(self.changed_line, node)
            self.last_delchar = node.backspace(0)
            repairnode = node

            # if node is empty, delete it and repair previous/next node
            if node.symbol.name == "" and not isinstance(node, BOS):
                repairnode = node.prev_term

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

            if repairnode is not None and not isinstance(repairnode, BOS):
                self.relex(repairnode)

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

    def print_line(self, y):
        current = self.lines[y].node
        while True:
            print(current)
            current = current.next_term
            if current is None:
                return

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
            if isinstance(current.symbol, MagicTerminal):
                current = current.symbol.ast.children[0]
            elif isinstance(current, EOS):
                root = current.get_root()
                lbox = root.get_magicterminal()
                if lbox:
                    current = lbox.next_term
            else:
                current = current.next_term

    def rescan_indentations_nostack(self, y):
        if y == 0:
            return

        newline = self.lines[y].node # get newline node
        node = newline.next_term # get first node in line

        # clean up previous indents/dedents
        while isinstance(node.symbol, IndentationTerminal):
            node.parent.remove_child(node)
            node = node.next_term

        indent_node = node
        if indent_node.lookup != "<ws>":
            return

        root = indent_node.get_root()
        lexer = self.lexers[root]
        if not lexer.is_indentation_based():
            return

        indent_level = len(indent_node.symbol.name)
        previous_indent_level = self.lines[y-1].indentation

        tokens = []
        if indent_level > previous_indent_level:
            # emit indent
            tokens.append(TextNode(IndentationTerminal("INDENT")))
        elif indent_level < previous_indent_level:
            # emit dedents
            current_level = previous_indent_level
            line_nr = y-1
            while previous_indent_level > 0 and previous_indent_level > indent_level and line_nr > 0:
                previous_indent_level = self.lines[line_nr-1]
                if current_level > previous_indent_level:
                    tokens.append(TextNode(IndentationTerminal("DEDENT")))
                current_level = previous_indent_level

        self.lines[y].indentation = indent_level

    def rescan_indentations(self, y):
        before = self.lines[y].indent_stack
        self.repair_indentation(y)
        now = self.lines[y].indent_stack
        if before == now:
            # nothing was changed
            #return
            pass # doing this optimisation kills pasting atm

        # repair succeeding lines until we reach a line that has equal or smaller indentation
        this_indent = now[-1]
        while True:
            y += 1
            if y == len(self.lines):
                break
            self.repair_indentation(y)
            indent = self.lines[y].indent_stack[-1]
            if indent == this_indent:
                if self.is_logical_line(y):
                    break


    def repair_indentation(self, y):
        if y == 0:
            return

        newline = self.lines[y].node # get newline node
        node = newline.next_term # get first node in line

        # clean up previous indents/dedents
        while isinstance(node.symbol, IndentationTerminal):
            node.parent.remove_child(node)
            node = node.next_term

        indent_node = node
        root = indent_node.get_root()
        lexer = self.lexers[root]
        if not lexer.is_indentation_based():
            self.lines[y].indent_stack = list(self.lines[y-1].indent_stack)
            return

        tokens = []
        if not self.is_logical_line(y) and y != len(self.lines)-1: # exception: last line containing eos
            self.lines[y].indent_stack = list(self.lines[y-1].indent_stack)
            return

        if indent_node.lookup != "<ws>":
            indent_level = 0
        else:
            indent_level = len(indent_node.symbol.name)

        previous_indent_stack = self.lines[y-1].indent_stack
        this_indent_stack = list(previous_indent_stack) # copy previous list
        for i in reversed(previous_indent_stack):
            if indent_level > i:
                # push INDENT and return
                this_indent_stack.append(indent_level)
                tokens.append(TextNode(IndentationTerminal("INDENT")))
                break
            if indent_level < i:
                # push DEDENT
                this_indent_stack.pop()
                tokens.append(TextNode(IndentationTerminal("DEDENT")))
                pass
            if indent_level == i:
                # we are done
                break

        tokens.append(TextNode(IndentationTerminal("NEWLINE")))
        for token in tokens:
            newline.insert_after(token)

        self.lines[y].indent_stack = this_indent_stack

        if y == len(self.lines)-1 and not isinstance(indent_node, EOS): # last line
            eos = newline.get_root().children[-1]
            node = eos.prev_term
            while isinstance(node.symbol, IndentationTerminal):
                node.parent.remove_child(node)
                node = node.prev_term
            for i in range(len(this_indent_stack)-1):
                node.insert_after(TextNode(IndentationTerminal("DEDENT")))
            node.insert_after(TextNode(IndentationTerminal("NEWLINE")))

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
            # if we are here, we reached a normal node
            return True

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

    def fix_scrollbars(self):
        x, y = self.cursor_to_coordinate()

        # fix vertical bar
        if y < 0:
            self.getWindow().ui.scrollArea.decVSlider()
        if y+3 > self.geometry().height(): # the 3 is the padding of the canvas
            self.getWindow().ui.scrollArea.incVSlider()

        # fix horizontal bar
        if self.cursor.x < -1 * self.geometry().x() / self.fontwt:
            self.getWindow().ui.scrollArea.decHSlider()
        if self.cursor.x > self.parentWidget().geometry().width()/self.fontwt + self.getWindow().ui.scrollArea.horizontalScrollBar().value():
            self.getWindow().ui.scrollArea.incHSlider()

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
        chars += self.lines[start.y].width - start.x
        chars += 1 # return
        chars += end.x

        for y in range(start.y+1, end.y):
            chars += self.lines[y].width
            chars += 1 # return

        return chars

    def hasSelection(self):
        return self.selection_start != self.selection_end

    def delete_if_empty(self, node):
        if node.symbol.name == "":
            node.parent.remove_child(node)

    def deleteSelection(self):
        #XXX simple version: later we might want to modify the nodes directly
        #nodes, diff_start, diff_end = self.get_nodes_from_selection()

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

    def copySelection(self):
        nodes, diff_start, diff_end = self.get_nodes_from_selection()
        if len(nodes) == 1:
            text = nodes[0].symbol.name[diff_start:diff_end]
            QApplication.clipboard().setText(text)
            return
        text = []
        start = nodes.pop(0)
        end = nodes.pop(-1)

        text.append(start.symbol.name[diff_start:])
        for node in nodes:
            if not isinstance(node.symbol, IndentationTerminal):
                text.append(node.symbol.name)
        text.append(end.symbol.name[:diff_end])
        QApplication.clipboard().setText("".join(text))

    def pasteSelection(self, node, inside, x):
        text = QApplication.clipboard().text()
        text = text.replace("\r\n","\r")
        text = text.replace("\n","\r")
        #self.insertText(text)
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
        text = text.replace("\n","\r")
        parser = list(self.parsers.values())[0]
        lexer = list(self.lexers.values())[0]
        # lex text into tokens
        bos = parser.previous_version.parent.children[0]
        new = TextNode(Terminal(text))
        bos.insert_after(new)
        root = new.get_root()
        lexer = self.lexers[root]
        lexer.relex_import(new)
        self.rescan_linebreaks(0)
        for y in range(len(self.lines)):
            self.repair_indentation(y)
        return

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
        x,y = self.cursor_to_coordinate()
        menu.exec_(self.mapToGlobal(QPoint(0,0)) + QPoint(3 + x, y + self.fontht))

    def createMenuFunction(self, l):
        def action():
            self.sublanguage = l
            self.edit_rightnode = True
        return action

    def selectSubgrammar(self, item):
        pass

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

    def saveToJson(self, filename):
        whitespaces = self.getWindow().ui.cb_add_implicit_ws.isChecked()

        root = self.ast.parent
        language = self.parser_langs[root]
        manager = JsonManager()
        manager.save(self.ast.parent, language, whitespaces, filename)

    def loadFromJson(self, filename):
        manager = JsonManager()
        language_boxes = manager.load(filename)

        #self.ast.parent = root
        #self.lines[0].node = root.children[0]
        #self.eos = root.children[-1]

        # setup main language
        root, language, whitespaces = language_boxes[0]
        grammar = lang_dict[language]
        incparser = IncParser(grammar.grammar, 1, whitespaces)
        incparser.init_ast()
        incparser.previous_version.parent = root
        inclexer = IncrementalLexer(grammar.priorities)
        self.reset()
        self.set_mainlanguage(incparser, inclexer, language)

        # setup language boxes
        for root, language, whitespaces in language_boxes[1:]:
            grammar = lang_dict[language]
            incparser = IncParser(grammar.grammar, 1, whitespaces)
            incparser.init_ast()
            incparser.previous_version.parent = root
            inclexer = IncrementalLexer(grammar.priorities)
            self.parsers[root] = incparser
            self.lexers[root] = inclexer
            self.parser_langs[root] = language

        self.rescan_linebreaks(0)
        for i in range(len(self.lines)):
            self.rescan_indentations(i)
        self.getWindow().btReparse([])

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

    def change_font(self, font):
        self.font = font[0]
        self.fontm = QtGui.QFontMetrics(self.font)
        self.fontht = self.fontm.height() + 3
        self.fontwt = self.fontm.width(" ")

    def export_unipycation(self):
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
        import tempfile
        f = tempfile.mkstemp()
        os.write(f[0],"".join(output))
        os.close(f[0])
        if os.environ.has_key("UNIPYCATION"):
            subprocess.Popen([os.path.join(os.environ["UNIPYCATION"], "pypy/goal/pypy-c"), f[1]])
        else:
            sys.stderr.write("UNIPYCATION environment not set")

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

    def incHSlider(self):
        self.horizontalScrollBar().setSliderPosition(self.horizontalScrollBar().sliderPosition() + self.horizontalScrollBar().singleStep())

    def decHSlider(self):
        self.horizontalScrollBar().setSliderPosition(self.horizontalScrollBar().sliderPosition() - self.horizontalScrollBar().singleStep())

    def incVSlider(self):
        self.verticalScrollBar().setSliderPosition(self.verticalScrollBar().sliderPosition() + self.verticalScrollBar().singleStep())

    def decVSlider(self):
        self.verticalScrollBar().setSliderPosition(self.verticalScrollBar().sliderPosition() - self.verticalScrollBar().singleStep())

class ParseView(QtGui.QMainWindow):
    def __init__(self):
        QtGui.QMainWindow.__init__(self)
        self.ui = Ui_ParseTree()
        self.ui.setupUi(self)

        self.connect(self.ui.cb_fit_ast, SIGNAL("clicked()"), self.refresh)
        self.connect(self.ui.cb_toggle_ast, SIGNAL("clicked()"), self.refresh)
        self.connect(self.ui.cb_toggle_ws, SIGNAL("clicked()"), self.refresh)
        self.connect(self.ui.bt_show_sel_ast, SIGNAL("clicked()"), self.showAstSelection)

        self.viewer = Viewer("pydot")
        self.ui.graphicsView.setRenderHints(QPainter.Antialiasing | QPainter.SmoothPixmapTransform | QPainter.TextAntialiasing)

    def setEditor(self, editor):
        self.editor = editor

    def refresh(self):
        whitespaces = self.ui.cb_toggle_ws.isChecked()
        if self.ui.cb_toggle_ast.isChecked():
            self.viewer.get_tree_image(self.editor.lrp.previous_version.parent, [], whitespaces)
            self.showImage(self.ui.graphicsView, self.viewer.image)

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

    def showAstSelection(self):
        whitespaces = self.ui.cb_toggle_ws.isChecked()
        nodes, _, _ = self.editor.get_nodes_from_selection()
        if len(nodes) == 0:
            return
        start = nodes[0]
        end = nodes[-1]
        ast = self.editor.lrp.previous_version
        parent = ast.find_common_parent(start, end)
        for node in nodes:
            p = node.get_parent()
            if p and p is not parent:
                nodes.append(p)
        nodes.append(parent)
        if parent:
            self.viewer.get_tree_image(parent, [start, end], whitespaces, nodes)
            self.showImage(self.ui.graphicsView, self.viewer.image)

class StateView(QtGui.QMainWindow):
    def __init__(self):
        QtGui.QMainWindow.__init__(self)
        self.ui = Ui_StateView()
        self.ui.setupUi(self)

        self.viewer = Viewer("pydot")

        self.connect(self.ui.btShowSingleState, SIGNAL("clicked()"), self.showSingleState)
        self.connect(self.ui.btShowWholeGraph, SIGNAL("clicked()"), self.showWholeGraph)

    def showWholeGraph(self):
        self.viewer.create_pydot_graph(self.editor.lrp.graph)
        self.showImage(self.ui.gvStategraph, self.viewer.image)

    def showSingleState(self):
        self.viewer.show_single_state(self.editor.lrp.graph, int(self.ui.leSingleState.text()))
        self.showImage(self.ui.gvStategraph, self.viewer.image)

    def setEditor(self, editor):
        self.editor = editor

    def showImage(self, graphicsview, imagefile):
        scene = QGraphicsScene()
        item = QGraphicsPixmapItem(QPixmap(imagefile))
        scene.addItem(item);
        graphicsview.setScene(scene)
        graphicsview.resetMatrix()

class AboutView(QtGui.QDialog):
    def __init__(self):
        QtGui.QDialog.__init__(self)
        self.ui = Ui_AboutDialog()
        self.ui.setupUi(self)

class Window(QtGui.QMainWindow):
    def __init__(self):
        QtGui.QMainWindow.__init__(self)
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)

        self.parseview = ParseView()
        self.parseview.setEditor(self.ui.frame)

        self.stateview = StateView()
        self.stateview.setEditor(self.ui.frame)

        self.connect(self.ui.cbShowLangBoxes, SIGNAL("clicked()"), self.ui.frame.update)

        for l in languages:
            self.ui.list_languages.addItem(str(l))

        self.ui.list_languages.item(0).setSelected(True)

        self.loadLanguage(self.ui.list_languages.item(0))

        self.connect(self.ui.list_languages, SIGNAL("itemClicked(QListWidgetItem *)"), self.loadLanguage)
        self.connect(self.ui.actionImport, SIGNAL("triggered()"), self.importfile)
        self.connect(self.ui.actionOpen, SIGNAL("triggered()"), self.openfile)
        self.connect(self.ui.actionSave, SIGNAL("triggered()"), self.savefile)
        self.connect(self.ui.actionRandomDel, SIGNAL("triggered()"), self.ui.frame.randomDeletion)
        self.connect(self.ui.actionSelect_font, SIGNAL("triggered()"), self.change_font)
        self.connect(self.ui.actionRun, SIGNAL("triggered()"), self.ui.frame.export_unipycation)
        self.connect(self.ui.actionUndoRandomDel, SIGNAL("triggered()"), self.ui.frame.undoDeletion)
        self.connect(self.ui.actionParse_Tree, SIGNAL("triggered()"), self.showParseView)
        self.connect(self.ui.actionStateGraph, SIGNAL("triggered()"), self.showStateView)
        self.connect(self.ui.actionAbout, SIGNAL("triggered()"), self.showAboutView)
        self.connect(self.ui.scrollArea.verticalScrollBar(), SIGNAL("valueChanged(int)"), self.ui.frame.sliderChanged)
        self.connect(self.ui.scrollArea.horizontalScrollBar(), SIGNAL("valueChanged(int)"), self.ui.frame.sliderXChanged)

        self.ui.frame.setFocus(True)

        self.viewer = Viewer("pydot")

    def showAboutView(self):
        about = AboutView()
        about.exec_()

    def showStateView(self):
        self.stateview.show()

    def showParseView(self):
        self.parseview.show()

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

    def change_font(self):
        font = QFontDialog.getFont(self.ui.frame.font)
        self.ui.frame.change_font(font)

    def savefile(self):
        filename = QFileDialog.getSaveFileName()
        self.ui.frame.saveToJson(filename)

    def openfile(self):
        filename = QFileDialog.getOpenFileName()
        self.ui.frame.loadFromJson(filename)
        self.ui.frame.update()

    def loadLanguage(self, item):
        self.language = languages[self.ui.list_languages.row(item)]
        self.main_language = self.language.name
        self.btUpdateGrammar()
        self.ui.frame.setFocus(Qt.OtherFocusReason)

    def btUpdateGrammar(self):
        new_grammar = str(self.language.grammar)
        new_priorities = str(self.language.priorities)
        whitespaces = self.ui.cb_add_implicit_ws.isChecked()
        self.lrp = IncParser(new_grammar, 1, whitespaces)
        self.lrp.init_ast()
        lexer = IncrementalLexer(new_priorities)
        self.ui.frame.reset()
        self.ui.frame.set_mainlanguage(self.lrp, lexer, self.main_language)
        self.btReparse([])

        #self.ui.graphicsView.setScene(QGraphicsScene())

    def btReparse(self, selected_node):
        results = []
        self.ui.list_parsingstatus.clear()
        for key in self.ui.frame.parsers:
            lang = self.ui.frame.parser_langs[key]
            #import cProfile
            #cProfile.runctx("status = self.ui.frame.parsers[key].inc_parse()", globals(), locals())
            status = self.ui.frame.parsers[key].inc_parse(self.ui.frame.line_indents)
            if status:
                qlistitem = QListWidgetItem(QString(lang))
                qlistitem.setIcon(QIcon("gui/accept.png"))
            else:
                qlistitem = QListWidgetItem(QString(lang))
                qlistitem.setIcon(QIcon("gui/cancel.png"))
            self.ui.list_parsingstatus.addItem(qlistitem)
        self.showAst(selected_node)

    def showAst(self, selected_node):
        self.parseview.refresh()

    def showLookahead(self, lrp=None):
        la = lrp.get_next_symbols_string()
        self.ui.lineEdit.setText(la)

def main():
    app = QtGui.QApplication(sys.argv)
    app.setStyle('gtk')
    window=Window()

    window.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
