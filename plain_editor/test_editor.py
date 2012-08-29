#! /usr/bin/env python

import sys
from PyQt4 import QtGui
from PyQt4 import QtCore


class Tooltip(QtGui.QWidget):
    def __init__(self, parent=None):
        QtGui.QWidget.__init__(self, parent)

        self.setGeometry(300, 300, 250, 150)
        pal = self.palette()
        pal.setColor(self.backgroundRole(), QtGui.QColor(0, 0, 0))
        self.setPalette(pal)
        self.setWindowTitle('Tooltip')
        self.lines = [""]
        # Initialize ed_l (edit_line) and ed_c (edit_column)
        self.ed_l = self.ed_c = 0

        QtGui.QToolTip.setFont(QtGui.QFont('OldEnglish', 10))
        
        self.font = QtGui.QFont('Courier', 12)
        self.fontm = QtGui.QFontMetrics(self.font)
        self.fontht = self.fontm.height()

        self.show_cursor = 0
        self.ctimer = QtCore.QTimer() # cursor timer
        QtCore.QObject.connect(self.ctimer, QtCore.SIGNAL("timeout()"), self.blink)
        self.ctimer.start(500)

        self.centre()


    def closeEvent(self, event):
        reply = QtGui.QMessageBox.question(self, 'Message',
            "Are you sure you want to quit?", "Quit", "Stay")

        print reply
        if reply == 0:
            event.accept()
        else:
            event.ignore()


    def blink(self):
        if self.show_cursor:
            self.show_cursor = 0
        else:
            self.show_cursor = 1
        
        self.update()
        

    def centre(self):
        screen = QtGui.QDesktopWidget().screenGeometry()
        size =  self.geometry()
        self.move((screen.width()-size.width())/2, (screen.height()-size.height())/2)


    def paintEvent(self, event):
        paint = QtGui.QPainter()
        paint.begin(self)
        paint.setPen(QtGui.QColor(255, 255, 255))
        paint.setFont(self.font)
        to = QtGui.QTextOption(QtCore.Qt.AlignLeft)
        to.flag = QtGui.QTextOption.ShowTabsAndSpaces | QtGui.QTextOption.ShowLineAndParagraphSeparators
        y = 1
        for l in self.lines:
            paint.drawText(QtCore.QPointF(0, y * self.fontht), l)
            y += 1

        l = self.lines[self.ed_l]
        if self.show_cursor:
            cc = QtGui.QColor(255, 0, 0, 255)
            paint.fillRect(self.fontm.width(l[:self.ed_c]) - 1, self.ed_l * self.fontht + 2, 2, self.fontht, QtGui.QBrush(cc, QtCore.Qt.SolidPattern))

        paint.end()


    def keyPressEvent(self, e):
        l = self.lines[self.ed_l] # line
        if e.key() == QtCore.Qt.Key_Backspace:
            if self.ed_c == 0:
                if self.ed_l == 0:
                    return
                else:
                    self.ed_c = len(self.lines[self.ed_l - 1])
                    self.lines[self.ed_l - 1] += l
                    del self.lines[self.ed_l]
                    self.ed_l -= 1
            elif len(l) == 0:
                del self.lines[self.ed_l]
                self.ed_l -= 1
                self.ed_c = len(self.lines[self.ed_l])
            else:
                self.lines[self.ed_l] = l[:self.ed_c - 1] + l[self.ed_c:]
                self.ed_c -= 1
        elif e.key() == QtCore.Qt.Key_Delete:
            if self.ed_l + 1 == len(self.lines) and self.ed_c == len(l):
                return
            elif self.ed_c == len(l):
                self.lines[self.ed_l] += self.lines[self.ed_l + 1]
                del self.lines[self.ed_l + 1]
            else:
                self.lines[self.ed_l] = l[:self.ed_c] + l[self.ed_c + 1:]
        elif e.key() == QtCore.Qt.Key_Left:
            if self.ed_l == 0 and self.ed_c == 0:
                return
            elif self.ed_c == 0:
                self.ed_l -= 1
                self.ed_c = len(self.lines[self.ed_l])
            else:
                self.ed_c -= 1
        elif e.key() == QtCore.Qt.Key_Right:
            if self.ed_l == len(self.lines) - 1 and self.ed_c == len(l):
                return
            elif self.ed_c == len(l):
                self.ed_l += 1
                self.ed_c = 0
            else:
                self.ed_c += 1
        elif e.key() == QtCore.Qt.Key_Up:
            if self.ed_l == 0:
                self.ed_c = 0
            else:
                self.ed_l -= 1
                if self.ed_c > len(self.lines[self.ed_l]):
                    self.ed_c = len(self.lines[self.ed_l])
        elif e.key() == QtCore.Qt.Key_Down:
            if self.ed_l == len(self.lines) - 1:
                self.ed_c = len(l)
            else:
                self.ed_l += 1
                if self.ed_c > len(self.lines[self.ed_l]):
                    self.ed_c = len(self.lines[self.ed_l])
        elif e.key() == QtCore.Qt.Key_Return:
            if self.ed_c == len(l):
                self.lines.insert(self.ed_l + 1, "")
            else:
                self.lines[self.ed_l] = l[:self.ed_c]
                self.lines.insert(self.ed_l + 1, l[self.ed_c:])
            self.ed_l += 1
            self.ed_c = 0
        elif e.key() == QtCore.Qt.Key_Home:
            self.ed_c = 0
        elif e.key() == QtCore.Qt.Key_End:
            self.ed_c = len(l)
        elif e.text() == "":
            # e.g. Shift on its own held down
            return
        else:
            self.lines[self.ed_l] = l[:self.ed_c] + unicode(e.text()) + l[self.ed_c:]
            self.ed_c += 1
        self.update()


    def mousePressEvent(self, e):
        g = self.geometry()
        rx = e.globalX() - g.x()
        ry = e.globalY() - g.y()

        lh = int(ry / self.fontht)
        if lh >= len(self.lines):
            self.ed_l = len(self.lines) - 1
        else:
            self.ed_l = lh
        
        l = self.lines[self.ed_l]
        e = len(l)
        while e >= 0:
            if e == len(l):
                if self.fontm.width(l[:e]) < rx:
                    break
            elif self.fontm.width(l[:e]) - 0.5 * self.fontm.width(l[e]) < rx:
                break
            e -= 1
        if e < 0:
            self.ed_c = 0
        else:
            self.ed_c = e

        self.show_cursor = 1
        self.update()



app = QtGui.QApplication(sys.argv)
tooltip = Tooltip()
tooltip.show()
sys.exit(app.exec_())
