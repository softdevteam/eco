# Copyright (c) 2012--2014 King's College London
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

from PyQt4 import QtCore
from PyQt4.QtCore import *
from PyQt4 import QtGui
from PyQt4.QtGui import *

from nodeeditor import NodeEditor
from grammars.grammars import Language, EcoGrammar, EcoFile

from incparser.incparser import IncParser
from inclexer.inclexer import IncrementalLexer

import os

BODY_FONT = "Monospace"
BODY_FONT_SIZE = 9

class EditorTab(QWidget):
    def __init__(self, parent=None):
        QtGui.QWidget.__init__(self, parent)
        boxlayout = QHBoxLayout(self)
        self.scrollarea = ScopeScrollArea(self)
        self.editor = NodeEditor(self)
        self.editor.setFocusPolicy(QtCore.Qt.WheelFocus)

        self.scrollarea.setWidget(self.editor)
        self.scrollarea.setWidgetResizable(True)
        self.scrollarea.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOn)
        self.scrollarea.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOn)
        self.scrollarea.update_theme()

        self.linenumbers = LineNumbers(self)
        self.linenumbers.setContextMenuPolicy(QtCore.Qt.DefaultContextMenu)

        self.autolboxes = AutoLBoxComplete(self)

        boxlayout.addWidget(self.autolboxes)
        boxlayout.addWidget(self.linenumbers)
        boxlayout.addWidget(self.scrollarea)

        self.connect(self.scrollarea.verticalScrollBar(), SIGNAL("valueChanged(int)"), self.editor.sliderChanged)
        self.connect(self.scrollarea.horizontalScrollBar(), SIGNAL("valueChanged(int)"), self.editor.sliderXChanged)
        self.connect(self.editor, SIGNAL("painted()"), self.painted)
        self.connect(self.editor, SIGNAL("keypress(QKeyEvent)"), self.keypress)
        self.connect(self.linenumbers, SIGNAL("breakpoint"), self.toggle_breakpoint)
        self.connect(self.linenumbers, SIGNAL("breakcondition"), self.set_breakpoint_condition)

        self.filename = self.export_path = None
        self.debugging = False
        self.breakpoints = {'keep': [], 'del': []}

    def update_theme(self):
        self.scrollarea.update_theme()
        self.editor.update()

    def changed(self):
        return self.editor.tm.changed

    def painted(self):
        self.linenumbers.update()
        self.scrollarea.update()
        self.autolboxes.update()
        if self.filename:
            filename = os.path.basename(str(self.filename))
        else:
            filename = "[No name]"
        if self.editor.tm.changed:
            filename += "*"
        tabwidget = self.parent().parent()
        index = tabwidget.indexOf(self)
        if tabwidget.tabText(index) != filename:
            tabwidget.setTabText(index, filename)

    def keypress(self, e=None, center=False):
        if(e and e.key() == Qt.Key_PageUp):
            self.scrollarea.decVSlider(True)
        elif(e and e.key() == Qt.Key_PageDown):
            self.scrollarea.incVSlider(True)
        else:
            self.editor.getScrollSizes()
            self.scrollarea.update()
            self.scrollarea.fix(center=center)

    def set_language(self, lang, whitespace):
        if isinstance(lang, Language):
            lrp = IncParser(str(lang.grammar), 1, whitespace)
            lrp.init_ast()
            lexer = IncrementalLexer(str(lang.priorities))
            self.editor.set_mainlanguage(lrp, lexer, lang.name)
        elif isinstance(lang, EcoGrammar):
            bootstrap = BootstrapParser(lr_type=1, whitespaces=whitespace)
            bootstrap.parse(lang.grammar)
            self.editor.set_mainlanguage(bootstrap.incparser, bootstrap.inclexer, lang.name)
        elif isinstance(lang, EcoFile):
            incparser, inclexer = lang.load()
            self.editor.set_mainlanguage(incparser, inclexer, lang.name)
            incparser.setup_autolbox(lang.name)

    def toggle_breakpoint(self, isTemp, number, from_click):
        self.emit(SIGNAL("breakpoint"), isTemp, number, from_click)

    def set_breakpoint_condition(self, number):
        self.emit(SIGNAL("breakcondition"), number)

    def is_debugging(self, isDebugging):
        self.debugging = isDebugging;
        if not isDebugging:
            self.breakpoints = {'keep': [], 'del': []}

    def set_breakpoints(self, bps):
        self.breakpoints = bps

class ScopeScrollArea(QtGui.QAbstractScrollArea):

    def update(self):
        QWidget.update(self)
        self.verticalScrollBar().setMaximum(self.parent().editor.scroll_height)
        self.verticalScrollBar().setPageStep(50)
        self.horizontalScrollBar().setMaximum(self.parent().editor.scroll_width)
        self.horizontalScrollBar().setPageStep(50)


    def fix(self, center=False):
        gfont = QApplication.instance().gfont
        x, y = self.parent().editor.cursor_to_coordinate()

        scrollbar_height = self.horizontalScrollBar().geometry().height()
        if center:
            half_screen = self.geometry().height() / 2
        else:
            half_screen = 0

        # fix vertical bar
        if y < 0:
            while y < half_screen:
                self.decVSlider()
                y += gfont.fontht
        if y+3 > self.parent().editor.geometry().height() - scrollbar_height: # the 3 is the padding of the canvas
            while y+3 + half_screen > self.parent().editor.geometry().height() - scrollbar_height:
                self.incVSlider()
                y -= gfont.fontht

        # fix horizontal bar
        cursor_x = self.parent().editor.cursor.get_x()
        while cursor_x < self.horizontalScrollBar().value():
             self.decHSlider()
        while cursor_x > ((self.geometry().width() - self.verticalScrollBar().width()) / gfont.fontwt) + self.horizontalScrollBar().value():
            self.incHSlider()
            if self.horizontalScrollBar().value() == self.horizontalScrollBar().maximum():
                break

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

    def update_theme(self):
        settings = QSettings("softdev", "Eco")
        pal = self.viewport().palette()
        if settings.value("app_custom", False).toBool():
            fg = settings.value("app_foreground", "#000000")
            bg = settings.value("app_background", "#ffffff")
            pal.setColor(QPalette.Base, QColor(bg))
            pal.setColor(QPalette.Text, QColor(fg))
        else:
            theme = settings.value("app_theme", "Light (Default)")
            if theme == "Dark":
                pal.setColor(QPalette.Base, QColor(0, 43, 54))
                pal.setColor(QPalette.Text, QColor("#93A1A1"))
            elif theme == "Gruvbox":
                pal.setColor(QPalette.Base, QColor("#32302F"))
                pal.setColor(QPalette.Text, QColor("#EBDBB2"))
            else:
                pal.setColor(QPalette.Base, QPalette().color(QPalette.Base))
                pal.setColor(QPalette.Text, QPalette().color(QPalette.Text))
        self.viewport().setPalette(pal)

    def incHSlider(self):
        self.horizontalScrollBar().setSliderPosition(self.horizontalScrollBar().sliderPosition() + self.horizontalScrollBar().singleStep())

    def decHSlider(self):
        self.horizontalScrollBar().setSliderPosition(self.horizontalScrollBar().sliderPosition() - self.horizontalScrollBar().singleStep())

    def incVSlider(self, page=False):
        if page:
            step = self.verticalScrollBar().pageStep()
        else:
            step = self.verticalScrollBar().singleStep()
        self.verticalScrollBar().setSliderPosition(self.verticalScrollBar().sliderPosition() + step)

    def decVSlider(self, page=False):
        if page:
            step = self.verticalScrollBar().pageStep()
        else:
            step = self.verticalScrollBar().singleStep()
        self.verticalScrollBar().setSliderPosition(self.verticalScrollBar().sliderPosition() - step)

class LineNumbers(QFrame):
    def mouseDoubleClickEvent(self, event):
        if not self.parent().debugging:
            return None;
        # Check which number is clicked
        editor = self.parent().editor
        line_clicked = self.findLineNumberAt(event.y())
        if line_clicked <= len(editor.lines):
            event.accept()
            self.emit(SIGNAL("breakpoint"), False, line_clicked, True)

    def contextMenuEvent(self, event):
        """This event is fired when line numbers are right clicked"""
        if not self.parent().debugging:
            return None;
        editor = self.parent().editor
        line_clicked = self.findLineNumberAt(event.y())

        if line_clicked > len(editor.lines):
           return None;
        event.accept()
        menu = QMenu(self)
        bAction = menu.addAction("Toggle breakpoint at "+str(line_clicked))
        tbAction = menu.addAction("Toggle temp breakpoint at "+str(line_clicked))
        bcAction = menu.addAction("Set breakpoint with condition at "+str(line_clicked))
        action = menu.exec_(self.mapToGlobal(event.pos()))
        if action == bAction:
            self.emit(SIGNAL("breakpoint"), False, line_clicked, False)
        elif action == tbAction:
            self.emit(SIGNAL("breakpoint"), True, line_clicked, False)
        elif action == bcAction:
            self.emit(SIGNAL("breakcondition"), line_clicked)

    def findLineNumberAt(self, y):
        gfont = QApplication.instance().gfont
        editor = self.parent().editor
        line = 0
        while gfont.fontht + line*gfont.fontht < y:
            line += 1
        start = editor.paint_start[0]
        return line+start+1

    def paintEvent(self, event):
        gfont = QApplication.instance().gfont
        paint = QtGui.QPainter()
        paint.begin(self)
        paint.setPen(QColor("grey"))
        paint.setFont(gfont.font)

        debugging = self.parent().debugging
        self.breakpoint_space = 10

        editor = self.parent().editor
        y = editor.paint_start[1]
        start = editor.paint_start[0]
        for i in range(start, len(editor.lines)):
            text = str(i+1)
            paint.drawText(QtCore.QPointF(self.geometry().width() - (len(text)+1)*gfont.fontwt, gfont.fontht + y*gfont.fontht), text +":")
            if debugging:
                self.draw_breakpoint(paint, text, gfont.fontht+y*gfont.fontht-9)
            y += editor.lines[i].height
            i += 1
            if (y+1)*gfont.fontht >= editor.geometry().height():
                break

        paint.end()

    def draw_breakpoint(self, paint, line_no, y_pos):
        big_rect = QtCore.QRectF(0, y_pos, 8, 8)
        small_rect = QtCore.QRectF(2, y_pos+2, 4, 4)

        paint.setBrush(QColor("blue"))
        breakpoints = self.parent().breakpoints

        if not breakpoints:
            return None
        move = False
        if line_no in breakpoints['keep']:
            paint.setBrush(QColor("blue"))
            paint.drawEllipse(big_rect)
            move = True
        if line_no in breakpoints['del']:
            paint.setBrush(QColor("yellow"))
            if move:
                paint.drawEllipse(small_rect)
            else:
                paint.drawEllipse(big_rect)

    def update(self):
        gfont = QApplication.instance().gfont
        editor = self.parent().editor
        import math
        if len(editor.lines) < 10:
            digits = 1
        else:
            digits = int(math.log10(len(editor.lines)))+1
        breakpoint_space = 0
        if self.parent().debugging:
            breakpoint_space = 10
        self.setMinimumWidth(gfont.fontwt * (digits + 1) + breakpoint_space)
        QFrame.update(self)

class AutoLBoxComplete(QFrame):
    def paintEvent(self, event):
        gfont = QApplication.instance().gfont
        paint = QtGui.QPainter()
        paint.begin(self)

        editor = self.parent().editor
        y = editor.paint_start[1]
        start = editor.paint_start[0]
        for i in range(start, len(editor.lines)):

            try:
                auto = self.parent().editor.autolboxlines[i]
                posy = y*gfont.fontht + gfont.fontht/2
                paint.drawImage(QPointF(0, posy), QImage("gui/lightbulb.png"))
            except KeyError:
                pass

            y += editor.lines[i].height
            i += 1
            if (y+1)*gfont.fontht >= editor.geometry().height():
                break

        paint.end()

    def update(self):
        self.setMinimumWidth(16)
        QFrame.update(self)

    def mousePressEvent(self, event):
        gfont = QApplication.instance().gfont
        if event.button() == Qt.LeftButton:
            # calculate line
            line = self.parent().linenumbers.findLineNumberAt(event.y()) - 1
            menu = QMenu(self)
            if line not in self.parent().editor.autolboxlines:
                return
            for s, e, l in self.parent().editor.autolboxlines[line]:
                text = []
                temp = s
                while temp is not e:
                    text.append(temp.symbol.name)
                    temp = temp.next_term
                text.append(e.symbol.name)
                text.append(" : {}".format(l))
                item = QAction("".join(text), menu)
                item.setData((s,e,l))
                menu.addAction(item)
            action = menu.exec_(self.mapToGlobal(event.pos()))
            if action:
                s, e, l = action.data().toPyObject()
                self.parent().editor.tm.select_nodes(s, e)
                langdef = self.parent().editor.tm.get_langdef_from_string(l)
                self.parent().editor.tm.surround_with_languagebox(langdef)
                self.parent().editor.tm.reparse(s)
                self.parent().editor.getWindow().btReparse([]) # refresh gui
                self.parent().editor.update() # refresh code editor
