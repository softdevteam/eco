import sys
import simpleast
from PyQt4.QtCore import *
from PyQt4 import QtGui
from PyQt4.QtGui import *


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


class ProgramTree(object):

    def __init__(self, program):
        self.program = program


    def drawChildren(self, parent):

        left = Node(parent.ast.left)
        parent.setLeft(left)
        scene.addItem(left)
        line = NodeLine(parent, left)
        scene.addItem(line)

        right = Node(parent.ast.right)
        parent.setRight(right)
        scene.addItem(right)
        line = NodeLine(parent, right)
        scene.addItem(line)

        if isinstance(left.ast, simpleast.Expression):
            self.drawChildren(left)

        if isinstance(right.ast, simpleast.Expression):
            self.drawChildren(right)


    def draw(self):
        for s in p.statements:
            state_node = Node(s)
            scene.addItem(state_node)
            if isinstance(state_node.ast, simpleast.Expression):
                self.drawChildren(state_node)

app = QApplication(sys.argv)
grview = QGraphicsView()
scene = QGraphicsScene()

p = simpleast.createTestProgram2()
tree = ProgramTree(p)
tree.draw()

grview.setScene(scene)

grview.show()

sys.exit(app.exec_())
