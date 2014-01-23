# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'parsetree.ui'
#
# Created: Wed Jan 15 17:00:13 2014
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
        self.horizontalLayout = QtGui.QHBoxLayout()
        self.horizontalLayout.setContentsMargins(-1, 0, -1, -1)
        self.horizontalLayout.setObjectName(_fromUtf8("horizontalLayout"))
        self.verticalLayout_3 = QtGui.QVBoxLayout()
        self.verticalLayout_3.setContentsMargins(-1, 0, -1, -1)
        self.verticalLayout_3.setObjectName(_fromUtf8("verticalLayout_3"))
        self.cb_toggle_ast = QtGui.QCheckBox(self.centralwidget)
        self.cb_toggle_ast.setCheckable(True)
        self.cb_toggle_ast.setChecked(False)
        self.cb_toggle_ast.setObjectName(_fromUtf8("cb_toggle_ast"))
        self.verticalLayout_3.addWidget(self.cb_toggle_ast)
        self.cb_toggle_ws = QtGui.QCheckBox(self.centralwidget)
        self.cb_toggle_ws.setEnabled(True)
        self.cb_toggle_ws.setChecked(False)
        self.cb_toggle_ws.setObjectName(_fromUtf8("cb_toggle_ws"))
        self.verticalLayout_3.addWidget(self.cb_toggle_ws)
        self.cb_fit_ast = QtGui.QCheckBox(self.centralwidget)
        self.cb_fit_ast.setObjectName(_fromUtf8("cb_fit_ast"))
        self.verticalLayout_3.addWidget(self.cb_fit_ast)
        self.horizontalLayout.addLayout(self.verticalLayout_3)
        self.verticalLayout_2 = QtGui.QVBoxLayout()
        self.verticalLayout_2.setContentsMargins(-1, 0, -1, -1)
        self.verticalLayout_2.setObjectName(_fromUtf8("verticalLayout_2"))
        self.rb_view_parsetree = QtGui.QRadioButton(self.centralwidget)
        self.rb_view_parsetree.setChecked(True)
        self.rb_view_parsetree.setObjectName(_fromUtf8("rb_view_parsetree"))
        self.verticalLayout_2.addWidget(self.rb_view_parsetree)
        self.rb_view_ast = QtGui.QRadioButton(self.centralwidget)
        self.rb_view_ast.setObjectName(_fromUtf8("rb_view_ast"))
        self.verticalLayout_2.addWidget(self.rb_view_ast)
        self.rb_view_linetree = QtGui.QRadioButton(self.centralwidget)
        self.rb_view_linetree.setObjectName(_fromUtf8("rb_view_linetree"))
        self.verticalLayout_2.addWidget(self.rb_view_linetree)
        self.horizontalLayout.addLayout(self.verticalLayout_2)
        self.verticalLayout.addLayout(self.horizontalLayout)
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
        MainWindow.setWindowTitle(_translate("MainWindow", "Tree viewer", None))
        self.cb_toggle_ast.setText(_translate("MainWindow", "Show tree", None))
        self.cb_toggle_ws.setText(_translate("MainWindow", "Show whitespace nodes", None))
        self.cb_fit_ast.setText(_translate("MainWindow", "Fit in view", None))
        self.rb_view_parsetree.setText(_translate("MainWindow", "Parse tree", None))
        self.rb_view_ast.setText(_translate("MainWindow", "AST", None))
        self.rb_view_linetree.setText(_translate("MainWindow", "Line based tree", None))
        self.bt_show_sel_ast.setText(_translate("MainWindow", "Show selected text parse tree", None))

