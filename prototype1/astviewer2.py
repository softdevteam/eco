import sys
import simpleast
from PyQt4.QtCore import *
from PyQt4 import QtGui
from PyQt4.QtGui import *

from gui.simplegui import Ui_MainWindow


class Node(QGraphicsEllipseItem):

    def __init__(self, ast):
        QGraphicsEllipseItem.__init__(self, 0,0,50,50)
        self.ast = ast
        self.left = left
        self.right = right
        self.setFlag(QtGui.QGraphicsItem.ItemIsMovable)

    def paint(self, painter, option, widget):
        QGraphicsEllipseItem.paint(self, painter, option, widget)
        painter.drawText(5,25, self.ast.getText())

    def setLeft(self, left):
        self.left = left
        self.left.parent = self
        self.left.setPos(self.pos() + QPointF(-50,100))

    def setRight(self, right):
        self.right = right
        self.right.setPos(self.pos() + QPointF(50,100))

    def getCenter(self):
        return self.pos() + QPointF(25,25)

class NodeLine(QGraphicsLineItem):

    def __init__(self, parent, child):
        QGraphicsLineItem.__init__(self, 0,0,0,0)
        self.parent = parent
        self.child = child

    def paint(self, painter, option, widget):
        x1 = self.parent.getCenter().x()
        y1 = self.parent.getCenter().y()
        x2 = self.child.getCenter().x()
        y2 = self.child.getCenter().y()
        self.setLine(QLineF(x1,y1,x2,y2))
        QGraphicsLineItem.paint(self, painter, option, widget)


class AstEditor(QTextEdit):

    def __init__(self, text=None):
        QTextEdit.__init__(self, text)

    def setGrammar(self, program):
        self.program = program

    def setTree(self, tree):
        # only necessary to notify the tree that the program has changed
        self.tree = tree

    def keyPressEvent(self, e):
        QTextEdit.keyPressEvent(self, e)
        # space = 32

        laststatement = None
        if len(self.program.statements) > 0:
            laststatement = self.program.statements[-1]

        if 48 <= e.key() <= 57: # numbers 0-9
            if isinstance(laststatement, simpleast.AddExpression):
                print("adding to last expression")
                laststatement.setRight(simpleast.IntLiteral(e.text()))
            else:
                self.program.addStatement(simpleast.IntLiteral(e.text()))

        if e.key() == 43: # +
            # get last statement and remove it from statement list
            last_statement = self.program.statements.pop(-1)
            add_expr = simpleast.AddExpression()
            add_expr.setLeft(last_statement)
            self.program.statements.append(add_expr)
        print(self.program.statements)

        self.tree.draw()
        print(e.key())

class ProgramTree(object):

    def __init__(self, program, scene):
        self.program = program
        self.scene = scene

    def drawChildren(self, parent):

        left = Node(parent.ast.left)
        parent.setLeft(left)
        self.scene.addItem(left)
        line = NodeLine(parent, left)
        self.scene.addItem(line)

        right = Node(parent.ast.right)
        parent.setRight(right)
        self.scene.addItem(right)
        line = NodeLine(parent, right)
        self.scene.addItem(line)

        if isinstance(left.ast, simpleast.Expression):
            self.drawChildren(left)

        if isinstance(right.ast, simpleast.Expression):
            self.drawChildren(right)

    def draw(self):
        # clear all nodes and lines, since we are going to recreate everything
        # XXX: reuse already created qtgraphic items and just move them to their new position
        for item in self.scene.items():
            if isinstance(item, Node) or isinstance(item, NodeLine):
                self.scene.removeItem(item)
        for s in self.program.statements:
            state_node = Node(s)
            self.scene.addItem(state_node)
            if isinstance(state_node.ast, simpleast.Expression):
                self.drawChildren(state_node)

class Window(QtGui.QMainWindow):
    def __init__(self):
        QtGui.QMainWindow.__init__(self)
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)

        # add a QGraphicsScene to the GUIs QGraphicsView on which we can then
        # draw the AST
        self.scene = QGraphicsScene()
        self.ui.graphicsView.setScene(self.scene)



def main():
    app = QtGui.QApplication(sys.argv)
    window=Window()

    p = simpleast.Program()

    # draw the tree
    tree = ProgramTree(p, window.scene)
    tree.draw()

    # set grammar to use by editor
    window.ui.plainTextEdit.setGrammar(p)
    window.ui.plainTextEdit.setTree(tree)

    window.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()

#app = QApplication(sys.argv)
#grview = QGraphicsView()
#scene = QGraphicsScene()
#
#p = simpleast.Program()
#tree = ProgramTree(p)
#tree.draw()
#
#qtextedit = AstEditor(p)
#qtextedit.move(-500,0)
#scene.addWidget(qtextedit)
#
#grview.setScene(scene)
#
#grview.show()
#
#sys.exit(app.exec_())
