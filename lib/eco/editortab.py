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

from PyQt5 import QtCore
from PyQt5.QtCore import *
from PyQt5 import QtGui
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *

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

        boxlayout.addWidget(self.linenumbers)
        boxlayout.addWidget(self.scrollarea)

        self.connect(self.scrollarea.verticalScrollBar(), SIGNAL("valueChanged(int)"), self.editor.sliderChanged)
        self.connect(self.scrollarea.horizontalScrollBar(), SIGNAL("valueChanged(int)"), self.editor.sliderXChanged)
        self.connect(self.editor, SIGNAL("painted()"), self.painted)
        self.connect(self.editor, SIGNAL("keypress(QKeyEvent)"), self.keypress)

        self.filename = self.export_path = None

    def update_theme(self):
        self.scrollarea.update_theme()

    def changed(self):
        return self.editor.tm.changed

    def painted(self):
        self.linenumbers.update()
        self.scrollarea.update()
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
            grammar = str(lang.grammar)
            new_priorities = str(lang.priorities)
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

class ScopeScrollArea(QAbstractScrollArea):

    def update(self):
        QWidget.update(self)
        self.verticalScrollBar().setMaximum(self.parent().editor.scroll_height)
        self.verticalScrollBar().setPageStep(50)
        self.horizontalScrollBar().setMaximum(self.parent().editor.scroll_width)
        self.horizontalScrollBar().setPageStep(50)


    def fix(self, center=False):
        gfont = QApplication.instance().gfont
        cursor = self.parent().editor.tm.cursor
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

    def paintEvent(self, event):
        gfont = QApplication.instance().gfont
        paint = QtGui.QPainter()
        paint.begin(self)
        paint.setPen(QColor("grey"))
        paint.setFont(gfont.font)


        editor = self.parent().editor
        y = editor.paint_start[1]
        start = editor.paint_start[0]
        for i in range(start, len(editor.lines)):
            text = str(i+1)
            paint.drawText(QtCore.QPointF(self.geometry().width() - (len(text)+1)*gfont.fontwt, gfont.fontht + y*gfont.fontht), text +":")
            y += editor.lines[i].height
            i += 1
            if (y+1)*gfont.fontht >= editor.geometry().height():
                break

        paint.end()

    def update(self):
        gfont = QApplication.instance().gfont
        editor = self.parent().editor
        import math
        if len(editor.lines) < 10:
            digits = 1
        else:
            digits = int(math.log10(len(editor.lines)))+1
        self.setMinimumWidth(gfont.fontwt * (digits + 1))
        QFrame.update(self)
