import sys
sys.path.append("../lr-parser/")
from PyQt4.QtCore import *
from PyQt4 import QtGui
from PyQt4.QtGui import *

from gui import Ui_MainWindow

from incparser import IncParser
from viewer import Viewer


grammar = """
    E ::= T
        | E "+" T
    T ::= P
        | T "*" P
    P ::= "1" | "2" | "3" | "4" | "5" | "6" | "7" | "8" | "9"
"""

class NodeEditor(QTextEdit):

    def __init__(self, text=None):
        self.lastpos = 0
        QTextEdit.__init__(self, text)

    def keyPressEvent(self, e):
        lrp = self.getLRP()
        current_node = self.getCurrentNodeFromPosition()
        print("Current Node:", current_node)

        QTextEdit.keyPressEvent(self, e)
        cursor = self.textCursor()
        pos = cursor.position()

        # type directly into current node
        if e.text() != "":
            if e.key() == 16777219:
                current_node.delete(pos)
            else:
                current_node.insert(e.text(), pos)
            # find all nodes that come after the changed node
            change = pos - self.lastpos
            lrp.previous_version.adjust_nodes_after_node(current_node, change)
            # mark changed nodes
            current_node.mark_changed()
        self.lastpos = pos

        self.parent().parent().btRefresh()

    def getCurrentNodeText(self):
        start = self.typing_start
        end = self.typing_end
        return self.toPlainText()[start:end]

    def getCurrentNodeFromPosition(self):
        cursor_pos = self.textCursor().position()
        ast = self.getLRP().previous_version
        print("POS", cursor_pos)
        return ast.find_node_at_pos(cursor_pos)

    def getLRP(self):
        return self.parent().parent().lrp

class Window(QtGui.QMainWindow):
    def __init__(self):
        QtGui.QMainWindow.__init__(self)
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)

        self.connect(self.ui.pushButton, SIGNAL("clicked()"), self.btReparse)
        self.connect(self.ui.pushButton_2, SIGNAL("clicked()"), self.btRefresh)

        self.lrp = IncParser(grammar, 1)
        self.lrp.init_ast()

    def btRefresh(self):
        image = Viewer().get_tree_image(self.lrp.previous_version.parent)
        self.showImage(self.ui.graphicsView, image)

    def btReparse(self):
        self.lrp.inc_parse()
        image = Viewer().get_tree_image(self.lrp.previous_version.parent)
        self.showImage(self.ui.graphicsView, image)

        image = Viewer().get_tree_image(self.lrp.get_stack_tree())
        self.showImage(self.ui.graphicsView_2, image)

    def showImage(self, graphicsview, imagefile):
        scene = QGraphicsScene()
        item = QGraphicsPixmapItem(QPixmap(imagefile))
        scene.addItem(item);
        graphicsview.setScene(scene)

def main():
    app = QtGui.QApplication(sys.argv)
    window=Window()

    window.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
