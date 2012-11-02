from __future__ import print_function

import sys
sys.path.append("../")
sys.path.append("../lr-parser/")

from PyQt4.QtCore import *
from PyQt4 import QtGui
from PyQt4.QtGui import *

from gui import Ui_MainWindow

from plexer import PriorityLexer
from incparser import IncParser
from viewer import Viewer

from gparser import Terminal
from astree import TextNode


grammar = """
    E ::= T
        | E "+" T
    T ::= P
        | T "*" P
    P ::= "INT"
"""

priorities = """
    "[0-9]+":INT
    "[+]":+
    "[*]":*
"""

class NodeEditor(QTextEdit):

    def __init__(self, text=None):
        self.lastpos = 0
        QTextEdit.__init__(self, text)

    def keyPressEvent(self, e):
        print("====================== KEYPRESS ============================")
        lrp = self.getLRP()
        if self.document().isEmpty():
            lrp.init_ast()

        selected_nodes = self.getNodesAtPosition()
        print("Selected Nodes:", selected_nodes)

        QTextEdit.keyPressEvent(self, e)

        cursor = self.textCursor()
        pos = cursor.position()

        # type directly into current node
        print(e.key())
        if e.text() != "":
            self.change_node_by_priority(selected_nodes, str(e.text()), pos)
            #if e.key() == 16777219:
            #    selected_node.backspace(pos)
            #elif e.key() == 16777223:
            #    selected_node.delete(pos)
            #else:
            #    selected_node.insert(str(e.text()), pos)
            # find all nodes that come after the changed node
            change = pos - self.lastpos
            lrp.previous_version.adjust_nodes_after_node(selected_nodes, change)
            # mark changed nodes
            #selected_node.mark_changed()
        self.lastpos = pos

        selected_nodes = self.getNodesAtPosition()
        self.parent().parent().btReparse(selected_nodes)

        self.parent().parent().showLookahead()

    def change_node(self, node, text, pos):
        # special case: empty starting node
        if node.symbol.name == "":
            node.change_text(text)
            node.regex = self.getPL().regex(text)
            node.lookup = self.getPL().name(text)
            return True

        new_text = list(node.symbol.name)
        new_text.insert(pos, text)
        print("Check match", node, "matches", "".join(new_text), "using", node.regex)
        if node.matches("".join(new_text)):
            print("Sucess")
            node.change_text("".join(new_text))
            return True
        else:
            print("Fail")
            return False

    def change_node_by_priority(self, nodes, text, pos):
        try:
            nodes.remove(None)
        except ValueError:
            pass
        sorted_nodes = sorted(nodes, key=lambda node: node.priority)

        for node in sorted_nodes:
            result = self.change_node(node, text, pos)
            if result:
                return
        # no match => create new node(s) (split if necessary)
        symbol = Terminal(text)
        state = -1
        children = []
        pos = pos
        regex = self.getPL().regex(text)
        priorit = self.getPL().priority(text)
        new_node = TextNode(symbol, state, children, pos)
        new_node.regex = regex
        new_node.lookup = self.getPL().name(text)
        # add to left node
        sorted_nodes[0].parent.insert_after_node(sorted_nodes[0], new_node)

    def getCurrentNodeText(self):
        start = self.typing_start
        end = self.typing_end
        return self.toPlainText()[start:end]

    def getNodesAtPosition(self):
        pl = self.getPL()
        #XXX return only one node if "inside" text
        cursor_pos = self.textCursor().position()
        ast = self.getLRP().previous_version
        nodes = ast.get_nodes_at_position(cursor_pos)
        return nodes

    def getPL(self):
        return self.parent().parent().pl

    def getLRP(self):
        return self.parent().parent().lrp

class Window(QtGui.QMainWindow):
    def __init__(self):
        QtGui.QMainWindow.__init__(self)
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)

        #self.connect(self.ui.pushButton, SIGNAL("clicked()"), self.btReparse)
        #self.connect(self.ui.pushButton_2, SIGNAL("clicked()"), self.btRefresh)

        self.lrp = IncParser(grammar, 1)
        self.lrp.init_ast()

        self.pl = PriorityLexer(priorities)

    def btRefresh(self):
        image = Viewer().get_tree_image(self.lrp.previous_version.parent)
        self.showImage(self.ui.graphicsView, image)

    def btReparse(self, selected_node):
        self.lrp.inc_parse()
        image = Viewer('pydot').get_tree_image(self.lrp.previous_version.parent, selected_node)
        self.showImage(self.ui.graphicsView, image)

    def showLookahead(self):
        la = self.lrp.get_next_symbols_string()
        self.ui.lineEdit.setText(la)

    def showImage(self, graphicsview, imagefile):
        scene = QGraphicsScene()
        item = QGraphicsPixmapItem(QPixmap(imagefile))
        scene.addItem(item);
        graphicsview.setScene(scene)

def main():
    app = QtGui.QApplication(sys.argv)
    app.setStyle('cde')
    window=Window()

    window.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
