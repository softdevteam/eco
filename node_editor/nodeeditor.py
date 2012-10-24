import sys
from PyQt4.QtCore import *
from PyQt4 import QtGui
from PyQt4.QtGui import *

from gui import Ui_MainWindow

class NodeEditor(QTextEdit):

    def __init__(self, text=None):
        self.nodes = [TextNode([], 0)]
        self.current_node_text = []
        self.typing_start = 0
        self.typing_end = 0
        self.lastpos = 0
        QTextEdit.__init__(self, text)

    def keyPressEvent(self, e):
        current_node = self.getCurrentNodeFromPosition()
        print(current_node)
        print(e.key())

        QTextEdit.keyPressEvent(self, e)
        cursor = self.textCursor()
        pos = cursor.position()

        if e.key() == 32: # key=space
            self.typing_end = pos-1
            # create new node
            node = TextNode([], pos)
            self.nodes.append(node)
            self.current_node_text = []
            # reset variables
            self.typing_start = pos
        else:
            # type directly into current node
            if e.text() != "":
                if e.key() == 16777219:
                    current_node.delete(pos)
                else:
                    current_node.insert(e.text(), pos)
                # find all nodes that come after the changed node
                change = pos - self.lastpos
                found = False
                for n in self.nodes:
                    if found:
                        n.pos += change
                    if n is current_node:
                        found = True
        self.lastpos = pos
        print(self.nodes)

    def getCurrentNodeText(self):
        start = self.typing_start
        end = self.typing_end
        return self.toPlainText()[start:end]

    def getCurrentNodeFromPosition(self):
        #XXX not very fast
        cursor_pos = self.textCursor().position()
        for node in self.nodes:
            if node.pos + len(node.text) >= cursor_pos:
                return node

class TextNode(object):
    def __init__(self, text, pos):
        self.text = text
        self.pos = pos

    def change_pos(self, i):
        self.pos += i

    def change_text(self, text):
        self.text = text

    def insert(self, char, pos):
        internal_pos = pos - self.pos
        self.text.insert(internal_pos-1, char)

    def delete(self, pos):
        internal_pos = pos - self.pos
        self.text.pop(internal_pos)

    def __repr__(self):
        return "(%s, %s)" % ("".join(self.text), self.pos)

class Window(QtGui.QMainWindow):
    def __init__(self):
        QtGui.QMainWindow.__init__(self)
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)

def main():
    app = QtGui.QApplication(sys.argv)
    window=Window()

    window.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
