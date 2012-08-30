import sys
import simpleast
from PyQt4.QtCore import *
from PyQt4 import QtGui
from PyQt4.QtGui import *


class Node(QGraphicsEllipseItem):

    def __init__(self, name):
        QGraphicsEllipseItem.__init__(self, 0,0,50,50)
        self.name = name
        self.left = left
        self.right = right
        self.setFlag(QtGui.QGraphicsItem.ItemIsMovable)

    def paint(self, painter, option, widget):
        QGraphicsEllipseItem.paint(self, painter, option, widget)
        painter.drawText(5,25, self.name)

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


def drawChildren(parent, parentnode):

    left_node = Node(parent.left.getText())
    parentnode.setLeft(left_node)
    scene.addItem(left_node)
    line = NodeLine(parentnode, left_node)
    scene.addItem(line)

    right_node = Node(parent.right.getText())
    parentnode.setRight(right_node)
    scene.addItem(right_node)
    line = NodeLine(parentnode, right_node)
    scene.addItem(line)

    if isinstance(parent.left, simpleast.Expression):
        drawChildren(parent.left, left_node)

    if isinstance(parent.right, simpleast.Expression):
        drawChildren(parent.right, right_node)

app = QApplication(sys.argv)
grview = QGraphicsView()
scene = QGraphicsScene()

p = simpleast.createTestProgram2()
for s in p.statements:
    state_node = Node(s.getText())
    scene.addItem(state_node)
    if isinstance(s, simpleast.Expression):
        drawChildren(s, state_node)

grview.setScene(scene)

grview.show()

sys.exit(app.exec_())
