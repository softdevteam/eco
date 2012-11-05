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
            if e.key() == 16777219:
                selected_nodes[0].backspace(pos)
            elif e.key() == 16777223:
                if selected_nodes[1] is not None:
                    selected_nodes[1].backspace(pos)
                else:
                    selected_nodes[0].backspace(pos)
            else:
                self.apply_change_to_nodes(selected_nodes, str(e.text()), pos)
            #else:
            #    selected_node.insert(str(e.text()), pos)
            # find all nodes that come after the changed node
            change = pos - self.lastpos
            #lrp.previous_version.adjust_nodes_after_node(selected_nodes, change)
            # mark changed nodes
            #selected_node.mark_changed()
        self.lastpos = pos

        selected_nodes = self.getNodesAtPosition()
        self.parent().parent().btReparse(selected_nodes)

        self.parent().parent().showLookahead()

    def change_node(self, node, text, pos):
        print("change_node", node, text, pos)
        if node is None:
            return None

        #XXX bos and eos not changable
        # special case: empty starting node
        if node.symbol.name == "":
            print("    node is empty")
            node.change_text(text)
            node.regex = self.getPL().regex(text)
            node.lookup = self.getPL().name(text)
            return True

        print("   not empty")
        new_text = list(node.symbol.name)
        internal_position = pos - node.position - 1
        new_text.insert(internal_position, text)
        if node.matches("".join(new_text)):
            node.change_text("".join(new_text))
            print("   node changed", node)
            return True
        else:
            print("   not changed")
            return False

    def apply_change_to_nodes(self, nodes, text, pos):
        print("apply_changes", nodes, text, pos)
        try:
            nodes.remove(None)
        except:
            pass
        # sort nodes by priority
        sorted_nodes = sorted(nodes, key=lambda node: node.priority)

        # CASE 1: inside text -> change or split
        if len(sorted_nodes) == 1:
            node = sorted_nodes[0]
            internal_pos = pos - node.position - 1
            result = self.change_node(node, text, pos)
            if result:
                return
            text1 = node.symbol.name[:internal_pos]
            text2 = node.symbol.name[internal_pos:]
            text3 = text
            print(text1, text2, text3)

            node.change_text(text1) # this may result in a invalid node
            node2 = self.create_new_node(text2)
            node.parent.insert_after_node(node, node2)
            self.apply_change_to_nodes([node, node2], text, pos)

            return

        # CASE 2: between two nodes -> choose correct node and change it

        for node in sorted_nodes:
            # try to change node and continue with the next one if the change isn't valid
            result = self.change_node(node, text, pos)
            if result:
                return
        # if none of the nodes matches, insert a new node
        print("no match at all, creating new node instead. insertion after", nodes[0])
        new_node = self.create_new_node(text)
        # add to left node
        nodes[0].parent.insert_after_node(nodes[0], new_node)

    def create_new_node(self, text):
        symbol = Terminal(text)
        node = TextNode(symbol, -1, [], -1)
        node.regex = self.getPL().regex(text)
        node.priority = self.getPL().priority(text)
        node.lookup = self.getPL().name(text)
        return node

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
