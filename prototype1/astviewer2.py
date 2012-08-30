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

def drawTree(scene, tree):
    scene.addItem(tree)
    if not tree.left is None:
        scene.addItem(tree.left)
    if not tree.right is None:
        scene.addItem(tree.right)

app = QApplication(sys.argv)
grview = QGraphicsView()
scene = QGraphicsScene()

parent = Node("parent")
child1 = Node("child1")
child2 = Node("child2")
parent.setLeft(child1)
parent.setRight(child2)

#drawTree(scene, parent)
p = simpleast.createTestProgram()
for s in p.statements:
    st_node = Node(s.getName())
    scene.addItem(st_node)
    if isinstance(s, simpleast.AddExpression):
        expr_node = Node(s.getName())
        left_node = Node(s.left.getName())
        right_node = Node(s.right.getName())
        expr_node.setLeft(left_node)
        expr_node.setRight(right_node)
        scene.addItem(expr_node)
        scene.addItem(left_node)
        scene.addItem(right_node)


grview.setScene(scene)

grview.show()

sys.exit(app.exec_())
