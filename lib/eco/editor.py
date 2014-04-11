from incparser.astree import TextNode, BOS, EOS, ImageNode, FinishSymbol
from grammar_parser.gparser import Terminal, MagicTerminal, IndentationTerminal, Nonterminal
from PyQt4 import QtCore
from PyQt4.QtGui import QPen, QColor, QImage

import math, os

class Editor(object):

    def __init__(self, fontwt, fontht):
        self.fontwt = fontwt
        self.fontht = fontht

    def paint_node(self, paint, node, x, y, highlighter):
        raise NotImplementedError

    def nextNode(self, node):
        node = node.next_term
        if isinstance(node, EOS):
            return None

    def update_image(self, node):
        pass

class NormalEditor(Editor):
    def paint_node(self, paint, node, x, y, highlighter):
        dx, dy = (0, 0)
        if node.symbol.name == "\r" or isinstance(node, EOS) or isinstance(node.symbol, IndentationTerminal):
            return dx, dy
        if isinstance(node, TextNode):
            paint.setPen(QPen(QColor(highlighter.get_color(node))))
            text = node.symbol.name
            paint.drawText(QtCore.QPointF(x, self.fontht + y*self.fontht), text)
            #print("drawing node", text, "at", x,y)
            dx = len(text) * self.fontwt
            dy = 0
        return dx, dy

    def doubleClick(self):
        pass # select/unselect

class ImageEditor(NormalEditor):

    def paint_node(self, paint, node, x, y, highlighter):
        self.update_image(node)
        dx, dy = (0, 0)
        if node.image is not None and not node.plain_mode:
            paint.drawImage(QtCore.QPoint(x, 3 + y * self.fontht), node.image)
            dx = int(math.ceil(node.image.width() * 1.0 / self.fontwt) * self.fontwt)
            dy = int(math.ceil(node.image.height() * 1.0 / self.fontht))
        else:
            dx, dy = NormalEditor.paint_node(self, paint, node, x, y, highlighter)
        return dx, dy

    def update_image(self, node):
        filename = "chemicals/" + node.symbol.name + ".png"
        if node.image_src == filename:
            return
        if os.path.isfile(filename):
            node.image = QImage(filename)
            node.image_src = filename
        else:
            node.image = None
            node.image_src = None

    def doubleClick(self):
        pass # switch between display modes

def get_editor(parent, fontwt, fontht):
    if parent == "Chemicals":
        return ImageEditor(fontwt, fontht)
    return NormalEditor(fontwt, fontht)
