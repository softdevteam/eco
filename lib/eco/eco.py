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

from treemanager import TreeManager

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
        self.indent = 0

    def __repr__(self):
        return "Line(%s, width=%s, height=%s)" % (self.node, self.width, self.height)

class LineNumbers(QFrame):
    def __init__(self, parent=None):
        QtGui.QWidget.__init__(self, parent)

        self.font = QtGui.QFont('Courier', 9)
        self.fontm = QtGui.QFontMetrics(self.font)
        self.fontht = self.fontm.height() + 3
        self.fontwt = self.fontm.width(" ")

        self.info = []

    def paintEvent(self, event):
        paint = QtGui.QPainter()
        paint.begin(self)
        paint.setFont(self.font)
        for y, line, indent in self.info:
            text = str(line)# + "|" + str(indent)
            x = self.geometry().width() - len(text) * self.fontwt - self.fontwt
            paint.drawText(QtCore.QPointF(x, self.fontht + y*self.fontht), text +":")
        paint.end()
        self.info = []

    def getMaxWidth(self):
        max_width = 0
        for _, line, _ in self.info:
            max_width = max(max_width, self.fontm.width(str(line)+":"))
        return max_width

class NodeEditor(QFrame):

    # ========================== init stuff ========================== #

    def __init__(self, parent=None):
        QtGui.QWidget.__init__(self, parent)

        self.defaultFont = self.font()
        self.boldDefaultFont = QFont(self.defaultFont)
        self.boldDefaultFont.setBold(True)

        self.font = QtGui.QFont('Courier', 9)
        self.fontm = QtGui.QFontMetrics(self.font)
        self.fontht = self.fontm.height() + 3
        self.fontwt = self.fontm.width(" ")

        self.infofont = QtGui.QFont('Courier', 6)
        self.infofontht = QtGui.QFontMetrics(self.infofont).height() + 3
        self.infofontwt = QtGui.QFontMetrics(self.infofont).width(" ")

        self.viewport_y = 0 # top visible line

        return

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

        self.changed_line = -1
        self.line_info = []
        self.line_heights = []
        self.line_indents = []
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
        self.tm = TreeManager()
        self.tm.add_parser(parser, lexer, lang_name)
        self.tm.set_font(self.fontm)
        return

        self.parsers = {}
        self.lexers = {}
        self.priorities = {}
        self.lrp = parser
        self.ast = parser.previous_version
        self.parsers[parser.previous_version.parent] = parser
        self.lexers[parser.previous_version.parent] = lexer
        self.parser_langs[parser.previous_version.parent] = lang_name
        self.magic_tokens = []


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

        self.getWindow().ui.fLinenumbers.setMinimumWidth(self.fontm.width("000: "))
        self.getWindow().ui.fLinenumbers.setMaximumWidth(self.fontm.width("000: "))

        self.getWindow().ui.fLinenumbers.update()


    # paint lines using new line manager
    def paintLines(self, paint, startline):

        # find internal line corresponding to visual line
        visual_line = 0
        internal_line = 0
        for l in self.tm.lines:
            if visual_line + l.height > startline:
                break
            visual_line += l.height
            internal_line += 1

        x = 0
        y = visual_line - startline # start drawing outside of viewport to display partial images
        self.paint_start = (internal_line, y)

        max_y = self.geometry().height()/self.fontht

        line = internal_line
        node = self.tm.lines[line].node
        if node.symbol.name == "\r":
            node = node.next_term # ignore \r if it is startnode


        self.paint_nodes(paint, node, x, y, line, max_y)

        #self.paintSelection(paint, visual_line)

    #XXX if starting node is inside language box, init lbox with amout of languge boxes
    def paint_nodes(self, paint, node, x, y, line, max_y, lbox=0):
        selected_language = self.tm.mainroot
        error_node = self.tm.get_mainparser().error_node

        highlighter = self.get_highlighter(node)
        selection_start = min(self.tm.selection_start, self.tm.selection_end)
        selection_end = max(self.tm.selection_start, self.tm.selection_end)
        start_lbox = self.get_languagebox(node)

        self.selected_lbox = self.tm.selected_lbox

        if start_lbox and self.selected_lbox is start_lbox:
            lbox += 1
            draw_lbox = True
        else:
            draw_lbox = False
        self.lines = self.tm.lines
        self.cursor = self.tm.cursor
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
                error_node = self.tm.get_parser(lbnode).error_node
                continue

            if isinstance(node, EOS):
                self.draw_selection(paint, node, line, selection_start, selection_end, y)
                lbnode = self.get_languagebox(node)
                if lbnode:
                    lbox -= 1
                    node = lbnode.next_term
                    highlighter = self.get_highlighter(node)
                    error_node = self.tm.get_parser(lbnode.symbol.ast).error_node
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
                self.getWindow().ui.fLinenumbers.info.append((y,line, self.lines[line].indent))
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

            # draw squiggly line
            if node is error_node:
                if isinstance(node, EOS):
                    length = self.fontwt
                else:
                    length = len(error_node.symbol.name)*self.fontwt
                if isinstance(node.symbol, MagicTerminal):
                    self.draw_vertical_squiggly_line(paint,x,y)
                else:
                    self.draw_squiggly_line(paint,x,y,length)

        self.getWindow().ui.fLinenumbers.info.append((y,line, self.lines[line].indent))
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

    def draw_vertical_squiggly_line(self, paint, x, y):
        paint.setPen(Qt.CustomDashLine)
        pen = paint.pen()
        pen.setDashPattern([2,2])
        pen.setColor(QColor("red"))
        paint.setPen(pen)
        y = 3+y*self.fontht
        paint.drawLine(x-1, y, x-1, y+self.fontht)
        paint.drawLine(x, y+2, x, y+self.fontht)
        paint.setPen(Qt.SolidLine)

    def draw_squiggly_line(self, paint, x, y, length):
        paint.setPen(Qt.CustomDashLine)
        pen = paint.pen()
        pen.setDashPattern([2,2])
        pen.setColor(QColor("red"))
        paint.setPen(pen)
        #x -= length
        y = (y+1)*self.fontht+1
        paint.drawLine(x, y, x+length, y)
        paint.drawLine(x+2, y+1, x+2+length, y+1)
        paint.setPen(Qt.SolidLine)

    def draw_selection(self, paint, node, line, selection_start, selection_end, y):
        # draw selection
        if node.lookup == "<return>" or node is self.tm.get_eos():
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
        base = lang_dict[self.tm.get_language(root)].base
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

    def get_languagebox(self, node):
        root = node.get_root()
        lbox = root.get_magicterminal()
        return lbox

    def focusNextPrevChild(self, b):
        # don't switch to next widget on TAB
        return False

    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton:
            cursor = self.coordinate_to_cursor(e.x(), e.y())
            self.tm.cursor = cursor
            self.tm.selection_start = cursor.copy()
            self.tm.selection_end = cursor.copy()
            self.tm.fix_cursor_on_image()
            self.getWindow().showLookahead()
            self.update()

    def mouseDoubleClickEvent(self, e):
        # XXX can be moved to treemanager once cursor.x is relative to nodes
        if e.button() == Qt.LeftButton:
            self.tm.cursor = self.coordinate_to_cursor(e.x(), e.y())
            selected_node, _, _ = self.tm.get_node_from_cursor()
            if selected_node.image is None:
                return

            self.tm.fix_cursor_on_image()
            if selected_node.plain_mode is False:
                selected_node.plain_mode = True
                self.tm.cursor.x -= math.ceil(selected_node.image.width() * 1.0 / self.fontwt)
                self.tm.cursor.x += len(selected_node.symbol.name)
            else:
                selected_node.plain_mode = False
                self.tm.fix_cursor_on_image()
            self.update()

    def cursor_to_coordinate(self):
        y = 0
        for l in self.tm.lines[:self.cursor.y]:
            y += l.height * self.fontht
        x = self.tm.cursor.x * self.fontwt
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
            y += self.tm.lines[line].height
            if y > mouse_y:
                break
            line += 1
        result.y = line

        cursor_x = x / self.fontwt

        if cursor_x < 0:
            result.x = 0
        elif cursor_x <= self.tm.lines[result.y].width:
            result.x = cursor_x
        else:
            result.x = self.tm.lines[result.y].width

        return result

    def mouseMoveEvent(self, e):
        # apparaently this is only called when a mouse button is clicked while
        # the mouse is moving
        self.tm.selection_end = self.coordinate_to_cursor(e.x(), e.y())
        self.update()

    def XXXkeyPressEvent(self, e):
        import cProfile
        cProfile.runctx("self.linkkeyPressEvent(e)", globals(), locals())

    def keyPressEvent(self, e):

        if e.key() in [Qt.Key_Shift, Qt.Key_Alt, Qt.Key_Control, Qt.Key_Meta, Qt.Key_AltGr]:
            if e.key() == Qt.Key_Shift:
                self.tm.key_shift()
            return

        #selected_node, inbetween, x = self.tm.get_nodes_from_cursor()

        text = e.text()

        self.edit_rightnode = False # has been processes in get_nodes_at_pos -> reset

        if e.key() == Qt.Key_Escape:
            self.tm.key_escape()
        elif e.key() == Qt.Key_Backspace:
            self.tm.key_backspace()
        elif e.key() in [Qt.Key_Up, Qt.Key_Down, Qt.Key_Left, Qt.Key_Right]:
            if e.modifiers() == Qt.ShiftModifier:
                self.tm.key_cursors(e.key(), True)
            else:
                self.tm.key_cursors(e.key(), False)
        elif e.key() == Qt.Key_Home:
            self.tm.key_home()
        elif e.key() == Qt.Key_End:
            self.tm.key_end()
        elif e.key() == Qt.Key_C and e.modifiers() == Qt.ControlModifier:
            text = self.tm.copySelection()
            QApplication.clipboard().setText(text)
        elif e.key() == Qt.Key_V and e.modifiers() == Qt.ControlModifier:
            text = QApplication.clipboard().text()
            self.tm.pasteText(text)
        elif e.key() == Qt.Key_X and e.modifiers() == Qt.ControlModifier:
            self.tm.cutSelection()
        elif e.key() == Qt.Key_Space and e.modifiers() == Qt.ControlModifier:
            self.showSubgrammarMenu()
            if self.sublanguage:
                if self.tm.hasSelection():
                    self.tm.surround_with_languagebox(self.sublanguage)
                else:
                    self.tm.add_languagebox(self.sublanguage)
        elif e.key() == Qt.Key_Space and e.modifiers() == Qt.ControlModifier | Qt.ShiftModifier:
            self.tm.leave_languagebox()
        elif e.key() == Qt.Key_Delete:
            self.tm.key_delete()
        else:
            if e.key() == Qt.Key_Tab:
                text = "    "
            else:
                text = e.text()
            self.tm.key_normal(text)

        self.getWindow().btReparse([])
        self.fix_scrollbars()
        self.update()
        self.getWindow().showLookahead()

    def println(self, prestring, y):
        node = self.lines[y].node.next_term
        x = []
        while node is not None and node.symbol.name != "\r":
            x.append(node.symbol.name)
            node = node.next_term
        print(prestring, "".join(x))

    def print_line(self, y):
        current = self.lines[y].node
        while True:
            print(current)
            current = current.next_term
            if current is None:
                return

    def fix_scrollbars(self):
        self.cursor = self.tm.cursor
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
        self.viewport_y = 0
        self.tm.import_file(text)
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
        lookaheads = self.tm.getLookaheadList()
        # Create menu
        menu = QtGui.QMenu( self )
        # Create actions
        toolbar = QtGui.QToolBar()
        for l in languages:
            item = toolbar.addAction(str(l), self.createMenuFunction(l))
            l = "<%s>" % (l)
            if l in lookaheads:
                item.setFont(self.boldDefaultFont)
            menu.addAction(item)
        x,y = self.cursor_to_coordinate()
        menu.exec_(self.mapToGlobal(QPoint(0,0)) + QPoint(3 + x, y + self.fontht))

    def getLookaheadList(self):
        selected_node, _, _ = self.get_nodes_at_position()
        root = selected_node.get_root()
        lrp = self.parsers[root]
        return lrp.get_next_symbols_list(selected_node.state)

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

        root = self.tm.parsers[0][0].previous_version.parent
        language = self.tm.parsers[0][2]
        manager = JsonManager()
        manager.save(root, language, whitespaces, filename)

    def loadFromJson(self, filename):
        manager = JsonManager()
        language_boxes = manager.load(filename)

        #self.ast.parent = root
        #self.lines[0].node = root.children[0]
        #self.eos = root.children[-1]

        self.tm = TreeManager()
        self.tm.set_font(self.fontm)

        self.tm.load_file(language_boxes)
        self.reset()
        self.getWindow().btReparse([])
        return

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
        self.tm.set_font(self.fontm)

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
            #self.viewer.get_terminal_tree(self.editor.lrp.previous_version.parent)
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
        if not filename:
            return
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
        if filename:
            self.ui.frame.saveToJson(filename)

    def openfile(self):
        filename = QFileDialog.getOpenFileName()
        if filename:
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
        for parser, lexer, lang in self.ui.frame.tm.parsers:
            #import cProfile
            #cProfile.runctx("parser.inc_parse(self.ui.frame.line_indents)", globals(), locals())
            status = parser.last_status #inc_parse(self.ui.frame.line_indents)
            qlistitem = QListWidgetItem(QString(lang))
            if status:
                qlistitem.setIcon(QIcon("gui/accept.png")) # XXX create icon only once
            else:
                qlistitem.setIcon(QIcon("gui/exclamation.png"))
                enode = parser.error_node
                symbols = parser.get_expected_symbols(enode.prev_term.state)
                l = []
                for s in symbols:
                    l.append("'%s'" % (s.name))
                emsg = "Error: Found \"%s\" expected %s (State: %s)" % (enode.symbol.name, ",".join(l), enode.prev_term.state)
                qlistitem.setToolTip(emsg)
            self.ui.list_parsingstatus.addItem(qlistitem)
            # XXX refactor
            #if self.ui.frame.selected_lbox and key is self.ui.frame.selected_lbox.symbol.ast:
            #    self.ui.list_parsingstatus.setCurrentItem(qlistitem)
            #if not self.ui.frame.selected_lbox and key is self.ui.frame.ast.parent:
            #    self.ui.list_parsingstatus.setCurrentItem(qlistitem)
        self.showAst(selected_node)

    def showAst(self, selected_node):
        self.parseview.refresh()

    def showLookahead(self):
        l = self.ui.frame.tm.getLookaheadList()
        self.ui.lineEdit.setText(", ".join(l))

def main():
    app = QtGui.QApplication(sys.argv)
    app.setStyle('gtk')
    window=Window()

    window.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
