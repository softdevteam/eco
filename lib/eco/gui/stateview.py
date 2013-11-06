# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'stateview.ui'
#
# Created: Wed Nov  6 14:11:37 2013
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
        MainWindow.resize(471, 468)
        self.centralwidget = QtGui.QWidget(MainWindow)
        self.centralwidget.setObjectName(_fromUtf8("centralwidget"))
        self.verticalLayout = QtGui.QVBoxLayout(self.centralwidget)
        self.verticalLayout.setObjectName(_fromUtf8("verticalLayout"))
        self.gvStategraph = QtGui.QGraphicsView(self.centralwidget)
        sizePolicy = QtGui.QSizePolicy(QtGui.QSizePolicy.Minimum, QtGui.QSizePolicy.Expanding)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.gvStategraph.sizePolicy().hasHeightForWidth())
        self.gvStategraph.setSizePolicy(sizePolicy)
        self.gvStategraph.setObjectName(_fromUtf8("gvStategraph"))
        self.verticalLayout.addWidget(self.gvStategraph)
        self.horizontalLayout_2 = QtGui.QHBoxLayout()
        self.horizontalLayout_2.setObjectName(_fromUtf8("horizontalLayout_2"))
        self.btShowWholeGraph = QtGui.QPushButton(self.centralwidget)
        self.btShowWholeGraph.setObjectName(_fromUtf8("btShowWholeGraph"))
        self.horizontalLayout_2.addWidget(self.btShowWholeGraph)
        self.leSingleState = QtGui.QLineEdit(self.centralwidget)
        sizePolicy = QtGui.QSizePolicy(QtGui.QSizePolicy.Minimum, QtGui.QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.leSingleState.sizePolicy().hasHeightForWidth())
        self.leSingleState.setSizePolicy(sizePolicy)
        self.leSingleState.setObjectName(_fromUtf8("leSingleState"))
        self.horizontalLayout_2.addWidget(self.leSingleState)
        self.btShowSingleState = QtGui.QPushButton(self.centralwidget)
        self.btShowSingleState.setObjectName(_fromUtf8("btShowSingleState"))
        self.horizontalLayout_2.addWidget(self.btShowSingleState)
        self.verticalLayout.addLayout(self.horizontalLayout_2)
        MainWindow.setCentralWidget(self.centralwidget)
        self.menubar = QtGui.QMenuBar(MainWindow)
        self.menubar.setGeometry(QtCore.QRect(0, 0, 471, 21))
        self.menubar.setObjectName(_fromUtf8("menubar"))
        MainWindow.setMenuBar(self.menubar)
        self.statusbar = QtGui.QStatusBar(MainWindow)
        self.statusbar.setObjectName(_fromUtf8("statusbar"))
        MainWindow.setStatusBar(self.statusbar)

        self.retranslateUi(MainWindow)
        QtCore.QMetaObject.connectSlotsByName(MainWindow)

    def retranslateUi(self, MainWindow):
        MainWindow.setWindowTitle(_translate("MainWindow", "MainWindow", None))
        self.btShowWholeGraph.setText(_translate("MainWindow", "Show whole graph", None))
        self.btShowSingleState.setText(_translate("MainWindow", "Show single state", None))

