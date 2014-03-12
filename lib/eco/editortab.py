from PyQt4 import QtCore
from PyQt4.QtCore import *
from PyQt4 import QtGui
from PyQt4.QtGui import *

from nodeeditor import NodeEditor
from grammars.grammars import Language, EcoGrammar

from incparser.incparser import IncParser
from inclexer.inclexer import IncrementalLexer
from grammar_parser.bootstrap import BootstrapParser

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

        self.linenumbers = LineNumbers(self)
        self.linenumbers.setMinimumWidth(30)

        boxlayout.addWidget(self.linenumbers)
        boxlayout.addWidget(self.scrollarea)

        self.connect(self.scrollarea.verticalScrollBar(), SIGNAL("valueChanged(int)"), self.editor.sliderChanged)
        self.connect(self.scrollarea.horizontalScrollBar(), SIGNAL("valueChanged(int)"), self.editor.sliderXChanged)
        self.connect(self.editor, SIGNAL("painted()"), self.painted)
        self.connect(self.editor, SIGNAL("keypress()"), self.keypress)

        self.filename = None

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
        tabwidget.setTabText(index, filename)

    def keypress(self):
        self.editor.getScrollSizes()
        self.scrollarea.update()
        self.scrollarea.fix()

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

class ScopeScrollArea(QtGui.QAbstractScrollArea):

    def update(self):
        QWidget.update(self)
        self.verticalScrollBar().setMaximum(self.parent().editor.scroll_height)
        self.verticalScrollBar().setPageStep(1)
        self.horizontalScrollBar().setMaximum(self.parent().editor.scroll_width)
        self.horizontalScrollBar().setPageStep(1)


    def fix(self):
        cursor = self.parent().editor.tm.cursor
        x, y = self.parent().editor.cursor_to_coordinate()

        scrollbar_height = self.horizontalScrollBar().geometry().height()

        # fix vertical bar
        if y < 0:
            while y < 0:
                self.decVSlider()
                y += self.parent().editor.fontht
        if y+3 > self.parent().editor.geometry().height() - scrollbar_height: # the 3 is the padding of the canvas
            while y+3 > self.parent().editor.geometry().height() - scrollbar_height:
                self.incVSlider()
                y -= self.parent().editor.fontht

        # fix horizontal bar
        cursor_x = self.parent().editor.cursor.get_x()
        while cursor_x < self.horizontalScrollBar().value():
             self.decHSlider()
        while cursor_x > ((self.geometry().width() - self.verticalScrollBar().width()) / self.parent().editor.fontwt) + self.horizontalScrollBar().value():
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

    def incHSlider(self):
        self.horizontalScrollBar().setSliderPosition(self.horizontalScrollBar().sliderPosition() + self.horizontalScrollBar().singleStep())

    def decHSlider(self):
        self.horizontalScrollBar().setSliderPosition(self.horizontalScrollBar().sliderPosition() - self.horizontalScrollBar().singleStep())

    def incVSlider(self):
        self.verticalScrollBar().setSliderPosition(self.verticalScrollBar().sliderPosition() + self.verticalScrollBar().singleStep())

    def decVSlider(self):
        self.verticalScrollBar().setSliderPosition(self.verticalScrollBar().sliderPosition() - self.verticalScrollBar().singleStep())

class LineNumbers(QFrame):
    def __init__(self, parent=None):
        QtGui.QFrame.__init__(self, parent)

        self.font = QtGui.QFont(BODY_FONT, BODY_FONT_SIZE)
        self.fontm = QtGui.QFontMetrics(self.font)
        self.fontht = self.fontm.height() + 3
        self.fontwt = self.fontm.width(" ")

        self.info = []

    def paintEvent(self, event):
        paint = QtGui.QPainter()
        paint.begin(self)
        paint.setPen(QColor("grey"))
        paint.setFont(self.font)

       #scrollbar_height = self.window().ui.scrollArea.horizontalScrollBar().geometry().height()

        editor = self.parent().editor
        y = editor.paint_start[1]
        start = editor.paint_start[0]
        for i in range(start, len(editor.lines)):
            text = str(i)
            paint.drawText(QtCore.QPointF(0, self.fontht + y*self.fontht), text +":")
            y += editor.lines[i].height
            i += 1
            if (y+1)*self.fontht >= editor.geometry().height():
                break

        paint.end()
        self.info = []

    def getMaxWidth(self):
        max_width = 0
        for _, line, _ in self.info:
            max_width = max(max_width, self.fontm.width(str(line)+":"))
        return max_width

    def change_font(self, font):
        self.font = font[0]
        self.fontm = QtGui.QFontMetrics(self.font)
        self.fontht = self.fontm.height() + 3
        self.fontwt = self.fontm.width(" ")
