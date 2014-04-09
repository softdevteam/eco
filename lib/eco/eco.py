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
from gui.finddialog import Ui_Dialog as Ui_FindDialog
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
from editortab import EditorTab

def print_var(name, value):
    print("%s: %s" % (name, value))

BODY_FONT = "Monospace"
BODY_FONT_SIZE = 9

class GlobalFont(object):
    def __init__(self, font, size):
        font = QtGui.QFont(font, size)
        self.setfont(font)

    def setfont(self, font):
        self.font = font
        self.fontm = QtGui.QFontMetrics(self.font)
        self.fontht = self.fontm.height() + 3
        self.fontwt = self.fontm.width(" ")

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
    def __init__(self, window):
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

        self.window = window

    def refresh(self):
        editor = self.window.getEditor()
        whitespaces = self.ui.cb_toggle_ws.isChecked()
        if self.ui.cb_toggle_ast.isChecked():
            if self.ui.rb_view_parsetree.isChecked():
                self.viewer.get_tree_image(editor.tm.get_mainparser().previous_version.parent, [], whitespaces)
            elif self.ui.rb_view_linetree.isChecked():
                self.viewer.get_terminal_tree(editor.tm.get_mainparser().previous_version.parent)
            elif self.ui.rb_view_ast.isChecked():
                self.viewer.get_tree_image(editor.tm.get_mainparser().previous_version.parent, [], whitespaces, ast=True)
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
        editor = self.window.getEditor()
        whitespaces = self.ui.cb_toggle_ws.isChecked()
        nodes, _, _ = editor.get_nodes_from_selection()
        if len(nodes) == 0:
            return
        start = nodes[0]
        end = nodes[-1]
        ast = editor.lrp.previous_version
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
    def __init__(self, window):
        QtGui.QMainWindow.__init__(self)
        self.ui = Ui_StateView()
        self.ui.setupUi(self)

        self.viewer = Viewer("pydot")

        self.connect(self.ui.btShowSingleState, SIGNAL("clicked()"), self.showSingleState)
        self.connect(self.ui.btShowWholeGraph, SIGNAL("clicked()"), self.showWholeGraph)

        self.window = window

    def showWholeGraph(self):
        editor = self.window.getEditor()
        self.viewer.create_pydot_graph(editor.tm.get_mainparser().graph)
        self.showImage(self.ui.gvStategraph, self.viewer.image)

    def showSingleState(self):
        editor = self.window.getEditor()
        self.viewer.show_single_state(editor.tm.get_mainparser().graph, int(self.ui.leSingleState.text()))
        self.showImage(self.ui.gvStategraph, self.viewer.image)

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

class FindDialog(QtGui.QDialog):
    def __init__(self):
        QtGui.QDialog.__init__(self)
        self.ui = Ui_FindDialog()
        self.ui.setupUi(self)
        self.ui.buttonBox.button(QDialogButtonBox.Ok).setText("Find")
        self.ui.buttonBox.button(QDialogButtonBox.Ok).setIcon(QIcon.fromTheme("find"))

    def getText(self):
        return self.ui.leText.text()

    def focus(self):
        self.ui.leText.setFocus(True)
        self.ui.leText.selectAll()

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

    def getWhitespace(self):
        return self.ui.cb_add_implicit_ws.isChecked()

class Window(QtGui.QMainWindow):


    def __init__(self):
        QtGui.QMainWindow.__init__(self)
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)

        self.filename = None

        # XXX show current file in views
        self.parseview = ParseView(self)

        self.stateview = StateView(self)

        self.connect(self.ui.actionImport, SIGNAL("triggered()"), self.importfile)
        self.connect(self.ui.actionOpen, SIGNAL("triggered()"), self.openfile)
        self.connect(self.ui.actionSave, SIGNAL("triggered()"), self.savefile)
        self.connect(self.ui.actionSave_as, SIGNAL("triggered()"), self.savefileAs)
        self.connect(self.ui.actionSelect_font, SIGNAL("triggered()"), self.change_font)
        self.connect(self.ui.actionRun, SIGNAL("triggered()"), self.run_subprocess)
        self.connect(self.ui.actionParse_Tree, SIGNAL("triggered()"), self.showParseView)
        self.connect(self.ui.actionStateGraph, SIGNAL("triggered()"), self.showStateView)
        self.connect(self.ui.actionAbout, SIGNAL("triggered()"), self.showAboutView)
        self.connect(self.ui.actionUndo, SIGNAL("triggered()"), self.undo)
        self.connect(self.ui.actionRedo, SIGNAL("triggered()"), self.redo)
        self.connect(self.ui.actionCopy, SIGNAL("triggered()"), self.copy)
        self.connect(self.ui.actionCut, SIGNAL("triggered()"), self.cut)
        self.connect(self.ui.actionPaste, SIGNAL("triggered()"), self.paste)
        self.connect(self.ui.actionFind, SIGNAL("triggered()"), self.find)
        self.connect(self.ui.actionAdd_language_box, SIGNAL("triggered()"), self.show_lbox_menu)
        self.connect(self.ui.actionSelect_next_language_box, SIGNAL("triggered()"), self.select_next_lbox)
        self.connect(self.ui.actionNew, SIGNAL("triggered()"), self.newfile)
        self.connect(self.ui.actionExit, SIGNAL("triggered()"), self.quit)
        self.connect(self.ui.tabWidget, SIGNAL("tabCloseRequested(int)"), self.closeTab)
        self.connect(self.ui.tabWidget, SIGNAL("currentChanged(int)"), self.tabChanged)


        self.ui.menuWindow.addAction(self.ui.dockWidget_2.toggleViewAction())
        self.ui.menuWindow.addAction(self.ui.dockWidget.toggleViewAction())

        self.viewer = Viewer("pydot")

        self.finddialog = FindDialog()

    def run_subprocess(self):
        self.ui.teConsole.clear()
        self.thread.start()

    def show_output(self, string):
        self.ui.teConsole.append(string)

    def select_next_lbox(self):
        self.getEditor().tm.leave_languagebox()
        self.getEditor().update()

    def show_lbox_menu(self):
        self.getEditor().showLanuageBoxMenu()
        self.getEditor().update()

    def find(self):
        self.finddialog.focus()
        result = self.finddialog.exec_()
        if result:
            text = self.finddialog.getText()
            self.getEditor().tm.find_text(text)
            self.getEditor().update()
            self.btReparse([])
            self.getEditorTab().keypress()

    def redo(self):
        self.getEditor().tm.key_shift_ctrl_z()
        self.getEditor().update()
        self.btReparse([])

    def undo(self):
        self.getEditor().tm.key_ctrl_z()
        self.getEditor().update()
        self.btReparse([])

    def cut(self):
        text = self.getEditor().tm.cutSelection()
        QApplication.clipboard().setText(text)
        self.getEditor().update()

    def copy(self):
        text = self.getEditor().tm.copySelection()
        if text:
            QApplication.clipboard().setText(text)
            self.getEditor().update()

    def paste(self):
        text = QApplication.clipboard().text()
        self.getEditor().tm.pasteText(text)
        self.getEditor().update()

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
            self.getEditor().insertTextNoSim(text)
            self.btReparse(None)
            self.getEditor().update()

    def change_font(self):
        gfont = QApplication.instance().gfont
        font = QFontDialog.getFont(gfont.font)
        gfont.setfont(font[0])

    def newfile(self):
        # create new nodeeditor
        lview = LanguageView(languages)
        result = lview.exec_()
        if result:
            etab = EditorTab()
            lang = languages[lview.getLanguage()]
            etab.set_language(lang, lview.getWhitespace())
            self.ui.tabWidget.addTab(etab, "[No name]")
            self.ui.tabWidget.setCurrentWidget(etab)
            etab.editor.setFocus(Qt.OtherFocusReason)

    def savefile(self):
        if self.getEditorTab().filename:
            self.getEditor().saveToJson(self.getEditorTab().filename)
        else:
            self.savefileAs()

    def savefileAs(self):
        filename = QFileDialog.getSaveFileName()
        if filename:
            self.getEditor().saveToJson(filename)
            self.getEditorTab().filename = filename

    def openfile(self):
        filename = QFileDialog.getOpenFileName()
        if filename:
            if filename.endsWith(".eco") or filename.endsWith(".nb"):
                etab = EditorTab()

                etab.editor.loadFromJson(filename)
                etab.editor.update()
                etab.filename = filename

                self.ui.tabWidget.addTab(etab, os.path.basename(str(filename)))
                self.ui.tabWidget.setCurrentWidget(etab)
                etab.editor.setFocus(Qt.OtherFocusReason)
            else: # import
                self.newfile()
                self.importfile(filename)

    def closeTab(self, index):
        etab = self.ui.tabWidget.widget(index)
        if not etab.changed():
            self.ui.tabWidget.removeTab(index)
            return
        mbox = QMessageBox()
        mbox.setText("Save changes?")
        mbox.setInformativeText("Do you want to save your changes?")
        mbox.setStandardButtons(QMessageBox.Save | QMessageBox.Discard | QMessageBox.Cancel)
        mbox.setDefaultButton(QMessageBox.Save)
        ret = mbox.exec_()
        if(ret == QMessageBox.Save):
            self.savefile()
            self.ui.tabWidget.removeTab(index)
        elif(ret == QMessageBox.Discard):
            self.ui.tabWidget.removeTab(index)

    def tabChanged(self, index):
        self.btReparse()

    def closeEvent(self, event):
        self.quit()
        event.ignore()

    def quit(self):
        for i in reversed(range(self.ui.tabWidget.count())):
            self.ui.tabWidget.setCurrentIndex(i)
            self.closeTab(i)
        if self.ui.tabWidget.count() == 0:
            QApplication.quit()

    def getEditor(self):
        etab = self.ui.tabWidget.currentWidget()
        if etab:
            return etab.editor
        else:
            return None

    def getEditorTab(self):
        return self.ui.tabWidget.currentWidget()

    def btReparse(self, selected_node=[]):
        results = []
        self.ui.list_parsingstatus.clear()
        editor = self.getEditor()
        if editor is None:
            return
        for parser, lexer, lang, _ in editor.tm.parsers:
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
        self.showAst(selected_node)

    def showAst(self, selected_node):
        self.parseview.refresh()

    def showLookahead(self):
        #l = self.ui.frame.tm.getLookaheadList()
        #self.ui.lineEdit.setText(", ".join(l))
        pass

def main():
    app = QtGui.QApplication(sys.argv)
    app.setStyle('gtk')
    app.gfont = GlobalFont(BODY_FONT, BODY_FONT_SIZE)
    window=Window()
    t = SubProcessThread(window, app)
    window.thread = t
    window.connect(window.thread, t.signal, window.show_output)

    window.show()
    t.wait()
    sys.exit(app.exec_())

class SubProcessThread(QThread):
    def __init__(self, window, parent):
        QThread.__init__(self, parent=parent)
        self.window = window
        self.signal = QtCore.SIGNAL("output")

    def run(self):
        p = self.window.getEditor().export_unipycation()
        for line in iter(p.stdout.readline, b''):
            self.emit(self.signal, line.rstrip())

if __name__ == "__main__":
    main()
