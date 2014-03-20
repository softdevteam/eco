from PyQt4 import QtCore
from PyQt4.QtCore import *
from PyQt4 import QtGui
from PyQt4.QtGui import *

from nodeeditor import NodeEditor
from grammars.grammars import Language, EcoGrammar, EcoFile

from incparser.incparser import IncParser
from inclexer.inclexer import IncrementalLexer
from grammar_parser.bootstrap import BootstrapParser

from jsonmanager import JsonManager

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

        boxlayout.addWidget(self.linenumbers)
        boxlayout.addWidget(self.scrollarea)

        self.connect(self.scrollarea.verticalScrollBar(), SIGNAL("valueChanged(int)"), self.editor.sliderChanged)
        self.connect(self.scrollarea.horizontalScrollBar(), SIGNAL("valueChanged(int)"), self.editor.sliderXChanged)
        self.connect(self.editor, SIGNAL("painted()"), self.painted)
        self.connect(self.editor, SIGNAL("keypress(QKeyEvent)"), self.keypress)

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

    def keypress(self, e=None):
        if(e and e.key() == Qt.Key_PageUp):
            self.scrollarea.decVSlider(True)
        elif(e and e.key() == Qt.Key_PageDown):
            self.scrollarea.incVSlider(True)
        else:
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
        elif isinstance(lang, EcoFile):
            manager = JsonManager(unescape=True)
            root, language, whitespaces = manager.load(lang.filename)[0]
            pickle_id = hash(open(lang.filename, "r").read())
            bootstrap = BootstrapParser(lr_type=1, whitespaces=whitespaces)
            bootstrap.ast = root
            bootstrap.create_parser(pickle_id)
            bootstrap.create_lexer()
            self.editor.set_mainlanguage(bootstrap.incparser, bootstrap.inclexer, lang.name)

class ScopeScrollArea(QtGui.QAbstractScrollArea):

    def update(self):
        QWidget.update(self)
        self.verticalScrollBar().setMaximum(self.parent().editor.scroll_height)
        self.verticalScrollBar().setPageStep(50)
        self.horizontalScrollBar().setMaximum(self.parent().editor.scroll_width)
        self.horizontalScrollBar().setPageStep(50)


    def fix(self):
        gfont = QApplication.instance().gfont
        cursor = self.parent().editor.tm.cursor
        x, y = self.parent().editor.cursor_to_coordinate()

        scrollbar_height = self.horizontalScrollBar().geometry().height()

        # fix vertical bar
        if y < 0:
            while y < 0:
                self.decVSlider()
                y += gfont.fontht
        if y+3 > self.parent().editor.geometry().height() - scrollbar_height: # the 3 is the padding of the canvas
            while y+3 > self.parent().editor.geometry().height() - scrollbar_height:
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
            text = str(i)
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
        if len(editor.lines) <= 10:
            digits = 1
        else:
            digits = int(math.log10(len(editor.lines)-1))+1
        self.setMinimumWidth(gfont.fontwt * (digits + 1))
        QFrame.update(self)
