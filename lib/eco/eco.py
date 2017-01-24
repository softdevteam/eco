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

from __future__ import print_function
import subprocess, sys

try:
    import py
except ImportError:
    sys.stderr.write("""Error: can't import the py module. Typically this can be installed with:
  pip install py

More detailed install instructions for py can be found at:
  http://pylib.readthedocs.org/en/latest/install.html
""")
    sys.exit(1)

from PyQt4 import QtCore
from PyQt4.QtCore import *
from PyQt4 import QtGui
from PyQt4.QtGui import *
from PyQt4 import uic

if not QtGui.QIcon.hasThemeIcon("document-new"):
    # attempt to fall back on generic icon theme
    QtGui.QIcon.setThemeName("gnome")

from grammar_parser.plexer import PriorityLexer
from incparser.incparser import IncParser
from inclexer.inclexer import IncrementalLexer
from viewer import Viewer

from grammar_parser.gparser import Terminal, MagicTerminal, IndentationTerminal, Nonterminal

from incparser.astree import TextNode, BOS, EOS, ImageNode, FinishSymbol

from grammars.grammars import languages, newfile_langs, submenu_langs, lang_dict, Language, EcoGrammar
import os
import math

import syntaxhighlighter
import editor

from nodeeditor import NodeEditor
from editortab import EditorTab

from lspace_ext import view_ecodoc_in_lspace

import logging
from debug import Debugger

Ui_MainWindow, _     = uic.loadUiType('gui/gui.ui')
Ui_ParseTree, _      = uic.loadUiType('gui/parsetree.ui')
Ui_StateView, _      = uic.loadUiType('gui/stateview.ui')
Ui_About, _          = uic.loadUiType('gui/about.ui')
Ui_InputLog, _       = uic.loadUiType('gui/inputlog.ui')
Ui_FindDialog, _     = uic.loadUiType('gui/finddialog.ui')
Ui_LanguageDialog, _ = uic.loadUiType('gui/languagedialog.ui')
Ui_Settings, _       = uic.loadUiType('gui/settings.ui')
Ui_Preview, _        = uic.loadUiType('gui/preview.ui')
Ui_Breakpoint, _     = uic.loadUiType('gui/breakpoint.ui')

def print_var(name, value):
    print("%s: %s" % (name, value))

def makelambda(func, arg):
    return lambda: func(arg)

class GlobalFont(object):
    def __init__(self, font, size):
        font = QtGui.QFont(font, size)
        self.setfont(font)

    def setfont(self, font):
        self.font = font
        self.fontm = QtGui.QFontMetrics(self.font)
        self.fontht = self.fontm.height()
        self.fontwt = self.fontm.width(" "*99)/99.0
        self.fontd = self.fontm.descent()

class ParseView(QtGui.QMainWindow):
    def __init__(self, window):
        QtGui.QMainWindow.__init__(self, window)
        self.ui = Ui_ParseTree()
        self.ui.setupUi(self)

        self.connect(self.ui.cb_fit_ast, SIGNAL("clicked()"), self.refresh)
        self.connect(self.ui.cb_toggle_ast, SIGNAL("clicked()"), self.refresh)
        self.connect(self.ui.cb_toggle_ws, SIGNAL("clicked()"), self.refresh)
        self.connect(self.ui.bt_show_sel_ast, SIGNAL("clicked()"), self.showAstSelection)
        self.connect(self.ui.rb_view_parsetree, SIGNAL("clicked()"), self.refresh)
        self.connect(self.ui.rb_view_linetree, SIGNAL("clicked()"), self.refresh)
        self.connect(self.ui.rb_view_ast, SIGNAL("clicked()"), self.refresh)
        self.connect(self.ui.comboBox, SIGNAL("activated(const QString&)"), self.change_version)

        self.viewer = Viewer("pydot")
        self.ui.graphicsView.setRenderHints(QPainter.Antialiasing | QPainter.SmoothPixmapTransform | QPainter.TextAntialiasing)
        self.ui.graphicsView.wheelEvent = self.gvWheelEvent
        self.zoom = 1.0

        self.window = window

    def change_version(self, text):
        self.redraw()

    def refresh(self):
        editor = self.window.getEditor()
        self.version = editor.tm.version
        self.ui.comboBox.clear()
        for v in xrange(editor.tm.get_max_version()):
            self.ui.comboBox.addItem(QString(str(v+1)))
        self.ui.comboBox.setCurrentIndex(editor.tm.get_max_version()-1)
        self.redraw()

    def redraw(self):
        editor = self.window.getEditor()
        whitespaces = self.ui.cb_toggle_ws.isChecked()
        if self.ui.cb_toggle_ast.isChecked():
            if self.ui.rb_view_parsetree.isChecked():
                self.viewer.get_tree_image(editor.tm.main_lbox, [], whitespaces, version=int(self.ui.comboBox.currentText()))
            elif self.ui.rb_view_linetree.isChecked():
                self.viewer.get_terminal_tree(editor.tm.main_lbox)
            elif self.ui.rb_view_ast.isChecked():
                self.viewer.get_tree_image(editor.tm.main_lbox, [], whitespaces, version=int(self.ui.comboBox.currentText()), ast=True)
            self.showImage(self.ui.graphicsView, self.viewer.image)

    def showImage(self, graphicsview, imagefile):
        scene = QGraphicsScene()
        item = QGraphicsPixmapItem(QPixmap(imagefile))
        item.setTransformationMode(Qt.SmoothTransformation)
        scene.addItem(item);
        graphicsview.setScene(scene)
        graphicsview.resetMatrix()
        if self.ui.cb_fit_ast.isChecked():
            self.fitInView(graphicsview)

    def gvWheelEvent(self, event):
        if event.modifiers() == Qt.ControlModifier:
            transform = self.ui.graphicsView.transform()
            if event.delta() > 0:
                self.zoom /= 0.9
            else:
                self.zoom *= 0.9
            transform.reset()
            transform.scale(self.zoom, self.zoom)
            self.ui.graphicsView.setTransform(transform)
        else:
            QGraphicsView.wheelEvent(self.ui.graphicsView, event)
        event.ignore()

    def fitInView(self, graphicsview):
        graphicsview.fitInView(graphicsview.sceneRect(), Qt.KeepAspectRatio)

    def showAstSelection(self):
        editor = self.window.getEditor()
        whitespaces = self.ui.cb_toggle_ws.isChecked()
        nodes, _, _ = editor.tm.get_nodes_from_selection()
        if len(nodes) == 0:
            return
        start = nodes[0]
        end = nodes[-1]
        ast = editor.tm.get_mainparser().previous_version
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

class SettingsView(QtGui.QMainWindow):
    def __init__(self, window):
        QtGui.QMainWindow.__init__(self)
        self.ui = Ui_Settings()
        self.ui.setupUi(self)

        self.connect(self.ui.buttonBox, SIGNAL("accepted()"), self.accept)
        self.connect(self.ui.buttonBox, SIGNAL("rejected()"), self.reject)
        # Appearance pane.
        self.connect(self.ui.app_foreground, SIGNAL("clicked()"), self.pick_color)
        self.connect(self.ui.app_background, SIGNAL("clicked()"), self.pick_color)
        # Profiling pane.
        self.connect(self.ui.heatmap_low, SIGNAL("clicked()"), self.pick_color)
        self.connect(self.ui.heatmap_high, SIGNAL("clicked()"), self.pick_color)
        # PyHyp pane.
        self.connect(self.ui.btpyhyp, SIGNAL("clicked()"), self.choose_file_or_dir)
        self.connect(self.ui.btpypyprefix, SIGNAL("clicked()"), self.choose_file_or_dir)
        # Unipycation pane.
        self.connect(self.ui.btunipycation, SIGNAL("clicked()"), self.choose_file_or_dir)
        # L-Space pane.
        self.connect(self.ui.btlspaceroot, SIGNAL("clicked()"), self.choose_file_or_dir)
        # JRuby pane.
        self.connect(self.ui.btjruby, SIGNAL("clicked()"), self.choose_file_or_dir)
        self.connect(self.ui.btjruby_load, SIGNAL("clicked()"), self.choose_file_or_dir)
        self.connect(self.ui.btruby_parser, SIGNAL("clicked()"), self.set_ruby_parser)
        # GraalVM pane.
        self.connect(self.ui.btgraalvm, SIGNAL("clicked()"), self.choose_file_or_dir)
        # Truffle pane.
        self.connect(self.ui.btsljar, SIGNAL("clicked()"), self.choose_file_or_dir)
        self.connect(self.ui.btjsjar, SIGNAL("clicked()"), self.choose_file_or_dir)
        self.connect(self.ui.bttrufflejar, SIGNAL("clicked()"), self.choose_file_or_dir)
        # Tab switcher.
        self.connect(self.ui.listWidget, SIGNAL("currentRowChanged(int)"), self.switch_view)
        # Defaults.
        self.foreground = None
        self.background = None
        self.heatmap_low = None
        self.heatmap_high = None
        self.window = window
        self.loadSettings()

    def switch_view(self, row):
        self.ui.stackedWidget.setCurrentIndex(self.ui.listWidget.currentRow())

    def showEvent(self, event):
        QWidget.showEvent(self, event)
        self.loadSettings()

    def _get_path_from_user(self, setting, is_file=True):
        settings = QSettings("softdev", "Eco")
        dir_ = os.path.dirname(str(settings.value(setting, "").toString()))
        if not dir_:
            dir_ = os.path.expanduser("~")
        if is_file:
            path = QFileDialog.getOpenFileName(self, "Choose file", directory=dir_)
        else:
            path = QFileDialog.getExistingDirectory(self, "Choose directory",
                                                    directory=dir_)
        if path:
            self.ui.__getattribute__(setting).setText(path)

    def choose_file_or_dir(self):
        if self.sender() is self.ui.btpyhyp:
            self._get_path_from_user("env_pyhyp", is_file=True)
        elif self.sender() is self.ui.btpypyprefix:
            self._get_path_from_user("env_pypyprefix", is_file=True)
        elif self.sender() is self.ui.btunipycation:
            self._get_path_from_user("env_unipycation", is_file=True)
        elif self.sender() is self.ui.btjruby:
            self._get_path_from_user("env_jruby", is_file=True)
        elif self.sender() is self.ui.btgraalvm:
            self._get_path_from_user("env_graalvm", is_file=True)
        elif self.sender() is self.ui.btsljar:
            self._get_path_from_user("env_sl_jar", is_file=True)
        elif self.sender() is self.ui.btjsjar:
            self._get_path_from_user("env_js_jar", is_file=True)
        elif self.sender() is self.ui.bttrufflejar:
            self._get_path_from_user("env_truffle_jar", is_file=True)
        elif self.sender() is self.ui.btpypyprefix:
            self._get_path_from_user("env_pypyprefix", is_file=False)
        elif self.sender() is self.ui.btlspaceroot:
            self._get_path_from_user("env_lspaceroot", is_file=False)
        elif self.sender() is self.ui.btjruby_load:
            self._get_path_from_user("env_jruby_load", is_file=False)

    def set_ruby_parser(self):
        settings = QSettings("softdev", "Eco")
        if self.sender() is self.ui.btruby_parser:
            settings.setValue("env_ruby_parser", self.ui.env_ruby_parser.text())

    def loadSettings(self):
        settings = QSettings("softdev", "Eco")
        # General pane.
        self.ui.gen_showconsole.setCheckState(settings.value("gen_showconsole", 0).toInt()[0])
        self.ui.gen_showparsestatus.setCheckState(settings.value("gen_showparsestatus", 2).toInt()[0])
        self.ui.gen_showhud.setCheckState(settings.value("gen_showhud", 0).toInt()[0])
        # Appearance pane.
        family = settings.value("font-family").toString()
        size = settings.value("font-size").toInt()[0]
        self.ui.app_fontfamily.setCurrentFont(QtGui.QFont(family, size))
        self.ui.app_fontsize.setValue(size)
        self.ui.app_theme.setCurrentIndex(settings.value("app_themeindex", 0).toInt()[0])
        self.ui.app_custom.setChecked(settings.value("app_custom", False).toBool())
        self.foreground = settings.value("app_foreground", "#000000").toString()
        self.background = settings.value("app_background", "#ffffff").toString()
        self.change_color(self.ui.app_foreground, self.foreground)
        self.change_color(self.ui.app_background, self.background)
        # Profiling pane.
        tool_info_family = settings.value("tool-font-family").toString()
        tool_info_size = settings.value("tool-font-size").toInt()[0]
        self.ui.tool_info_fontfamily.setCurrentFont(QtGui.QFont(tool_info_family, tool_info_size))
        self.ui.tool_info_fontsize.setValue(tool_info_size)
        self.heatmap_low = settings.value("heatmap_low", "#deebf7").toString()
        self.heatmap_high = settings.value("heatmap_high", "#3182bd").toString()
        self.ui.heatmap_alpha.setValue(settings.value("heatmap_alpha", 100).toInt()[0])
        self.ui.graalvm_pic_size.setValue(settings.value("graalvm_pic_size", 2).toInt()[0])
        self.change_color(self.ui.heatmap_low, self.heatmap_low)
        self.change_color(self.ui.heatmap_high, self.heatmap_high)
        # PyHyp pane.
        self.ui.env_pyhyp.setText(settings.value("env_pyhyp", "").toString())
        # Unipycation pane.
        self.ui.env_unipycation.setText(settings.value("env_unipycation", "").toString())
        self.ui.env_pypyprefix.setText(settings.value("env_pypyprefix", "").toString())
        # L-Space pane.
        self.ui.env_lspaceroot.setText(settings.value("env_lspaceroot", "").toString())
        # JRuby pane.
        self.ui.env_jruby.setText(settings.value("env_jruby", "").toString())
        self.ui.env_jruby_load.setText(settings.value("env_jruby_load", "").toString())
        self.ui.env_ruby_parser.setText(settings.value("env_ruby_parser", "").toString())
        # GraalVM pane.
        self.ui.env_graalvm.setText(settings.value("env_graalvm", "").toString())
        # Truffle pane.
        self.ui.env_sl_jar.setText(settings.value("env_sl_jar", "").toString())
        self.ui.env_js_jar.setText(settings.value("env_js_jar", "").toString())
        self.ui.env_truffle_jar.setText(settings.value("env_truffle_jar", "").toString())

    def saveSettings(self):
        settings = QSettings("softdev", "Eco")
        # General pane.
        settings.setValue("gen_showconsole", self.ui.gen_showconsole.checkState())
        settings.setValue("gen_showparsestatus", self.ui.gen_showparsestatus.checkState())
        settings.setValue("gen_showhud", self.ui.gen_showhud.checkState())
        settings.setValue("font-family", self.ui.app_fontfamily.currentFont().family())
        settings.setValue("font-size", self.ui.app_fontsize.value())
        settings.setValue("tool-font-family", self.ui.tool_info_fontfamily.currentFont().family())
        settings.setValue("tool-font-size", self.ui.tool_info_fontsize.value())

        settings.setValue("app_theme", self.ui.app_theme.currentText())
        settings.setValue("app_themeindex", self.ui.app_theme.currentIndex())
        settings.setValue("app_custom", self.ui.app_custom.isChecked())
        settings.setValue("app_foreground", self.foreground)
        settings.setValue("app_background", self.background)
        settings.setValue("highlight_line", self.ui.app_highlight_line.isChecked())
        # Profiling pane.
        settings.setValue("tool-font-family", self.ui.tool_info_fontfamily.currentFont().family())
        settings.setValue("tool-font-size", self.ui.tool_info_fontsize.value())
        settings.setValue("heatmap_low", self.heatmap_low)
        settings.setValue("heatmap_high", self.heatmap_high)
        settings.setValue("heatmap_alpha", self.ui.heatmap_alpha.value())
        # PyHyp pane.
        settings.setValue("env_pyhyp", self.ui.env_pyhyp.text())
        # Unipycation pane.
        settings.setValue("env_unipycation", self.ui.env_unipycation.text())
        settings.setValue("env_pypyprefix", self.ui.env_pypyprefix.text())
        # L-Space pane.
        settings.setValue("env_lspaceroot", self.ui.env_lspaceroot.text())
        # JRuby pane.
        settings.setValue("env_jruby", self.ui.env_jruby.text())
        settings.setValue("env_jruby_load", self.ui.env_jruby_load.text())
        settings.setValue("env_ruby_parser", self.ui.env_ruby_parser.text())
        # GraalVM pane.
        settings.setValue("env_graalvm", self.ui.env_graalvm.text())
        settings.setValue("graalvm_pic_size", self.ui.graalvm_pic_size.value())
        # Truffle pane.
        settings.setValue("env_sl_jar", self.ui.env_sl_jar.text())
        settings.setValue("env_js_jar", self.ui.env_js_jar.text())
        settings.setValue("env_truffle_jar", self.ui.env_truffle_jar.text())

    def accept(self):
        self.saveSettings()
        settings = QSettings("softdev", "Eco")

        gfont = QApplication.instance().gfont
        gfont.setfont(QFont(settings.value("font-family").toString(), settings.value("font-size").toInt()[0]))
        tool_info_font = QApplication.instance().tool_info_font
        tool_info_font.setfont(QFont(settings.value("tool-font-family").toString(), settings.value("tool-font-size").toInt()[0]))

        app = QApplication.instance()
        app.heatmap_low = settings.value("heatmap_low")
        app.heatmap_high = settings.value("heatmap_high")
        app.heatmap_alpha = settings.value("heatmap_alpha")
        app.graalvm_pic_size = settings.value("graalvm_pic_size")

        self.window.refreshTheme()
        self.close()

    def reject(self):
        self.close()

    def pick_color(self):
        color = QColorDialog.getColor()
        self.change_color(self.sender(), color.name())
        if self.sender() is self.ui.app_foreground:
            self.foreground = color.name()
        elif self.sender() is self.ui.app_background:
            self.background = color.name()
        elif self.sender() is self.ui.heatmap_low:
            self.heatmap_low = QColor(color.name())
        elif self.sender() is self.ui.heatmap_high:
            self.heatmap_high = QColor(color.name())

    def change_color(self, widget, color):
        """Change the background color of a widget.
        Used to ensure that the color picker widgets display the color
        that the user picked.
        """
        widget.setStyleSheet("background-color: %s" % (color))

class InputLogView(QtGui.QDialog):
    def __init__(self, parent):
        self.parent = parent
        QtGui.QDialog.__init__(self, parent)
        self.ui = Ui_InputLog()
        self.ui.setupUi(self)

        self.connect(self.ui.pushButton, SIGNAL("pressed()"), self.apply_log)

    def apply_log(self):
        log = self.ui.textEdit_2.toPlainText()
        self.tm.apply_inputlog(str(log))
        self.accept()

class AboutView(QtGui.QDialog):
    def __init__(self, parent):
        self.parent = parent
        QtGui.QDialog.__init__(self, parent)
        self.ui = Ui_About()
        self.ui.setupUi(self)

class PreviewDialog(QtGui.QDialog):
    def __init__(self, parent):
        self.parent = parent
        QtGui.QDialog.__init__(self, parent)
        self.ui = Ui_Preview()
        self.ui.setupUi(self)

        self.connect(self.ui.comboBox, SIGNAL("currentIndexChanged(const QString&)"), self.change)

    def change(self, index):
        if index == "Text":
            text = self.tm.export_as_text("/dev/null")
            self.ui.textEdit.setText(text)
        elif index == "Default":
            text = self.tm.export("/dev/null")
            if not text:
                text = ""
                self.show_export_fail_message()
            self.ui.textEdit.setText(text)

class FindDialog(QtGui.QDialog):
    def __init__(self, parent):
        self.parent = parent
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

class BreakpointDialog(QtGui.QDialog):
    def __init__(self, parent):
        QtGui.QMainWindow.__init__(self)
        self.parent = parent
        QtGui.QDialog.__init__(self)
        self.ui = Ui_Breakpoint()
        self.ui.setupUi(self)
        self.line_number = 0
        self.connect(self.ui.buttonBox, SIGNAL("accepted()"), self.accept)
        self.connect(self.ui.buttonBox, SIGNAL("rejected()"), self.reject)

    def accept(self):
        make_temp =  self.ui.bp_type.currentText() == 'Temporary'
        self.parent.debug_breakpoint(make_temp, self.line_number, False,
        self.ui.bp_condition.displayText(), str(self.ui.bp_ignore.value()), True)
        self.hide()

    def reject(self):
        self.hide()

class LanguageView(QtGui.QDialog):
    def __init__(self, parent, languages):
        self.parent = parent
        QtGui.QDialog.__init__(self)
        self.ui = Ui_LanguageDialog()
        self.ui.setupUi(self)

        # categorize languages
        d = {}
        self.d = d
        for l in newfile_langs:
            if d.has_key(l.base):
                d[l.base].append(l)
            else:
                d[l.base] = [l]

        for k in sorted(d.keys()):
            self.addLangItem(self.ui.listWidget, k)
        self.ui.listWidget.item(0).setSelected(True)

        for l in d[str(self.ui.listWidget.item(0).text())]:
            self.addLangItem(self.ui.listWidget_2, l)
        self.ui.listWidget_2.item(0).setSelected(True)

        self.connect(self.ui.listWidget, SIGNAL("currentRowChanged(int)"), self.row_changed)

    def row_changed(self, index):
        self.ui.listWidget_2.clear()
        for l in self.d[str(self.ui.listWidget.item(index).text())]:
            self.addLangItem(self.ui.listWidget_2, l)
        self.ui.listWidget_2.item(0).setSelected(True)
        self.ui.listWidget_2.setCurrentRow(0)

    def addLangItem(self, widget, name):
        item = QListWidgetItem(widget)
        item.setText(str(name))
        try:
            base = name.base
        except AttributeError:
            base = name
        if base.lower() == "html":
            icon = QIcon.fromTheme("text-html")
        else:
            icon = QIcon.fromTheme("text-x-" + base.lower())
        if icon.isNull():
            icon = QIcon.fromTheme("application-x-" + base.lower())
            if icon.isNull():
                icon = QIcon.fromTheme("text-x-generic")
        item.setIcon(icon)

    def getLanguage(self):
        row = self.ui.listWidget_2.currentRow()
        item = self.ui.listWidget_2.item(row).text()
        return lang_dict[str(item)]

    def getWhitespace(self):
        return True


from optparse import OptionParser
class Window(QtGui.QMainWindow):

    def __init__(self):
        QtGui.QMainWindow.__init__(self)
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)

        # XXX show current file in views
        self.parseview = ParseView(self)
        self.stateview = StateView(self)
        self.settingsview = SettingsView(self)
        self.previewdialog = PreviewDialog(self)
        self.breakpointdialog = BreakpointDialog(self)

        self.connect(self.ui.actionImport, SIGNAL("triggered()"), self.importfile)
        self.connect(self.ui.actionOpen, SIGNAL("triggered()"), self.openfile)
        self.connect(self.ui.actionSave, SIGNAL("triggered()"), self.savefile)
        self.connect(self.ui.actionSave_as, SIGNAL("triggered()"), self.savefileAs)
        self.connect(self.ui.actionExport, SIGNAL("triggered()"), self.export)
        self.connect(self.ui.actionExportAs, SIGNAL("triggered()"), self.exportAs)
        self.connect(self.ui.actionRun, SIGNAL("triggered()"), self.run_subprocess)
        self.connect(self.ui.actionDebug, SIGNAL("triggered()"), self.debug_subprocess)
        self.connect(self.ui.actionProfile, SIGNAL("triggered()"), self.profile_subprocess)
        self.connect(self.ui.actionVisualise_automatically, SIGNAL("triggered()"), self.run_background_tools)

        try:
            import pydot
            self.connect(self.ui.actionParse_Tree, SIGNAL("triggered()"), self.showParseView)
            self.connect(self.ui.actionStateGraph, SIGNAL("triggered()"), self.showStateView)
        except ImportError:
            sys.stderr.write("Warning: pydot not installed, so viewing of trees is disabled.\n")
            self.ui.actionParse_Tree.setEnabled(False)
            self.ui.actionStateGraph.setEnabled(False)
        self.connect(self.ui.actionPvShow, SIGNAL("triggered()"), self.showPygameTree)

        self.connect(self.ui.actionSettings, SIGNAL("triggered()"), self.showSettingsView)
        self.connect(self.ui.actionAbout, SIGNAL("triggered()"), self.showAboutView)
        self.connect(self.ui.actionPreview, SIGNAL("triggered()"), self.showPreviewDialog)
        self.connect(self.ui.actionUndo, SIGNAL("triggered()"), self.undo)
        self.connect(self.ui.actionRedo, SIGNAL("triggered()"), self.redo)
        self.connect(self.ui.actionSelect_all, SIGNAL("triggered()"), self.select_all)
        self.connect(self.ui.actionCopy, SIGNAL("triggered()"), self.copy)
        self.connect(self.ui.actionCut, SIGNAL("triggered()"), self.cut)
        self.connect(self.ui.actionPaste, SIGNAL("triggered()"), self.paste)
        self.connect(self.ui.actionFind, SIGNAL("triggered()"), self.find)
        self.connect(self.ui.actionFind_next, SIGNAL("triggered()"), self.find_next)
        self.connect(self.ui.actionAdd_language_box, SIGNAL("triggered()"), self.show_lbox_menu)
        self.connect(self.ui.actionSelect_next_language_box, SIGNAL("triggered()"), self.select_next_lbox)
        self.connect(self.ui.actionNew, SIGNAL("triggered()"), self.newfile)
        self.connect(self.ui.actionExit, SIGNAL("triggered()"), self.quit)
        self.connect(self.ui.tabWidget, SIGNAL("tabCloseRequested(int)"), self.closeTab)
        self.connect(self.ui.tabWidget, SIGNAL("currentChanged(int)"), self.tabChanged)
        self.connect(self.ui.actionCode_complete, SIGNAL("triggered()"), self.show_code_completion)
        #self.connect(self.ui.actionFull_reparse, SIGNAL("triggered()"), self.full_reparse)
        self.connect(self.ui.treeWidget, SIGNAL("itemDoubleClicked(QTreeWidgetItem *, int)"), self.click_parsers)
        self.connect(self.ui.actionShow_language_boxes, SIGNAL("triggered()"), self.update_editor)
        self.connect(self.ui.actionShow_namebinding, SIGNAL("triggered()"), self.update_editor)
        self.connect(self.ui.actionShow_indentation, SIGNAL("triggered()"), self.toogle_indentation)
        self.connect(self.ui.actionShow_lspaceview, SIGNAL("triggered()"), self.view_in_lspace)
        self.connect(self.ui.menuChange_language_box, SIGNAL("aboutToShow()"), self.showEditMenu)
        self.connect(self.ui.menuRecent_files, SIGNAL("aboutToShow()"), self.showRecentFiles)
        self.connect(self.ui.actionInput_log, SIGNAL("triggered()"), self.show_input_log)
        self.connect(self.ui.actionShow_tool_visualisations, SIGNAL("triggered()"), self.toggle_overlay)

        # Debug buttons
        self.connect(self.ui.actionContinue, SIGNAL("triggered()"), self.debug_continue)
        self.connect(self.ui.actionStop, SIGNAL("triggered()"), self.debug_stop)
        self.connect(self.ui.actionStepInto, SIGNAL("triggered()"), self.debug_step_into)
        self.connect(self.ui.actionStepOver, SIGNAL("triggered()"), self.debug_step_over)

        # Make sure the Project -> Profile and Project -> Run with Debugger menu items
        # only appear for languages that support it.
        self.connect(self.ui.tabWidget, SIGNAL("currentChanged(int)"), self.set_profiler_enabled)
        self.connect(self.ui.tabWidget, SIGNAL("currentChanged(int)"), self.set_debugger_enabled)

        self.ui.menuWindow.addAction(self.ui.dockWidget.toggleViewAction())
        self.ui.menuWindow.addAction(self.ui.dockWidget_2.toggleViewAction())
        self.ui.menuWindow.addAction(self.ui.dockWidget_3.toggleViewAction())

        self.ui.teConsole.setFont(QApplication.instance().gfont.font)
        self.connect(self.ui.teConsole, SIGNAL("customContextMenuRequested(QPoint)"), self.consoleContextMenu)
        self.ui.teConsole.setContextMenuPolicy(Qt.CustomContextMenu)

        # Set up HUD radio buttons.
        self.ui.hud_off_button.setChecked(True)
        self.connect(self.ui.hud_callgraph_button, SIGNAL("clicked()"), self.hud_callgraph_toggle)
        self.connect(self.ui.hud_eval_button, SIGNAL("clicked()"), self.hud_eval_toggle)
        self.connect(self.ui.hud_types_button, SIGNAL("clicked()"), self.hud_types_toggle)
        self.connect(self.ui.hud_heat_map_button, SIGNAL("clicked()"), self.hud_heat_map_toggle)
        self.connect(self.ui.hud_off_button, SIGNAL("clicked()"), self.hud_off_toggle)

        self.viewer = Viewer("pydot")
        self.pgviewer = None

        self.finddialog = FindDialog(self)

        self.last_dir = None

        self.debugging = False
        self.expression_list = []
        self.expression_num = 0
        # hide debug expression box
        self.ui.expressionBox.hide()

        # apply settings
        settings = QSettings("softdev", "Eco")
        if not settings.value("gen_showconsole", False).toBool():
            self.ui.dockWidget.hide()
        if not settings.value("gen_showparsestatus", True).toBool():
            self.ui.dockWidget_2.hide()
        if not settings.value("gen_showhud", False).toBool():
            self.ui.dockWidget_3.hide()

        # hardcoded key bindings for OS X
        if sys.platform == "darwin":
            self.ui.actionFind_next.setShortcut("Ctrl+G")
            self.ui.actionCode_complete.setShortcut("Meta+Space")

        # adjust icon size depending on DPI
        dpi = QApplication.desktop().physicalDpiX()
        if dpi > 96:
            iconsize = dpi / 96 * 16
            self.ui.toolBar.setIconSize(QtCore.QSize(iconsize, iconsize))

    def hud_callgraph_toggle(self):
        ed = self.getEditor()
        if ed is not None:
            ed.hud_show_callgraph()
            ed.update()

    def hud_eval_toggle(self):
        ed = self.getEditor()
        if ed is not None:
            ed.hud_show_eval()
            ed.update()

    def hud_types_toggle(self):
        ed = self.getEditor()
        if ed is not None:
            ed.hud_show_types()
            ed.update()

    def hud_heat_map_toggle(self):
        ed = self.getEditor()
        if ed is not None:
            ed.hud_show_heat_map()
            ed.update()

    def hud_off_toggle(self):
        ed = self.getEditor()
        if ed is not None:
            ed.hud_off()
            ed.update()

    def set_profiler_enabled(self):
        ed = self.getEditor()
        if (ed is not None) and (ed.tm is not None):
            self.ui.actionProfile.setEnabled(ed.tm.can_profile())

    def set_debugger_enabled(self):
        ed = self.getEditor()
        if (ed is not None) and (ed.tm is not None):
            self.ui.actionDebug.setEnabled(ed.tm.can_debug(ed.get_mainlanguage()))

    def run_background_tools(self):
        self.ui.actionShow_tool_visualisations.setChecked(True)
        ed_tab = self.getEditor()
        if ed_tab is not None:
            ed_tab.run_background_tools = True
        self.profiler_finished()

    def profiler_finished(self):
        self.profile_throbber.hide()
        ed_tab = self.getEditor()
        if ed_tab is None:
            return
        if self.ui.actionVisualise_automatically.isChecked():
            ed_tab.run_background_tools = True
            self.profile_subprocess()
        else:
            ed_tab.run_background_tools = False

    def debug_finished(self):
        self.ui.expressionBox.hide()
        self.debug_toggle_buttons(False)
        self.debugging = False
        self.debug_t.exit()
        self.getEditorTab().is_debugging(False)

    def draw_overlay(self, tool_data):
        """Send profiler or tool information to the overlay object."""
        ed_tab = self.getEditor()
        if self.ui.actionShow_tool_visualisations.isChecked():
            ed_tab.show_overlay()

    def toggle_overlay(self):
        ed_tab = self.getEditorTab()
        ed_tab.show_tool_visualisation = self.ui.actionShow_tool_visualisations.isChecked()
        ed_tab.editor.toggle_overlay()

    def show_overlay(self):
        self.ui.actionShow_tool_visualisations.setChecked(True)
        ed_tab = self.getEditorTab()
        ed_tab.editor.show_overlay()

    def hide_overlay(self):
        self.ui.actionShow_tool_visualisations.setChecked(False)
        ed_tab = self.getEditorTab()
        ed_tab.editor.hide_overlay()

    def consoleContextMenu(self, pos):
        def clear():
            self.ui.teConsole.clear()
        menu = self.ui.teConsole.createStandardContextMenu()
        menu.addSeparator()
        menu.addAction("Clear", clear)
        menu.exec_(self.ui.teConsole.mapToGlobal(pos))

    def contextMenu(self, pos):
        menu = QMenu(self)

        # add other contextmenu actions, e.g. copy, paste
        menu.addAction(self.ui.actionUndo)
        menu.addAction(self.ui.actionRedo)
        menu.addSeparator()
        menu.addAction(self.ui.actionCut)
        menu.addAction(self.ui.actionCopy)
        menu.addAction(self.ui.actionPaste)
        menu.addSeparator()
        menu.addAction(self.ui.actionFind)
        menu.addAction(self.ui.actionFind_next)
        menu.addSeparator()

        # create language box menues
        changemenu = QMenu("Change languagebox", self)
        changemenu.setIcon(QtGui.QIcon.fromTheme("reload"))
        self.getEditor().createSubgrammarMenu(changemenu, change=True)

        newmenu = QMenu("Add languagebox", self)
        newmenu.setIcon(QtGui.QIcon.fromTheme("list-add"))
        self.getEditor().createSubgrammarMenu(newmenu)

        menu.addMenu(changemenu)
        menu.addMenu(newmenu)
        menu.addAction(self.ui.actionSelect_next_language_box)
        menu.addSeparator()
        menu.addAction(self.ui.actionCode_complete)

        action = menu.exec_(self.getEditor().mapToGlobal(pos))
        if not action:
            return

        self.getEditor().sublanguage = action.data().toPyObject()
        self.getEditor().edit_rightnode = True
        if action.parentWidget() is newmenu:
            self.getEditor().create_languagebox()
        elif action.parentWidget() is changemenu:
            self.getEditor().change_languagebox()
        else:
            return
        self.getEditor().update()
        self.btReparse([])

    def showPygameTree(self):
        if not self.pgviewer:
            editor = self.getEditor()
            tree = editor.tm.main_lbox
            from pgviewer import PGViewer
            self.pgviewer = PGViewer(tree, editor.tm.version)
            self.pgviewer.max_version = self.getEditor().tm.get_max_version()
            self.pgviewer.run()
            return
        if not self.pgviewer.is_alive():
            self.pgviewer.max_version = self.getEditor().tm.get_max_version()
            self.pgviewer.version = self.getEditor().tm.version
            self.pgviewer.run()

    def showEditMenu(self):
        self.ui.menuChange_language_box.clear()
        if self.getEditor():
            self.getEditor().createSubgrammarMenu(self.ui.menuChange_language_box)
            self.ui.menuChange_language_box.update()
            for a in self.ui.menuChange_language_box.actions():
                self.connect(a, SIGNAL("triggered()"), self.actionChangeLBoxMenu)

    def showRecentFiles(self):
        settings = QSettings("softdev", "Eco")
        rf = settings.value("recent_files", []).toList()
        self.ui.menuRecent_files.clear()
        for f in rf:
            n = os.path.basename(str(f.toString()))
            fullname = f.toString()
            action = QAction(n, self.ui.menuRecent_files)
            action.triggered.connect(makelambda(self.openfile, fullname))
            self.ui.menuRecent_files.addAction(action)

    def actionChangeLBoxMenu(self):
        action = self.sender()
        if action:
            self.getEditor().sublanguage = action.data().toPyObject()
            self.getEditor().edit_rightnode = True
            self.getEditor().change_languagebox()
            self.getEditor().update()
            self.btReparse([])

    def parse_options(self):
        # parse options
        parser = OptionParser(usage="usage: python2.7 %prog FILE [options]")
        parser.add_option("-p", "--preload", action="store_true", default=False, help="Preload grammars")
        parser.add_option("-v", "--verbose", action="store_true", default=False, help="Show output")
        parser.add_option("-l", "--log", default="WARNING", help="Log level: INFO, WARNING, ERROR, DEBUG [default: %default]")
        parser.add_option("-e", "--export", action="store_true", default=False, help="Fast export files. Usage: --export [SOURCE] [DESTINATION]")
        parser.add_option("-f", "--fullexport", action="store_true", default=False, help="Export files. Usage: --fullexport [SOURCE] [DESTINATION]")
        parser.add_option("-g", "--grammar", action="store_true", default=None, help="Load external grammar. Usage: --grammar [GRAMMARFILE]")
        (options, args) = parser.parse_args()
        if options.preload:
            self.preload()
        if options.fullexport:
            source = args[0]
            dest = args[1]
            self.cli_export(source, dest, False)
        if options.export:
            source = args[0]
            dest = args[1]
            self.cli_export(source, dest, True)
        if options.grammar:
            self.load_external_grammar(args[0])
            return
        if len(args) > 0:
            for f in args:
                self.openfile(QString(f))

        if options.log.upper() in ["INFO", "WARNING", "ERROR", "DEBUG"]:
            loglevel=getattr(logging, options.log.upper())
        else:
            loglevel=logging.WARNING
        logging.basicConfig(format='%(levelname)s: %(message)s', filemode='w', level=loglevel)

    def preload(self):
        for l in newfile_langs + submenu_langs:
            try:
                print("Preloading %s" % (l.name))
                l.load()
            except AttributeError:
                pass

    def cli_export(self, source, dest, fast):
        print("Exporting...")
        print("    Source: %s" % source)
        print("    Destination: %s" % dest)

        from jsonmanager import JsonManager
        manager = JsonManager()
        language_boxes = manager.load(source)

        from treemanager import TreeManager
        self.tm = TreeManager()

        if fast:
            self.tm.fast_export(language_boxes, dest, source=source)
        else:
            self.tm.load_file(language_boxes)
            ex = self.tm.export(dest, source=source)
            if ex == False:
                self.show_export_fail_message()
        QApplication.quit()
        sys.exit(1)

    def show_languageboxes(self):
        if self.ui.actionShow_language_boxes.isChecked():
            return True
        return False

    def show_namebinding(self):
        if self.ui.actionShow_namebinding.isChecked():
            return True
        return False

    def toogle_indentation(self):
        if self.ui.actionShow_indentation.isChecked():
            QApplication.instance().showindent = True
        else:
            QApplication.instance().showindent = False
        self.getEditor().update()

    def view_in_lspace(self):
        settings = QSettings("softdev", "Eco")
        lspace_root = str(settings.value("env_lspaceroot").toString())
        lspace_root = lspace_root if lspace_root != "" else None
        ed = self.getEditorTab()
        if not ed:
            return
        view_ecodoc_in_lspace.view_in_lspace(self.getEditor().tm, lspace_root=lspace_root)

    def refreshTheme(self):
        self.ui.teConsole.setFont(QApplication.instance().gfont.font)
        for i in range(self.ui.tabWidget.count()):
            self.ui.tabWidget.widget(i).update_theme()

    def update_editor(self):
        self.getEditor().update()

    def run_subprocess(self):
        self.ui.teConsole.clear()
        self.thread.start()

    def debug_subprocess(self):
        if self.debugging:
            self.debugger.exit()
            self.debug_finished()
        self.ui.teConsole.clear()
        self.ui.dockWidget.show()
        self.ui.expressionBox.show()
        self.debug_t.start()
        self.emit(self.debugger.signal_start)
        self.debugging = True
        self.getEditorTab().is_debugging(True)

    def profile_subprocess(self):
        self.ui.teConsole.clear()
        self.ui.actionShow_tool_visualisations.setChecked(True)
        ed = self.getEditor()
        ed.tm.tool_data_is_dirty = False
        ed.overlay.clear_data()
        self.profile_throbber.show(self.ui.tabWidget.currentIndex())
        self.thread_prof.start()

    def show_output(self, string):
        self.ui.teConsole.append(string)

    def select_next_lbox(self):
        self.getEditor().tm.leave_languagebox()
        self.getEditor().update()

    def show_lbox_menu(self):
        self.getEditor().showLanguageBoxMenu()
        self.getEditor().update()

    def show_code_completion(self):
        self.getEditor().showCodeCompletion()

    def full_reparse(self):
        self.getEditor().tm.full_reparse()

    def find(self):
        self.finddialog.focus()
        result = self.finddialog.exec_()
        if result:
            text = self.finddialog.getText()
            self.getEditor().tm.find_text(text)
            self.getEditor().update()
            self.btReparse([])
            self.getEditorTab().keypress()

    def find_next(self):
        text = self.finddialog.getText()
        if text:
            self.getEditor().tm.find_text(text)
            self.getEditor().update()
            self.btReparse([])
            self.getEditorTab().keypress(center=True)

    def click_parsers(self, item, col):
        self.getEditor().tm.jump_to_error(item.parser)
        self.getEditor().update()
        self.btReparse([])
        self.getEditorTab().keypress(center=True)
        self.getEditor().setFocus(True)

    def redo(self):
        self.getEditor().tm.key_shift_ctrl_z()
        self.getEditor().update()
        self.btReparse([])
        self.getEditorTab().keypress()

    def undo(self):
        self.getEditor().undotimer.stop()
        self.getEditor().tm.key_ctrl_z()
        self.getEditor().update()
        self.btReparse([])
        self.getEditorTab().keypress()

    def cut(self):
        text = self.getEditor().tm.cutSelection()
        QApplication.clipboard().setText(text)
        self.getEditor().update()
        self.btReparse([])

    def copy(self):
        text = self.getEditor().tm.copySelection()
        if text:
            QApplication.clipboard().setText(text)
            self.getEditor().update()

    def paste(self):
        text = QApplication.clipboard().text()
        self.getEditor().tm.pasteText(text)
        self.getEditor().update()
        self.btReparse([])

    def select_all(self):
        editor = self.getEditor()
        editor.tm.select_all()
        editor.update()

    def show_input_log(self):
        if self.getEditor():
            v = InputLogView(self)
            v.tm = self.getEditor().tm
            v.ui.textEdit.setText("\n".join(self.getEditor().tm.input_log))
            v.exec_()

    def showAboutView(self):
        about = AboutView(self)
        about.exec_()

    def showStateView(self):
        self.stateview.show()

    def showParseView(self):
        self.parseview.show()

    def showSettingsView(self):
        self.settingsview.show()

    def showPreviewDialog(self):
        if self.getEditor():
            self.previewdialog.tm = self.getEditor().tm
            self.previewdialog.show()
            self.previewdialog.change(self.previewdialog.ui.comboBox.currentText())

    def importfile(self, filename):
        if filename:
            text = open(filename, "r").read()
            # for some reason text has an additional newline
            if text[-1] in ["\n", "\r"]:
                text = text[:-1]
            # key simulated opening
            self.getEditor().insertTextNoSim(text)
            #self.btReparse(None)
            #self.getEditor().update()

    def newfile(self):
        # create new nodeeditor
        lview = LanguageView(self, languages)
        result = lview.exec_()
        if result:
            etab = EditorTab()
            lang = lview.getLanguage()
            etab.set_language(lang, lview.getWhitespace())
            self.ui.tabWidget.addTab(etab, "[No name]")
            self.ui.tabWidget.setCurrentWidget(etab)
            etab.editor.setFocus(Qt.OtherFocusReason)
            etab.editor.setContextMenuPolicy(Qt.CustomContextMenu)
            etab.editor.customContextMenuRequested.connect(self.contextMenu)
            self.set_breakpoint_signals(etab)
            self.toggle_menu(True)
            return True
        return False

    def load_external_grammar(self, filename):
        from grammars.grammars import EcoFile, lang_dict
        etab = EditorTab()
        lang = "ExternalGrammar"
        tmpgrm = EcoFile(lang, filename, "")
        lang_dict[lang] = tmpgrm
        etab.set_language(tmpgrm, False)
        self.ui.tabWidget.addTab(etab, "[No name]")
        self.ui.tabWidget.setCurrentWidget(etab)
        etab.editor.setFocus(Qt.OtherFocusReason)
        etab.editor.setContextMenuPolicy(Qt.CustomContextMenu)
        etab.editor.customContextMenuRequested.connect(self.contextMenu)
        self.toggle_menu(True)

    def savefile(self):
        ed = self.getEditorTab()
        if not ed:
            return
        if self.getEditorTab().filename:
            self.getEditor().saveToJson(self.getEditorTab().filename)
            self.delete_swap()
        else:
            self.savefileAs()
        ed_ = self.getEditor()
        if ed_.run_background_tools:
            if self.thread_prof.isRunning():
                self.thread_prof.quit()
            self.profile_subprocess()

    def savefileAs(self):
        ed = self.getEditorTab()
        if not ed:
            return
        self.delete_swap()
        filename = QFileDialog.getSaveFileName(self, "Save File", self.get_last_dir(), "Eco files (*.eco *.nb);; All files (*.*)")
        if filename:
            self.save_last_dir(str(filename))
            self.add_to_recent_files(str(filename))
            self.getEditor().saveToJson(filename)
            self.getEditorTab().filename = filename
        ed_ = self.getEditor()
        if ed_.run_background_tools:
            if self.thread_prof.isRunning():
                self.thread_prof.quit()
            self.profile_subprocess()

    def delete_swap(self):
        if self.getEditorTab().filename is None:
            return
        swpfile = self.getEditorTab().filename + ".swp"
        if os.path.isfile(swpfile):
            os.remove(swpfile)

    def show_backup_msgbox(self, name):
        if not os.path.isfile(name):
            return "original"
        mbox = QMessageBox()
        mbox.setText("Swap file already exists")
        mbox.setInformativeText("Found a swap file by the name of '%s'. What do you want to do?" % (name,))
        btorg = mbox.addButton("Open original (overwrites swap file)", QMessageBox.AcceptRole)
        btswp = mbox.addButton("Open swap file", QMessageBox.ResetRole)
        btabort = mbox.addButton("Abort", QMessageBox.RejectRole)
        mbox.setDefaultButton(btabort)
        mbox.exec_()
        if(mbox.clickedButton() == btorg):
            return "original"
        elif(mbox.clickedButton() == btswp):
            return "swap"
        return "abort"

    def export(self):
        ed = self.getEditorTab()
        if not ed:
            return
        if not ed.export_path:
            ed.export_path = QFileDialog.getSaveFileName()
        if ed.export_path:
            ex = self.getEditor().tm.export(ed.export_path, source=ed.filename)
        if ex == False:
            self.show_export_fail_message()

    def exportAs(self):
        ed = self.getEditorTab()
        if not ed:
            return
        path = QFileDialog.getSaveFileName(self, "Export file", self.get_last_dir())
        if path:
            self.save_last_dir(str(path))
            ed.export_path = path
            ex = self.getEditor().tm.export(path, source=ed.filename)
        if ex == False:
            self.show_export_fail_message()

    def show_export_fail_message(self):
        QMessageBox.about(self, "Error", "Eco cannot execute/export this program because it is syntactically invalid.")

    def get_last_dir(self):
        settings = QSettings("softdev", "Eco")
        last_dir = settings.value("last_dir").toString()
        if last_dir:
            return last_dir
        return QDir.currentPath()

    def save_last_dir(self, filename):
        settings = QSettings("softdev", "Eco")
        settings.setValue("last_dir", filename)

    def add_to_recent_files(self, filename):
        settings = QSettings("softdev", "Eco")
        prev = settings.value("recent_files", []).toList()
        if filename in prev:
            prev.remove(filename)
        prev.insert(0, filename)
        if len(prev) > 10:
            prev.pop()
        settings.setValue("recent_files", prev)

    def openfile(self, filename=None):
        if not filename:
            filename = QFileDialog.getOpenFileName(self, "Open File", self.get_last_dir(), "Eco files (*.eco *.nb *.eco.bak);; All files (*.*)")
        if filename:
            self.save_last_dir(str(filename))
            self.add_to_recent_files(str(filename))
            if filename.endsWith(".eco") or filename.endsWith(".nb") or filename.endsWith(".eco.bak") or filename.endsWith(".eco.swp"):
                ret = self.show_backup_msgbox(filename + ".swp")
                if ret == "abort":
                    return
                elif ret == "swap":
                    filename += ".swp"
                etab = EditorTab()

                etab.editor.loadFromJson(filename)
                etab.editor.update()
                etab.filename = filename
                lang = etab.editor.get_mainlanguage()
                self.set_breakpoint_signals(etab)

                self.ui.tabWidget.addTab(etab, os.path.basename(str(filename)))
                self.ui.tabWidget.setCurrentWidget(etab)
                etab.editor.setFocus(Qt.OtherFocusReason)
            else: # import
                if self.newfile():
                    self.importfile(filename)
                    self.getEditorTab().update()
            self.toggle_menu(True)

    def closeTab(self, index):
        etab = self.ui.tabWidget.widget(index)
        if not etab.changed():
            self.delete_swap()
            self.ui.tabWidget.removeTab(index)
            return
        mbox = QMessageBox()
        mbox.setText("Save changes?")
        mbox.setInformativeText("Do you want to save your changes?")
        mbox.setStandardButtons(QMessageBox.Save | QMessageBox.Discard | QMessageBox.Cancel)
        mbox.setDefaultButton(QMessageBox.Save)
        ret = mbox.exec_()
        self.delete_swap()
        if(ret == QMessageBox.Save):
            self.savefile()
            self.ui.tabWidget.removeTab(index)
        elif(ret == QMessageBox.Discard):
            self.ui.tabWidget.removeTab(index)

    def tabChanged(self, index):
        ed_tab = self.getEditorTab()
        if ed_tab is not None:
            if ed_tab.editor.is_overlay_visible():
                self.ui.actionShow_tool_visualisations.setChecked(True)
            else:
                self.ui.actionShow_tool_visualisations.setChecked(False)
            self.ui.actionVisualise_automatically.setChecked(ed_tab.editor.run_background_tools)

            if ed_tab.editor.tm.get_mainparser().graph:
                self.ui.actionStateGraph.setEnabled(True)
            else:
                self.ui.actionStateGraph.setEnabled(False)
            lang = ed_tab.editor.get_mainlanguage()
        else:
            self.toggle_menu(False)
        self.btReparse()

    def closeEvent(self, event):
        self.quit()
        event.ignore()

    def quit(self):
        if self.debugging:
            if self.debug_t.isRunning():
                self.debug_t.quit()
        for i in reversed(range(self.ui.tabWidget.count())):
            self.ui.tabWidget.setCurrentIndex(i)
            self.closeTab(i)
        if self.ui.tabWidget.count() == 0:
            if self.pgviewer and self.pgviewer.is_alive():
                self.pgviewer.quit()
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
        self.ui.treeWidget.clear()
        editor = self.getEditor()
        if editor is None:
            return
        nested = {}
        for parser, lexer, lang, _, _ in editor.tm.parsers:
            #import cProfile
            #cProfile.runctx("parser.inc_parse(self.ui.frame.line_indents)", globals(), locals())
            root = parser.previous_version.parent
            lbox_terminal = root.get_magicterminal()
            if lbox_terminal:
                try:
                    l = nested.get(lbox_terminal.parent_lbox, [])
                    l.append((parser,lexer,lang))
                    nested[lbox_terminal.parent_lbox] = l
                except AttributeError,e:
                    print(e)
                    return
            else:
                l = nested.get(None, [])
                l.append((parser,lexer,lang))
                nested[None] = l

        self.add_parsingstatus(nested, None, self.ui.treeWidget)
        self.ui.treeWidget.expandAll()

        self.showAst(selected_node)
        if self.pgviewer:
            self.pgviewer.max_version = editor.tm.get_max_version()
            self.pgviewer.refresh(editor.tm.version)


    def add_parsingstatus(self, nested, root, parent):
        if not nested.has_key(root):
            return
        for parser, lexer, lang in nested[root]:
            status = parser.last_status
            qtreeitem = QTreeWidgetItem(parent)
            qtreeitem.setText(0, QString(lang))
            if status:
                qtreeitem.setIcon(0, QIcon("gui/accept.png"))
            else:
                qtreeitem.setIcon(0, QIcon("gui/exclamation.png"))
                enode = parser.error_node
                emsg = "Error on \"%s\"" % (enode.symbol.name,)
                qtreeitem.setToolTip(0, emsg)
            qtreeitem.parser = parser
            self.add_parsingstatus(nested, parser.previous_version.parent, qtreeitem)

    def showAst(self, selected_node):
        self.parseview.refresh()

    def showLookahead(self):
        pass

    def toggle_menu(self, enabled=True):
        self.ui.actionSave.setEnabled(enabled)
        self.ui.actionSave_as.setEnabled(enabled)
        self.ui.actionExport.setEnabled(enabled)
        self.ui.actionExportAs.setEnabled(enabled)
        self.ui.actionRun.setEnabled(enabled)
        self.ui.actionUndo.setEnabled(enabled)
        self.ui.actionRedo.setEnabled(enabled)
        self.ui.actionCopy.setEnabled(enabled)
        self.ui.actionPaste.setEnabled(enabled)
        self.ui.actionCut.setEnabled(enabled)
        self.ui.actionFind.setEnabled(enabled)
        self.ui.actionSelect_all.setEnabled(enabled)
        self.ui.actionFind_next.setEnabled(enabled)
        self.ui.actionAdd_language_box.setEnabled(enabled)
        self.ui.actionSelect_next_language_box.setEnabled(enabled)
        try:
            import pydot
            self.ui.actionParse_Tree.setEnabled(enabled)
        except ImportError:
            pass
        self.ui.actionCode_complete.setEnabled(enabled)
        self.ui.menuChange_language_box.setEnabled(enabled)
        self.ui.actionPreview.setEnabled(enabled)
        self.ui.actionInput_log.setEnabled(enabled)

        if enabled == False:
            self.ui.actionProfile.setEnabled(enabled)
            self.ui.actionDebug.setEnabled(enabled)
            self.ui.actionStateGraph.setEnabled(enabled)

    def debug_continue(self):
        self.emit(self.debugger.signal_command, "c")

    def debug_stop(self):
        self.emit(self.debugger.signal_command, "q")

    def debug_step_into(self):
        self.emit(self.debugger.signal_command, "s")

    def debug_step_over(self):
        self.emit(self.debugger.signal_command, "n")

    def debug_toggle_buttons(self, enable):
        self.ui.actionContinue.setEnabled(enable)
        self.ui.actionStop.setEnabled(enable)
        self.ui.actionStepInto.setEnabled(enable)
        self.ui.actionStepOver.setEnabled(enable)

    def debug_breakpoint(self, isTemp, number, from_click, 
        condition="", ignore=0, from_dialog=False):
        # If there is a breakpoint and the user double clicks it (from_click)
        # then the breakpoint should just be removed, don't make another one
        if self.debugging:
            removed_same_type = False
            removed_bp = False
            bp_number = self.debugger.get_breakpoints(False, number, False)
            removed_same_type = (isTemp == False)
            if not bp_number:
                bp_number = self.debugger.get_breakpoints(True, number, False)
                removed_same_type = (isTemp == True)
            if bp_number:
                # breakpoint exists, delete it
                self.debugger.run_command("cl " + str(bp_number))
                removed_bp = True
                output = ""
            if not ((removed_bp and removed_same_type) or
            (from_click and removed_bp)) or from_dialog:
                if isTemp:
                    output=self.debugger.run_command("tbreak " + str(number))
                else:
                    output=self.debugger.run_command("b " + str(number))
            if not output and not (condition or ignore):
                return None

            bp_index = output.split(" ")[2]
            try:
                int(bp_index)
            except ValueError:
                return
            if condition:
                self.debugger.run_command("condition " + bp_index
                + " " + str(condition))
            if int(ignore) > 0:
                self.debugger.run_command("ignore " + bp_index + " " + str(ignore))

    def debug_breakpoint_condition(self, number):
        """Open window to create breakpoint"""
        self.breakpointdialog.show()
        self.breakpointdialog.setWindowTitle("Set Breakpoint on line "+str(number))
        self.breakpointdialog.line_number = number

    def debug_expression(self):
        if self.ui.expressionBox.displayText():
            ex_input = self.ui.expressionBox.displayText()
            self.debugger.run_command("p " + str(ex_input))
            # Add expression to top of expression "stack" if it's not already there
            if self.expression_list.count(ex_input) > 0:
                if not self.expression_list[0] == ex_input:
                    self.expression_list.remove(ex_input)
                    self.expression_list.insert(0, ex_input)
            else:
                # If 10 or more items are in the list, remove the oldest entry
                if len(self.expression_list) >= 10:
                    self.expression_list.pop()
                self.expression_list.insert(0, ex_input)
            self.expression_num = -1
            self.ui.expressionBox.clear()

    def set_breakpoint_signals(self, etab):
        self.connect(etab, SIGNAL("breakpoint"), self.debug_breakpoint)
        self.connect(etab, SIGNAL("breakcondition"), self.debug_breakpoint_condition)

    def keyPressEvent(self, event):
        if self.debugging:
            if event.key() == QtCore.Qt.Key_Return or event.key() == QtCore.Qt.Key_Enter:
                self.debug_expression()
            elif event.key() == QtCore.Qt.Key_Down:
                # Next most recent expression
                self.change_expression(False)
            elif event.key() == QtCore.Qt.Key_Up:
                # Previous expression
                self.change_expression(True)

    def change_expression(self, previous):
        if len(self.expression_list) == 0:
            return None

        # Go through list of used expressions and show next or previous one in the input box
        if previous:
           if self.expression_num+1 < len(self.expression_list):
               self.expression_num += 1
        else:
           if self.expression_num-1 >= 0:
                self.expression_num -= 1

        self.ui.expressionBox.setText(self.expression_list[self.expression_num])

def main():
    app = QtGui.QApplication(sys.argv)
    app.setStyle('gtk')

    settings = QSettings("softdev", "Eco")
    if not settings.contains("font-family"):
        settings.setValue("font-family", "Monospace")
        settings.setValue("font-size", 9)
    if not settings.contains("tool-font-family"):
        settings.setValue("tool-font-family", "Monospace")
        settings.setValue("tool-font-size", 9)

    app.gfont = GlobalFont(settings.value("font-family").toString(), settings.value("font-size").toInt()[0])
    app.tool_info_font = GlobalFont(settings.value("tool-font-family").toString(), settings.value("tool-font-size").toInt()[0])

    if not settings.contains("heatmap_low"):
        settings.setValue("heatmap_low", QColor(222, 235, 247))
    if not settings.contains("heatmap_high"):
        settings.setValue("heatmap_high", QColor(49, 130, 189))
    if not settings.contains("heatmap_alpha"):
        settings.setValue("heatmap_alpha", 100)
    if not settings.contains("graalvm_pic_size"):
        settings.setValue("graalvm_pic_size", 2)

    app.heatmap_low = settings.value("heatmap_low")
    app.heatmap_high = settings.value("heatmap_high")
    app.heatmap_alpha = settings.value("heatmap_alpha")
    app.graalvm_pic_size = settings.value("graalvm_pic_size")

    app.showindent = False

    window=Window()
    t = SubProcessThread(window, app)
    window.thread = t
    window.thread_prof = ProfileThread(window, app)

    window.debug_t = QThread()
    window.debugger = Debugger(window)
    window.debugger.moveToThread(window.debug_t)

    window.profile_throbber = Throbber(window.ui.tabWidget)
    window.connect(window, window.debugger.signal_command, window.debugger.run_command)
    window.connect(window, window.debugger.signal_start, window.debugger.start_pdb)
    window.connect(window.debugger, window.debugger.signal_output, window.show_output)
    window.connect(window.debugger, window.debugger.signal_done, window.debug_finished)
    window.connect(window.debugger, window.debugger.signal_toggle_buttons, window.debug_toggle_buttons)
    window.connect(window.debugger, window.debugger.signal_execute_fail, window.show_export_fail_message)

    window.connect(window.thread, t.signal_execute_fail, window.show_export_fail_message)
    window.connect(window.thread, t.signal, window.show_output)
    window.connect(window.thread_prof, window.thread_prof.signal, window.show_output)
    # Connect the profiler (tool) thread to the throbber.
    window.connect(window.thread_prof,
                   window.thread_prof.signal_done,
                   window.profiler_finished)
    # Connect the profiler(tool) thread to the overlay which draws a heatmap
    # or other visualisation.
    window.connect(window.thread_prof,
                   window.thread_prof.signal_overlay,
                   window.draw_overlay)

    window.parse_options()
    window.show()
    t.wait()
    sys.exit(app.exec_())

class SubProcessThread(QThread):
    def __init__(self, window, parent):
        QThread.__init__(self, parent=parent)
        self.window = window
        self.signal = QtCore.SIGNAL("output")
        self.signal_execute_fail = QtCore.SIGNAL("executefail")

    def run(self):
        ed = self.window.getEditorTab()
        p = self.window.getEditor().export(run=True, source=str(ed.filename))
        lang = self.window.getEditor().get_mainlanguage()
        if p:
            for line in iter(p.stdout.readline, b''):
                if lang == "PHP + Python":
                    if line.startswith("  <?php{ "):
                        line = "  " + line[9:]
                self.emit(self.signal, line.rstrip())
        else:
            self.emit(self.signal_execute_fail)

class ProfileThread(QThread):
    def __init__(self, window, parent):
        QThread.__init__(self, parent=parent)
        self.window = window
        self.signal_done = QtCore.SIGNAL("finished")
        self.signal = QtCore.SIGNAL("output")
        self.signal_overlay = QtCore.SIGNAL("profile_overlay")
        self.signal_execute_fail = QtCore.SIGNAL("executefail")

    def run(self):
        ed = self.window.getEditorTab()
        p = self.window.getEditor().tm.export(path=str(ed.filename), profile=True)
        # Using read() here, rather than readline() because profiler output
        # often includes blank lines in the middle of the output.
        if p:
            text = p.stdout.read()
            self.emit(self.signal, text.strip())
            self.emit(self.signal_overlay, self.window.getEditor().tm.profile_data)
        else:
            self.emit(self.signal_overlay, None)
            self.emit(self.signal_execute_fail)
        self.emit(self.signal_done, None)


class Throbber(QLabel):
    """Throbber which displays in the right-hand corner of the tabbed notebook.
    Used to alert the user that a potentially long-running background
    profile is taking place.
    """
    def __init__(self, tab_bar):
        super(Throbber, self).__init__()
        self.tab_bar = tab_bar
        self.setAlignment(Qt.AlignCenter)
        self._movie = QMovie("gui/throbber.gif")
        self.setMovie(self._movie)

    def hide(self):
        """Hide throbber in right hand corner of tabbed notebook.
        """
        self._movie.stop()
        self.tab_bar.setCornerWidget(None, corner=Qt.TopRightCorner)
        super(Throbber, self).hide()

    def show(self, tab_index):
        """Display throbber in right hand corner of tabbed notebook.
        """
        self.tab_bar.setCornerWidget(self, corner=Qt.TopRightCorner)
        self._movie.start()
        super(Throbber, self).show()


if __name__ == "__main__":
    main()
