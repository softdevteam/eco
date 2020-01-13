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


import subprocess, sys

try:
    import __pypy__
    print("Warning: PyQt is currently not supported in PyPy. Some features thus have been disabled.")
except ImportError:
    pass

try:
    import py
except ImportError:
    sys.stderr.write("""Error: can't import the py module. Typically this can be installed with:
  pip install py

More detailed install instructions for py can be found at:
  http://pylib.readthedocs.org/en/latest/install.html
""")
    sys.exit(1)

from PyQt5 import QtCore
from PyQt5.QtCore import *
from PyQt5 import QtGui
from PyQt5.QtGui import *
from PyQt5 import uic
from PyQt5.QtWidgets import *

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

class ParseView(QMainWindow):
    def __init__(self, window):
        QMainWindow.__init__(self, window)
        self.ui = Ui_ParseTree()
        self.ui.setupUi(self)

        self.ui.cb_fit_ast.clicked.connect(self.refresh)
        self.ui.cb_toggle_ast.clicked.connect(self.refresh)
        self.ui.cb_toggle_ws.clicked.connect(self.refresh)
        self.ui.bt_show_sel_ast.clicked.connect(self.showAstSelection)
        self.ui.rb_view_parsetree.clicked.connect(self.refresh)
        self.ui.rb_view_linetree.clicked.connect(self.refresh)
        self.ui.rb_view_ast.clicked.connect(self.refresh)
        self.ui.comboBox.activated.connect(self.change_version)

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
        for v in range(editor.tm.get_max_version()):
            self.ui.comboBox.addItem(str(v+1))
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

class StateView(QMainWindow):
    def __init__(self, window):
        QMainWindow.__init__(self)
        self.ui = Ui_StateView()
        self.ui.setupUi(self)

        self.viewer = Viewer("pydot")

        self.ui.btShowSingleState.clicked.connect(self.showSingleState)
        self.ui.btShowWholeGraph.clicked.connect(self.showWholeGraph)

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

class SettingsView(QMainWindow):
    def __init__(self, window):
        QMainWindow.__init__(self)
        self.ui = Ui_Settings()
        self.ui.setupUi(self)

        self.ui.buttonBox.accepted.connect(self.accept)
        self.ui.buttonBox.rejected.connect(self.reject)
        # Appearance pane.
        self.ui.app_foreground.clicked.connect(self.pick_color)
        self.ui.app_background.clicked.connect(self.pick_color)
        # Profiling pane.
        self.ui.heatmap_low.clicked.connect(self.pick_color)
        self.ui.heatmap_high.clicked.connect(self.pick_color)
        # PyHyp pane.
        self.ui.btpyhyp.clicked.connect(self.choose_file_or_dir)
        self.ui.btpypyprefix.clicked.connect(self.choose_file_or_dir)
        # Unipycation pane.
        self.ui.btunipycation.clicked.connect(self.choose_file_or_dir)
        # L-Space pane.
        self.ui.btlspaceroot.clicked.connect(self.choose_file_or_dir)
        # JRuby pane.
        self.ui.btjruby.clicked.connect(self.choose_file_or_dir)
        self.ui.btjruby_load.clicked.connect(self.choose_file_or_dir)
        self.ui.btruby_parser.clicked.connect(self.set_ruby_parser)
        # GraalVM pane.
        self.ui.btgraalvm.clicked.connect(self.choose_file_or_dir)
        # Truffle pane.
        self.ui.btsljar.clicked.connect(self.choose_file_or_dir)
        self.ui.btjsjar.clicked.connect(self.choose_file_or_dir)
        self.ui.bttrufflejar.clicked.connect(self.choose_file_or_dir)
        # Tab switcher.
        self.ui.listWidget.currentRowChanged.connect(self.switch_view)
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
        dir_ = os.path.dirname(str(settings.value(setting, "", type=str)))
        if not dir_:
            dir_ = os.path.expanduser("~")
        if is_file:
            path, _ = QFileDialog.getOpenFileName(self, "Choose file", directory=dir_)
        else:
            path, _ = QFileDialog.getExistingDirectory(self, "Choose directory",
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
        self.ui.gen_showconsole.setCheckState(settings.value("gen_showconsole", 0, type=int))
        self.ui.gen_showparsestatus.setCheckState(settings.value("gen_showparsestatus", 2, type=int))
        self.ui.gen_showhud.setCheckState(settings.value("gen_showhud", 0, type=int))
        self.ui.gen_showoutline.setCheckState(settings.value("gen_showoutline", 0, type=int))
        # Appearance pane.
        family = settings.value("font-family", type=str)
        size = settings.value("font-size", type=int)
        self.ui.app_fontfamily.setCurrentFont(QtGui.QFont(family, size))
        self.ui.app_fontsize.setValue(size)
        self.ui.app_theme.setCurrentIndex(settings.value("app_themeindex", 0, type=int))
        self.ui.app_custom.setChecked(settings.value("app_custom", False, type=bool))
        self.foreground = settings.value("app_foreground", "#000000", type=str)
        self.background = settings.value("app_background", "#ffffff", type=str)
        self.change_color(self.ui.app_foreground, self.foreground)
        self.change_color(self.ui.app_background, self.background)
        # Profiling pane.
        tool_info_family = settings.value("tool-font-family", type=str)
        tool_info_size = settings.value("tool-font-size", type=int)
        self.ui.tool_info_fontfamily.setCurrentFont(QtGui.QFont(tool_info_family, tool_info_size))
        self.ui.tool_info_fontsize.setValue(tool_info_size)
        self.heatmap_low = settings.value("heatmap_low", "#deebf7", type=str)
        self.heatmap_high = settings.value("heatmap_high", "#3182bd", type=str)
        self.ui.heatmap_alpha.setValue(settings.value("heatmap_alpha", 100, type=int))
        self.ui.graalvm_pic_size.setValue(settings.value("graalvm_pic_size", 2, type=int))
        self.change_color(self.ui.heatmap_low, self.heatmap_low)
        self.change_color(self.ui.heatmap_high, self.heatmap_high)
        # PyHyp pane.
        self.ui.env_pyhyp.setText(settings.value("env_pyhyp", "", type=str))
        # Unipycation pane.
        self.ui.env_unipycation.setText(settings.value("env_unipycation", "", type=str))
        self.ui.env_pypyprefix.setText(settings.value("env_pypyprefix", "", type=str))
        # L-Space pane.
        self.ui.env_lspaceroot.setText(settings.value("env_lspaceroot", "", type=str))
        # JRuby pane.
        self.ui.env_jruby.setText(settings.value("env_jruby", "", type=str))
        self.ui.env_jruby_load.setText(settings.value("env_jruby_load", "", type=str))
        self.ui.env_ruby_parser.setText(settings.value("env_ruby_parser", "", type=str))
        # GraalVM pane.
        self.ui.env_graalvm.setText(settings.value("env_graalvm", "", type=str))
        # Truffle pane.
        self.ui.env_sl_jar.setText(settings.value("env_sl_jar", "", type=str))
        self.ui.env_js_jar.setText(settings.value("env_js_jar", "", type=str))
        self.ui.env_truffle_jar.setText(settings.value("env_truffle_jar", "", type=str))

    def saveSettings(self):
        settings = QSettings("softdev", "Eco")
        # General pane.
        settings.setValue("gen_showconsole", self.ui.gen_showconsole.checkState())
        settings.setValue("gen_showparsestatus", self.ui.gen_showparsestatus.checkState())
        settings.setValue("gen_showhud", self.ui.gen_showhud.checkState())
        settings.setValue("gen_showoutline", self.ui.gen_showoutline.checkState())
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
        gfont.setfont(QFont(settings.value("font-family", type=str), settings.value("font-size", type=int)))
        tool_info_font = QApplication.instance().tool_info_font
        tool_info_font.setfont(QFont(settings.value("tool-font-family", type=str), settings.value("tool-font-size", type=int)))

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

class InputLogView(QDialog):
    def __init__(self, parent):
        self.parent = parent
        QDialog.__init__(self, parent)
        self.ui = Ui_InputLog()
        self.ui.setupUi(self)

        self.ui.pushButton.pressed.connect(self.apply_log)

    def apply_log(self):
        log = self.ui.textEdit_2.toPlainText()
        self.tm.apply_inputlog(str(log))
        self.accept()

class AboutView(QDialog):
    def __init__(self, parent):
        self.parent = parent
        QDialog.__init__(self, parent)
        self.ui = Ui_About()
        self.ui.setupUi(self)

class PreviewDialog(QDialog):
    def __init__(self, parent):
        self.parent = parent
        QDialog.__init__(self, parent)
        self.ui = Ui_Preview()
        self.ui.setupUi(self)

        self.ui.comboBox.currentIndexChanged.connect(self.change)

    def change(self, index):
        if index == "Text":
            text = self.tm.export_as_text("/dev/null")
            self.ui.textEdit.setText(text)
        elif index == "Default":
            text = self.tm.export("/dev/null")
            if not text:
                text = ""
            self.ui.textEdit.setText(text)

class FindDialog(QDialog):
    def __init__(self, parent):
        self.parent = parent
        QDialog.__init__(self)
        self.ui = Ui_FindDialog()
        self.ui.setupUi(self)
        self.ui.buttonBox.button(QDialogButtonBox.Ok).setText("Find")
        self.ui.buttonBox.button(QDialogButtonBox.Ok).setIcon(QIcon.fromTheme("find"))

    def getText(self):
        return self.ui.leText.text()

    def focus(self):
        self.ui.leText.setFocus(True)
        self.ui.leText.selectAll()

class BreakpointDialog(QDialog):
    def __init__(self, parent):
        QMainWindow.__init__(self)
        self.parent = parent
        QDialog.__init__(self)
        self.ui = Ui_Breakpoint()
        self.ui.setupUi(self)
        self.line_number = 0
        self.ui.buttonBox.accepted.connect(self.accept)
        self.ui.buttonBox.rejected.connect(self.reject)

    def accept(self):
        make_temp =  self.ui.bp_type.currentText() == 'Temporary'
        self.parent.debug_breakpoint(make_temp, self.line_number, False,
        self.ui.bp_condition.displayText(), str(self.ui.bp_ignore.value()), True)
        self.hide()

    def reject(self):
        self.hide()

class LanguageView(QDialog):
    def __init__(self, parent, languages):
        self.parent = parent
        QDialog.__init__(self)
        self.ui = Ui_LanguageDialog()
        self.ui.setupUi(self)

        if len(newfile_langs) == 0:
            return

        # categorize languages
        d = {}
        self.d = d
        for l in newfile_langs:
            if l.base in d:
                d[l.base].append(l)
            else:
                d[l.base] = [l]

        for k in sorted(d.keys()):
            self.addLangItem(self.ui.listWidget, k)
        self.ui.listWidget.item(0).setSelected(True)

        for l in d[str(self.ui.listWidget.item(0).text())]:
            self.addLangItem(self.ui.listWidget_2, l)
        self.ui.listWidget_2.item(0).setSelected(True)

        self.ui.listWidget.currentRowChanged.connect(self.row_changed)

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
class Window(QMainWindow):

    def __init__(self):
        QMainWindow.__init__(self)
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)

        # XXX show current file in views
        self.parseview = ParseView(self)
        self.stateview = StateView(self)
        self.settingsview = SettingsView(self)
        self.previewdialog = PreviewDialog(self)
        self.breakpointdialog = BreakpointDialog(self)

        self.ui.actionImport.triggered.connect(self.importfile)
        self.ui.actionOpen.triggered.connect(self.openfile)
        self.ui.actionSave.triggered.connect(self.savefile)
        self.ui.actionSave_as.triggered.connect(self.savefileAs)
        self.ui.actionExport.triggered.connect(self.export)
        self.ui.actionExportAs.triggered.connect(self.exportAs)
        self.ui.actionRun.triggered.connect(self.run_subprocess)
        self.ui.actionDebug.triggered.connect(self.debug_subprocess)
        self.ui.actionProfile.triggered.connect(self.profile_subprocess)

        try:
            import pydot
            self.ui.actionParse_Tree.triggered.connect(self.showParseView)
            self.ui.actionStateGraph.triggered.connect(self.showStateView)
            self.ui.actionPvShow.triggered.connect(self.showPygameTree)
        except ImportError:
            sys.stderr.write("Warning: pydot not installed. Viewing of parse trees/graphs disabled.\n")
            self.ui.actionParse_Tree.setEnabled(False)
            self.ui.actionPvShow.setEnabled(False)
            self.ui.actionStateGraph.setEnabled(False)

        self.ui.actionSettings.triggered.connect(self.showSettingsView)
        self.ui.actionAbout.triggered.connect(self.showAboutView)
        self.ui.actionPreview.triggered.connect(self.showPreviewDialog)
        self.ui.actionUndo.triggered.connect(self.undo)
        self.ui.actionRedo.triggered.connect(self.redo)
        self.ui.actionSelect_all.triggered.connect(self.select_all)
        self.ui.actionCopy.triggered.connect(self.copy)
        self.ui.actionCut.triggered.connect(self.cut)
        self.ui.actionPaste.triggered.connect(self.paste)
        self.ui.actionFind.triggered.connect(self.find)
        self.ui.actionFind_next.triggered.connect(self.find_next)
        self.ui.actionAdd_language_box.triggered.connect(self.show_lbox_menu)
        self.ui.actionSelect_next_language_box.triggered.connect(self.select_next_lbox)
        self.ui.actionNew.triggered.connect(self.newfile)
        self.ui.actionExit.triggered.connect(self.quit)
        self.ui.tabWidget.tabCloseRequested.connect(self.closeTab)
        self.ui.tabWidget.currentChanged.connect(self.tabChanged)
        self.ui.actionCode_complete.triggered.connect(self.show_code_completion)
        #self.ui.actionFull_reparse.triggered.connect(self.full_reparse)
        self.ui.treeWidget.itemDoubleClicked.connect(self.click_parsers)
        self.ui.actionShow_language_boxes.triggered.connect(self.update_editor)
        self.ui.actionShow_namebinding.triggered.connect(self.update_editor)
        self.ui.actionShow_indentation.triggered.connect(self.toogle_indentation)
        self.ui.actionAutolboxFind.triggered.connect(self.toggle_find_autolboxes)
        self.ui.actionAutolboxInsert.triggered.connect(self.toggle_insert_autolboxes)
        self.ui.actionShow_lspaceview.triggered.connect(self.view_in_lspace)
        self.ui.menuChange_language_box.aboutToShow.connect(self.showEditMenu)
        self.ui.actionRemove_language_box.triggered.connect(self.remove_languagebox)
        self.ui.actionLock_Unlock_language_box.triggered.connect(self.toggle_lock_languagebox)
        self.ui.menuRecent_files.aboutToShow.connect(self.showRecentFiles)
        self.ui.actionInput_log.triggered.connect(self.show_input_log)

        # Debug buttons
        self.ui.actionContinue.triggered.connect(self.debug_continue)
        self.ui.actionStop.triggered.connect(self.debug_stop)
        self.ui.actionStepInto.triggered.connect(self.debug_step_into)
        self.ui.actionStepOver.triggered.connect(self.debug_step_over)

        # Make sure the Project -> Profile and Project -> Run with Debugger menu items
        # only appear for languages that support it.
        self.ui.tabWidget.currentChanged.connect(self.set_profiler_enabled)
        self.ui.tabWidget.currentChanged.connect(self.set_debugger_enabled)

        self.ui.menuWindow.addAction(self.ui.dockWidget.toggleViewAction())
        self.ui.menuWindow.addAction(self.ui.dockWidget_2.toggleViewAction())
        self.ui.menuWindow.addAction(self.ui.dockWidget_3.toggleViewAction())
        self.ui.menuWindow.addAction(self.ui.dockWidget_4.toggleViewAction())

        self.ui.teConsole.setFont(QApplication.instance().gfont.font)
        self.ui.teConsole.customContextMenuRequested.connect(self.consoleContextMenu)
        self.ui.teConsole.setContextMenuPolicy(Qt.CustomContextMenu)

        # Set up HUD radio buttons.
        self.ui.hud_off_button.setChecked(True)
        self.ui.hud_off_button.clicked.connect(self.hud_off_toggle)
        self.ui.hud_callgraph_button.clicked.connect(self.hud_callgraph_toggle)
        self.ui.hud_eval_button.clicked.connect(self.hud_eval_toggle)
        self.ui.hud_types_button.clicked.connect(self.hud_types_toggle)
        self.ui.hud_heat_map_button.clicked.connect(self.hud_heat_map_toggle)
        self.ui.hud_callgraph_button.setDisabled(True)
        self.ui.hud_eval_button.setDisabled(True)
        self.ui.hud_types_button.setDisabled(True)
        self.ui.hud_heat_map_button.setDisabled(True)

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
        if not settings.value("gen_showconsole", False, type=bool):
            self.ui.dockWidget.hide()
        if not settings.value("gen_showparsestatus", True, type=bool):
            self.ui.dockWidget_2.hide()
        if not settings.value("gen_showhud", False, type=bool):
            self.ui.dockWidget_3.hide()
        if not settings.value("gen_showoutline", False, type=bool):
            self.ui.dockWidget_4.hide()

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

    def profiler_finished(self):
        self.profile_throbber.hide()
        ed_tab = self.getEditor()
        if ed_tab is not None:
            ed_tab.update()

    def debug_finished(self):
        self.ui.expressionBox.hide()
        self.debug_toggle_buttons(False)
        self.debugging = False
        self.debug_t.exit()
        self.getEditorTab().is_debugging(False)

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
        menu.addMenu(newmenu)

        lbox = self.getEditor().tm.get_selected_languagebox()
        if lbox is not None:
            menu.addAction(self.ui.actionRemove_language_box)
            lockaction = QAction(QIcon.fromTheme("lock"), "Lock language box", menu)
            lockaction.triggered.connect(self.toggle_lock_languagebox)
            menu.addAction(lockaction)
            if not lbox.tbd:
                lockaction.setText("Unlock language box")

            menu.addMenu(changemenu)

        menu.addAction(self.ui.actionSelect_next_language_box)
        menu.addSeparator()
        menu.addAction(self.ui.actionCode_complete)

        action = menu.exec_(self.getEditor().mapToGlobal(pos))
        if not action:
            return

        self.getEditor().sublanguage = action.data()
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
        os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = "hide"
        try:
            import pygame
        except ImportError:
            sys.stderr.write("Warning: pygame not installed. Interactive viewing of parse trees disabled.\n")
            self.ui.actionPvShow.setEnabled(False)
            return

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
                a.triggered.connect(self.actionChangeLBoxMenu)

    def showRecentFiles(self):
        settings = QSettings("softdev", "Eco")
        rf = settings.value("recent_files", [], type=list)
        self.ui.menuRecent_files.clear()
        for f in rf:
            n = os.path.basename(f)
            fullname = f
            action = QAction(n, self.ui.menuRecent_files)
            action.triggered.connect(makelambda(self.openfile, fullname))
            self.ui.menuRecent_files.addAction(action)

    def actionChangeLBoxMenu(self):
        action = self.sender()
        if action:
            self.getEditor().sublanguage = action.data()
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
        parser.add_option("-c", "--composition", action="store_true", default=None, help="Load external composition. Usage: --composition [COMPOSITIONFILE]")
        (options, args) = parser.parse_args()

        if options.log.upper() in ["INFO", "WARNING", "ERROR", "DEBUG"]:
            loglevel=getattr(logging, options.log.upper())
        else:
            loglevel=logging.WARNING
        logging.basicConfig(format='%(levelname)s: %(message)s', filemode='w', level=loglevel)

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
        if options.composition:
            self.load_composition(args[0])
            return
        if len(args) > 0:
            for f in args:
                self.openfile(str(f))


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
            self.tm.export(dest, source=source)
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

    def toggle_find_autolboxes(self):
        if self.ui.actionAutolboxFind.isChecked():
            self.getEditor().tm.option_autolbox_find = True
        else:
            self.getEditor().tm.option_autolbox_find = False
            self.getEditor().tm.option_autolbox_insert = False
            self.ui.actionAutolboxInsert.setChecked(False)

    def toggle_insert_autolboxes(self):
        if self.ui.actionAutolboxInsert.isChecked():
            self.getEditor().tm.option_autolbox_insert = True
            self.getEditor().tm.option_autolbox_find = True
            self.ui.actionAutolboxFind.setChecked(True)
        else:
            self.getEditor().tm.option_autolbox_insert = False

    def view_in_lspace(self):
        settings = QSettings("softdev", "Eco")
        lspace_root = str(settings.value("env_lspaceroot", type=str))
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
        self.debugger.signal_start.emit()
        self.debugging = True
        self.getEditorTab().is_debugging(True)

    def profile_subprocess(self):
        self.ui.teConsole.clear()
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

    def remove_languagebox(self):
        self.getEditor().tm.remove_selected_lbox()
        self.btReparse([])
        self.getEditor().update()

    def toggle_lock_languagebox(self):
        self.getEditor().tm.toggle_lock_languagebox()

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
            self.getEditorTab().keypress(center=True)

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

    def load_composition(self, filename):
        import json
        from grammars.grammars import create_grammar_from_config
        with open(filename) as f:
            cfg = json.load(f)
            create_grammar_from_config(cfg, filename)

    def savefile(self):
        ed = self.getEditorTab()
        if not ed:
            return
        if self.getEditorTab().filename:
            self.getEditor().saveToJson(self.getEditorTab().filename)
            self.delete_swap()
        else:
            self.savefileAs()

    def savefileAs(self):
        ed = self.getEditorTab()
        if not ed:
            return
        self.delete_swap()
        filename, _ = QFileDialog.getSaveFileName(self, "Save File", self.get_last_dir(), "Eco files (*.eco *.nb);; All files (*.*)")
        if filename:
            self.save_last_dir(str(filename))
            self.add_to_recent_files(str(filename))
            self.getEditor().saveToJson(filename)
            self.getEditorTab().filename = filename

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
            ed.export_path, _ = QFileDialog.getSaveFileName()
        if ed.export_path:
            result = self.getEditor().tm.export(ed.export_path, source=ed.filename)
            if result is False:
                self.show_export_fail_message()

    def exportAs(self):
        ed = self.getEditorTab()
        if not ed:
            return
        path, _ = QFileDialog.getSaveFileName(self, "Export file", self.get_last_dir())
        if path:
            self.save_last_dir(str(path))
            ed.export_path = path
            result = self.getEditor().tm.export(path, source=ed.filename)
            if result is False:
                self.show_export_fail_message()

    def show_export_fail_message(self):
        QMessageBox.warning(self, "Warning", "Export failed: program syntactically invalid!")

    def show_execution_fail_message(self, reason):
        self.show_output("Execution error: {}.".format(reason))

    def get_last_dir(self):
        settings = QSettings("softdev", "Eco")
        last_dir = settings.value("last_dir", type=str)
        if last_dir:
            return last_dir
        return QDir.currentPath()

    def save_last_dir(self, filename):
        settings = QSettings("softdev", "Eco")
        settings.setValue("last_dir", filename)

    def add_to_recent_files(self, filename):
        settings = QSettings("softdev", "Eco")
        prev = settings.value("recent_files", [], type=str)
        if filename in prev:
            prev.remove(filename)
        prev.insert(0, filename)
        if len(prev) > 10:
            prev.pop()
        settings.setValue("recent_files", prev)

    def openfile(self, filename=None):
        if not filename:
            filename, _ = QFileDialog.getOpenFileName(self, "Open File", self.get_last_dir(), "Eco files (*.eco *.nb *.eco.bak);; All files (*.*)")
        if filename:
            self.save_last_dir(str(filename))
            self.add_to_recent_files(str(filename))
            if filename.endswith(".eco") or filename.endswith(".nb") or filename.endswith(".eco.bak") or filename.endswith(".eco.swp"):
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

    def enable_hud_buttons(self, language):
        """Enable the correct HUD buttons for the current language.
        Never disables the hud_off button.
        """
        if language == "Python 2.7.5":
            self.ui.hud_callgraph_button.setDisabled(True)
            self.ui.hud_eval_button.setDisabled(True)
            self.ui.hud_types_button.setDisabled(True)
            self.ui.hud_heat_map_button.setDisabled(False)
        elif language.startswith("Ruby"):  # Includes JRuby + SL, etc.
            self.ui.hud_callgraph_button.setDisabled(False)
            self.ui.hud_eval_button.setDisabled(False)
            self.ui.hud_types_button.setDisabled(False)
            self.ui.hud_heat_map_button.setDisabled(True)
        else:
            self.ui.hud_callgraph_button.setDisabled(True)
            self.ui.hud_eval_button.setDisabled(True)
            self.ui.hud_types_button.setDisabled(True)
            self.ui.hud_heat_map_button.setDisabled(True)

    def tabChanged(self, index):
        ed_tab = self.getEditorTab()
        if ed_tab is not None:
            if hasattr(ed_tab.editor.tm.get_mainparser(), "graph") and \
                    ed_tab.editor.tm.get_mainparser().graph:
                self.ui.actionStateGraph.setEnabled(True)
            else:
                self.ui.actionStateGraph.setEnabled(False)
            language = ed_tab.editor.get_mainlanguage()
            self.enable_hud_buttons(language)
            if ed_tab.editor.hud_callgraph:
                self.ui.hud_callgraph_button.setChecked(True)
            elif ed_tab.editor.hud_eval:
                self.ui.hud_eval_button.setChecked(True)
            elif ed_tab.editor.hud_types:
                self.ui.hud_types_button.setChecked(True)
            elif ed_tab.editor.hud_heat_map:
                self.ui.hud_heat_map_button.setChecked(True)
            else:
                self.ui.hud_off_button.setChecked(True)
            tm = ed_tab.editor.tm
            tm.option_autolbox_find = self.ui.actionAutolboxFind.isChecked()
            tm.option_autolbox_insert = self.ui.actionAutolboxInsert.isChecked()
            if self.pgviewer:
                self.pgviewer.update(tm.main_lbox, tm.version, tm.get_max_version())
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
        for i in reversed(list(range(self.ui.tabWidget.count()))):
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
                except AttributeError as e:
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

    def updateASTOutline(self):
        self.ui.tw_astoutline.clear()
        aa = self.getEditor().tm.parsers[0][3]
        if "class" in aa.data:
            for uri in aa.data["class"]:
                if not uri.path or (uri.path and uri.path[0].name is None and len(uri.path) == 1):
                    self.addToASTOutline(aa, uri, self.ui.tw_astoutline)
        self.ui.tw_astoutline.expandAll()

    def addToASTOutline(self, aa, uri, parent):
        qtreeitem = QTreeWidgetItem(parent)
        qtreeitem.setText(0, uri.name)
        qtreeitem.setIcon(0, QIcon("gui/"+uri.kind+".png"))
        names = aa.get_names_within_path(uri.as_path())
        for n in names:
            self.addToASTOutline(aa, n, qtreeitem)

    def add_parsingstatus(self, nested, root, parent):
        if root not in nested:
            return
        for parser, lexer, lang in nested[root]:
            status = parser.last_status
            qtreeitem = QTreeWidgetItem(parent)
            qtreeitem.setText(0, lang)
            if status:
                qtreeitem.setIcon(0, QIcon("gui/accept.png"))
            else:
                qtreeitem.setIcon(0, QIcon("gui/exclamation.png"))
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
        self.ui.actionRemove_language_box.setEnabled(enabled)
        self.ui.actionLock_Unlock_language_box.setEnabled(enabled)
        self.ui.actionSelect_next_language_box.setEnabled(enabled)
        self.ui.actionAutolboxInsert.setEnabled(enabled)
        self.ui.actionAutolboxFind.setEnabled(enabled)
        try:
            import pydot
            self.ui.actionParse_Tree.setEnabled(enabled)
        except ImportError:
            pass
        self.ui.actionPvShow.setEnabled(enabled)
        self.ui.actionCode_complete.setEnabled(enabled)
        self.ui.menuChange_language_box.setEnabled(enabled)
        self.ui.actionPreview.setEnabled(enabled)
        self.ui.actionInput_log.setEnabled(enabled)

        if enabled == False:
            self.ui.actionProfile.setEnabled(enabled)
            self.ui.actionDebug.setEnabled(enabled)
            self.ui.actionStateGraph.setEnabled(enabled)

    def debug_continue(self):
        self.debugger.signal_command.emit("c")

    def debug_stop(self):
        self.debugger.signal_command.emit("q")

    def debug_step_into(self):
        self.debugger.signal_command.emit("s")

    def debug_step_over(self):
        self.debugger.signal_command.emit("n")

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
        etab.breakpoint.connect(self.debug_breakpoint)
        etab.breakcondition.connect(self.debug_breakpoint_condition)

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
    app = QApplication(sys.argv)
    app.setStyle('gtk')

    settings = QSettings("softdev", "Eco")
    if not settings.contains("font-family"):
        settings.setValue("font-family", "Monospace")
        settings.setValue("font-size", 9)
    if not settings.contains("tool-font-family"):
        settings.setValue("tool-font-family", "Monospace")
        settings.setValue("tool-font-size", 9)

    app.gfont = GlobalFont(settings.value("font-family", type=str), settings.value("font-size", type=int))
    app.tool_info_font = GlobalFont(settings.value("tool-font-family", type=str), settings.value("tool-font-size", type=int))

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
    window.debugger.signal_command.connect(window.debugger.run_command)
    window.debugger.signal_start.connect(window.debugger.start_pdb)
    window.debugger.signal_output.connect(window.show_output)
    window.debugger.signal_done.connect(window.debug_finished)
    window.debugger.signal_toggle_buttons.connect(window.debug_toggle_buttons)
    window.debugger.signal_execute_fail.connect(window.show_execution_fail_message)

    t.signal_execute_fail.connect(window.show_execution_fail_message)
    t.signal.connect(window.show_output)
    window.thread_prof.signal.connect(window.show_output)
    # Connect the profiler (tool) thread to the throbber.
    window.thread_prof.signal_done.connect(window.profiler_finished)

    window.parse_options()
    window.show()
    t.wait()
    sys.exit(app.exec_())

class SubProcessThread(QThread):
    signal = pyqtSignal(str)
    signal_execute_fail = pyqtSignal(str)

    def __init__(self, window, parent):
        QThread.__init__(self, parent=parent)
        self.window = window

    def run(self):
        from treemanager import ExecutionError
        ed = self.window.getEditorTab()
        try:
            p = self.window.getEditor().export(run=True, source=str(ed.filename))
            lang = self.window.getEditor().get_mainlanguage()
            if p is False:
                self.signal_execute_fail.emit("program syntactically invalid")
            else:
                for line in iter(p.stdout.readline, b''):
                    if lang == "PHP + Python" and line.startswith(b"  <?php{ "):
                        line = b"  " + line[9:]
                    self.signal.emit(line.rstrip().decode("utf-8"))
        except ExecutionError as e:
            self.signal_execute_fail.emit(e.message)

class ProfileThread(QThread):
    signal_done = pyqtSignal()
    signal = pyqtSignal()
    signal_overlay = pyqtSignal(dict)
    signal_execute_fail = pyqtSignal()

    def __init__(self, window, parent):
        QThread.__init__(self, parent=parent)
        self.window = window

    def run(self):
        ed = self.window.getEditorTab()
        p = self.window.getEditor().tm.export(path=str(ed.filename), profile=True)
        # Using read() here, rather than readline() because profiler output
        # often includes blank lines in the middle of the output.
        if p:
            text = p.stdout.read()
            self.signal.emit(text.strip())
            self.signal_overlay.emit(self.window.getEditor().tm.profile_data)
        else:
            self.signal_overlay.emit(None)
            self.signal_execute_fail.emit()
        self.signal_done.emit(None)


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
