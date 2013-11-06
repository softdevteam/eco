# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'parsetree.ui'
#
# Created: Wed Nov  6 14:07:55 2013
#      by: PyQt4 UI code generator 4.10.3
#
# WARNING! All changes made in this file will be lost!

from PyQt4 import QtCore, QtGui

try:
    _fromUtf8 = QtCore.QString.fromUtf8
except AttributeError:
    def _fromUtf8(s):
        return s

try:
    _encoding = QtGui.QApplication.UnicodeUTF8
    def _translate(context, text, disambig):
        return QtGui.QApplication.translate(context, text, disambig, _encoding)
except AttributeError:
    def _translate(context, text, disambig):
        return QtGui.QApplication.translate(context, text, disambig)

class Ui_MainWindow(object):
    def setupUi(self, MainWindow):
        MainWindow.setObjectName(_fromUtf8("MainWindow"))
        MainWindow.resize(594, 568)
        self.centralwidget = QtGui.QWidget(MainWindow)
        self.centralwidget.setObjectName(_fromUtf8("centralwidget"))
        self.verticalLayout = QtGui.QVBoxLayout(self.centralwidget)
        self.verticalLayout.setObjectName(_fromUtf8("verticalLayout"))
        self.graphicsView = QtGui.QGraphicsView(self.centralwidget)
        sizePolicy = QtGui.QSizePolicy(QtGui.QSizePolicy.Minimum, QtGui.QSizePolicy.Expanding)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.graphicsView.sizePolicy().hasHeightForWidth())
        self.graphicsView.setSizePolicy(sizePolicy)
        palette = QtGui.QPalette()
        brush = QtGui.QBrush(QtGui.QColor(255, 255, 255))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Active, QtGui.QPalette.Base, brush)
        brush = QtGui.QBrush(QtGui.QColor(255, 255, 255))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Inactive, QtGui.QPalette.Base, brush)
        brush = QtGui.QBrush(QtGui.QColor(247, 247, 247))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Disabled, QtGui.QPalette.Base, brush)
        self.graphicsView.setPalette(palette)
        self.graphicsView.setAutoFillBackground(True)
        self.graphicsView.setDragMode(QtGui.QGraphicsView.ScrollHandDrag)
        self.graphicsView.setObjectName(_fromUtf8("graphicsView"))
        self.verticalLayout.addWidget(self.graphicsView)
        self.cb_toggle_ws = QtGui.QCheckBox(self.centralwidget)
        self.cb_toggle_ws.setEnabled(True)
        self.cb_toggle_ws.setChecked(False)
        self.cb_toggle_ws.setObjectName(_fromUtf8("cb_toggle_ws"))
        self.verticalLayout.addWidget(self.cb_toggle_ws)
        self.cb_toggle_ast = QtGui.QCheckBox(self.centralwidget)
        self.cb_toggle_ast.setCheckable(True)
        self.cb_toggle_ast.setChecked(False)
        self.cb_toggle_ast.setObjectName(_fromUtf8("cb_toggle_ast"))
        self.verticalLayout.addWidget(self.cb_toggle_ast)
        self.cb_fit_ast = QtGui.QCheckBox(self.centralwidget)
        self.cb_fit_ast.setObjectName(_fromUtf8("cb_fit_ast"))
        self.verticalLayout.addWidget(self.cb_fit_ast)
        self.bt_show_sel_ast = QtGui.QPushButton(self.centralwidget)
        self.bt_show_sel_ast.setObjectName(_fromUtf8("bt_show_sel_ast"))
        self.verticalLayout.addWidget(self.bt_show_sel_ast)
        MainWindow.setCentralWidget(self.centralwidget)
        self.menubar = QtGui.QMenuBar(MainWindow)
        self.menubar.setGeometry(QtCore.QRect(0, 0, 594, 21))
        self.menubar.setObjectName(_fromUtf8("menubar"))
        MainWindow.setMenuBar(self.menubar)
        self.statusbar = QtGui.QStatusBar(MainWindow)
        self.statusbar.setObjectName(_fromUtf8("statusbar"))
        MainWindow.setStatusBar(self.statusbar)

        self.retranslateUi(MainWindow)
        QtCore.QMetaObject.connectSlotsByName(MainWindow)

    def retranslateUi(self, MainWindow):
        MainWindow.setWindowTitle(_translate("MainWindow", "Parse Tree", None))
        self.cb_toggle_ws.setText(_translate("MainWindow", "Show whitespace nodes", None))
        self.cb_toggle_ast.setText(_translate("MainWindow", "Show parse tree", None))
        self.cb_fit_ast.setText(_translate("MainWindow", "Fit AST in view", None))
        self.bt_show_sel_ast.setText(_translate("MainWindow", "Show selected text parse tree", None))

