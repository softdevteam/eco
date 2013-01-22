import sys
from PyQt4 import QtGui
from PyQt4 import QtCore

class LanguageEditor(QtGui.QFrame):

    def __init__(self, parent=None):
        QtGui.QWidget.__init__(self, parent)
        self.lrinput = LRInput([Token("some simple text"), Token("\n"), Token("and more")])

        self.font = QtGui.QFont('Courier', 9)
        self.fontm = QtGui.QFontMetrics(self.font)
        self.fontht = self.fontm.height()
        self.fontwt = self.fontm.width(" ")
        self.cursor = [0,0]

        # make cursor blink
        self.show_cursor = 0
        self.ctimer = QtCore.QTimer()
        QtCore.QObject.connect(self.ctimer, QtCore.SIGNAL("timeout()"), self.blink)
        self.ctimer.start(500)

    def set_lrparser(self, lrp):
        self.lrp = lrp

    def paintEvent(self, event):
        QtGui.QFrame.paintEvent(self, event)
        paint = QtGui.QPainter()
        paint.begin(self)
        paint.setFont(self.font)
        y = 1 + self.fontht
        x = 3
        for token in self.lrinput.content:
            if token.text == "\n":
                y += self.fontht
                x = 3
            else:
                paint.drawText(QtCore.QPointF(x, y), token.text)
                x += self.fontm.width(token.text)

        if self.hasFocus() and self.show_cursor:
            paint.drawRect(3 + self.cursor[0] * self.fontwt, 2 + self.cursor[1] * self.fontht, self.fontwt-1, self.fontht)

        paint.end()

    def paint_lrinput(self, paint):
        pass

    def keyPressEvent(self, e):

        if e.key() == QtCore.Qt.Key_Up:
            if self.cursor[1] > 0:
                self.cursor[1] -= 1
        elif e.key() == QtCore.Qt.Key_Down:
            if self.cursor[1] < 9: #XXX max lines
                self.cursor[1] += 1
        elif e.key() == QtCore.Qt.Key_Left:
            if self.cursor[0] > 0:
                self.cursor[0] -= 1
        elif e.key() == QtCore.Qt.Key_Right:
            if self.cursor[0] < 100: #XXX: len of line
                self.cursor[0] += 1
        elif e.key() == QtCore.Qt.Key_Backspace:
            if self.cursor[0] > 0:
                self.cursor[0] -= 1
                element, internalpos = self.find_token_at_cursor()
                element.delete(internalpos)
        elif e.key() == QtCore.Qt.Key_Delete:
            element, internalpos = self.find_token_at_cursor()
            element.delete(internalpos)
        elif e.key() == QtCore.Qt.Key_Return:
            pass
        elif e.text() == "":
            return
        else:
            element, internalpos = self.find_token_at_cursor()
            element.insert(e.text(), internalpos)
            self.cursor[0] += 1

        self.update()

    def find_token_at_cursor(self):
        #XXX: to avoid to search the token at the cursor position, always keep the current selected token in memory
        #     and move to the next, previous token from there
        #     left, right: select previous, next token
        #     up, down: only search in previous, next line

        token_iter = iter(self.lrinput.content)
        token = None

        # skip to line
        line = 0
        while line < self.cursor[1]:
            token = token_iter.next()
            if token.text == "\n":
                line += 1

        # find pos
        previous_tokens_length = 0
        token = token_iter.next()
        while previous_tokens_length + len(token) < self.cursor[0]:
            previous_tokens_length += len(token)
            token = token_iter.next()

        return (token, self.cursor[0] - previous_tokens_length)

    def blink(self):
        if self.show_cursor:
            self.show_cursor = 0
        else:
            self.show_cursor = 1
        self.update()

class Input(object):
    pass

class LRInput(Input):
    def __init__(self, content):
        self.content = content

    def __len__(self):
        result = 0
        for element in self.content:
            result += len(element)
        return result

    def insert(self, key, pos):
        self.content = self.content[:pos] + key + self.content[pos:]

class Token(object):
    def __init__(self, text):
        self.text = text

    def insert(self, key, pos):
        self.text = self.text[:pos] + key + self.text[pos:]

    def delete(self, pos):
        if pos < len(self) and pos >= 0:
            self.text = self.text[:pos] + self.text[pos+1:]

    def __len__(self):
        return len(self.text)
