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
from gui.languagedialog import Ui_Dialog as Ui_LanguageDialog

from grammar_parser.plexer import PriorityLexer
from incparser.incparser import IncParser
from inclexer.inclexer import IncrementalLexer
from viewer import Viewer

from grammar_parser.gparser import Terminal, MagicTerminal, IndentationTerminal, Nonterminal

from incparser.astree import TextNode, BOS, EOS, ImageNode, FinishSymbol

from grammars.grammars import languages, lang_dict, Language, EcoGrammar

from grammar_parser.bootstrap import BootstrapParser

from time import time
import os
import math

import syntaxhighlighter
import editor
from jsonmanager import JsonManager

from treemanager import TreeManager, Cursor

from nodeeditor import NodeEditor

def print_var(name, value):
    print("%s: %s" % (name, value))

BODY_FONT = "Monospace"
BODY_FONT_SIZE = 9

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

        scrollbar_height = self.window().ui.scrollArea.horizontalScrollBar().geometry().height()

        for y, line, indent in self.info:
            if self.fontht + y*self.fontht > self.geometry().height() - scrollbar_height:
                break
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

    def change_font(self, font):
        self.font = font[0]
        self.fontm = QtGui.QFontMetrics(self.font)
        self.fontht = self.fontm.height() + 3
        self.fontwt = self.fontm.width(" ")

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
        self.connect(self.ui.rb_view_parsetree, SIGNAL("clicked()"), self.refresh)
        self.connect(self.ui.rb_view_linetree, SIGNAL("clicked()"), self.refresh)
        self.connect(self.ui.rb_view_ast, SIGNAL("clicked()"), self.refresh)

        self.viewer = Viewer("pydot")
        self.ui.graphicsView.setRenderHints(QPainter.Antialiasing | QPainter.SmoothPixmapTransform | QPainter.TextAntialiasing)

    def setEditor(self, editor):
        self.editor = editor

    def refresh(self):
        whitespaces = self.ui.cb_toggle_ws.isChecked()
        if self.ui.cb_toggle_ast.isChecked():
            if self.ui.rb_view_parsetree.isChecked():
                self.viewer.get_tree_image(self.editor.tm.get_mainparser().previous_version.parent, [], whitespaces)
            elif self.ui.rb_view_linetree.isChecked():
                self.viewer.get_terminal_tree(self.editor.tm.get_mainparser().previous_version.parent)
            elif self.ui.rb_view_ast.isChecked():
                self.viewer.get_tree_image(self.editor.tm.get_mainparser().previous_version.parent, [], whitespaces, ast=True)
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
        self.viewer.create_pydot_graph(self.editor.tm.get_mainparser().graph)
        self.showImage(self.ui.gvStategraph, self.viewer.image)

    def showSingleState(self):
        self.viewer.show_single_state(self.editor.tm.get_mainparser().graph, int(self.ui.leSingleState.text()))
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

class LanguageView(QtGui.QDialog):
    def __init__(self, languages):
        QtGui.QDialog.__init__(self)
        self.ui = Ui_LanguageDialog()
        self.ui.setupUi(self)

        for l in languages:
            item = QListWidgetItem(self.ui.listWidget)
            item.setText(str(l))
            icon = QIcon.fromTheme("text-x-" + l.base.lower())
            if icon.isNull():
                icon = QIcon.fromTheme("text-x-source")
            item.setIcon(icon)

        self.ui.listWidget.item(0).setSelected(True)

    def getLanguage(self):
        return self.ui.listWidget.currentRow()

class Window(QtGui.QMainWindow):
    def __init__(self):
        QtGui.QMainWindow.__init__(self)
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)

        self.filename = None

        self.parseview = ParseView()
        self.parseview.setEditor(self.ui.frame)

        self.stateview = StateView()
        self.stateview.setEditor(self.ui.frame)

        self.connect(self.ui.cbShowLangBoxes, SIGNAL("clicked()"), self.ui.frame.update)

        for l in languages:
            self.ui.list_languages.addItem(str(l))

        self.ui.list_languages.item(0).setSelected(True)

        self.loadLanguage(0)

        self.connect(self.ui.list_languages, SIGNAL("itemClicked(QListWidgetItem *)"), self.loadLanguage)
        self.connect(self.ui.actionImport, SIGNAL("triggered()"), self.importfile)
        self.connect(self.ui.actionOpen, SIGNAL("triggered()"), self.openfile)
        self.connect(self.ui.actionSave, SIGNAL("triggered()"), self.savefile)
        self.connect(self.ui.actionSave_as, SIGNAL("triggered()"), self.savefileAs)
        self.connect(self.ui.actionRandomDel, SIGNAL("triggered()"), self.ui.frame.randomDeletion)
        self.connect(self.ui.actionSelect_font, SIGNAL("triggered()"), self.change_font)
        self.connect(self.ui.actionRun, SIGNAL("triggered()"), self.ui.frame.export_unipycation)
        self.connect(self.ui.actionUndoRandomDel, SIGNAL("triggered()"), self.ui.frame.undoDeletion)
        self.connect(self.ui.actionParse_Tree, SIGNAL("triggered()"), self.showParseView)
        self.connect(self.ui.actionStateGraph, SIGNAL("triggered()"), self.showStateView)
        self.connect(self.ui.actionAbout, SIGNAL("triggered()"), self.showAboutView)
        self.connect(self.ui.scrollArea.verticalScrollBar(), SIGNAL("valueChanged(int)"), self.ui.frame.sliderChanged)
        self.connect(self.ui.scrollArea.horizontalScrollBar(), SIGNAL("valueChanged(int)"), self.ui.frame.sliderXChanged)
        self.connect(self.ui.actionUndo, SIGNAL("triggered()"), self.undo)
        self.connect(self.ui.actionRedo, SIGNAL("triggered()"), self.redo)
        self.connect(self.ui.actionCopy, SIGNAL("triggered()"), self.copy)
        self.connect(self.ui.actionCut, SIGNAL("triggered()"), self.cut)
        self.connect(self.ui.actionPaste, SIGNAL("triggered()"), self.paste)
        self.connect(self.ui.actionAdd_language_box, SIGNAL("triggered()"), self.show_lbox_menu)
        self.connect(self.ui.actionSelect_next_language_box, SIGNAL("triggered()"), self.select_next_lbox)
        self.connect(self.ui.actionNew, SIGNAL("triggered()"), self.newfile)
        self.connect(self.ui.actionExit, SIGNAL("triggered()"), QApplication.quit)

        self.ui.menuWindow.addAction(self.ui.dockWidget_2.toggleViewAction())
        self.ui.menuWindow.addAction(self.ui.dockWidget_3.toggleViewAction())

        self.ui.frame.setFocus(True)

        self.viewer = Viewer("pydot")

    def select_next_lbox(self):
        self.ui.frame.tm.leave_languagebox()
        self.ui.frame.update()

    def show_lbox_menu(self):
        self.ui.frame.showLanuageBoxMenu()
        self.ui.frame.update()

    def redo(self):
        self.ui.frame.tm.key_shift_ctrl_z()
        self.ui.frame.update()
        self.btReparse([])

    def undo(self):
        self.ui.frame.tm.key_ctrl_z()
        self.ui.frame.update()
        self.btReparse([])

    def cut(self):
        text = self.ui.frame.tm.cutSelection()
        QApplication.clipboard().setText(text)
        self.ui.frame.update()

    def copy(self):
        text = self.ui.frame.tm.copySelection()
        if text:
            QApplication.clipboard().setText(text)
            self.ui.frame.update()

    def paste(self):
        text = QApplication.clipboard().text()
        self.ui.frame.tm.pasteText(text)
        self.ui.frame.update()

    def showAboutView(self):
        about = AboutView()
        about.exec_()

    def showStateView(self):
        self.stateview.show()

    def showParseView(self):
        self.parseview.show()

    def importfile(self, filename):
        if filename:
            text = open(filename, "r").read()
            # for some reason text has an additional newline
            if text[-1] in ["\n", "\r"]:
                text = text[:-1]
            # key simulated opening
            self.ui.frame.insertTextNoSim(text)
            self.btReparse(None)
            self.ui.frame.update()

    def change_font(self):
        font = QFontDialog.getFont(self.ui.frame.font)
        self.ui.frame.change_font(font)
        self.ui.fLinenumbers.change_font(font)

    def newfile(self):
        lview = LanguageView(languages)
        result = lview.exec_()
        if result:
            self.filename = None
            self.loadLanguage(lview.getLanguage())

    def savefile(self):
        if self.filename:
            self.ui.frame.saveToJson(self.filename)
        else:
            self.savefileAs()

    def savefileAs(self):
        filename = QFileDialog.getSaveFileName()
        if filename:
            self.ui.frame.saveToJson(filename)
            self.filename = filename

    def openfile(self):
        filename = QFileDialog.getOpenFileName()
        if filename and filename.endsWith(".eco"):
            self.ui.frame.loadFromJson(filename)
            self.ui.frame.update()
            self.filename = filename
        else: # import
            self.importfile(filename)

    def loadLanguage(self, index):
        self.language = languages[index]
        self.main_language = self.language.name
        self.btUpdateGrammar()
        self.ui.frame.setFocus(Qt.OtherFocusReason)

    def btUpdateGrammar(self):
        whitespaces = self.ui.cb_add_implicit_ws.isChecked()
        if isinstance(self.language, Language):
            new_grammar = str(self.language.grammar)
            new_priorities = str(self.language.priorities)
            self.lrp = IncParser(new_grammar, 1, whitespaces)
            self.lrp.init_ast()
            lexer = IncrementalLexer(new_priorities)
            self.ui.frame.reset()
            self.ui.frame.set_mainlanguage(self.lrp, lexer, self.main_language)
        elif isinstance(self.language, EcoGrammar):
            bootstrap = BootstrapParser(lr_type=1, whitespaces=whitespaces)
            bootstrap.parse(self.language.grammar)
            self.ui.frame.set_mainlanguage(bootstrap.incparser, bootstrap.inclexer, self.language.name)
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
