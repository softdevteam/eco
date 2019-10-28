# Copyright (c) 2013--2014 King's College London
# Created by the Software Development Team <http://soft-dev.org/>
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to
# deal in the Software without restriction, including without limitation the
# rights to use, copy, modify, merge, publish, distribute, sublicense, and/or
# sell copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
# FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS
# IN THE SOFTWARE.

import sys
try:
    # checkout https://github.com/Brittix1023/mipy into eco/lib/
    sys.path.append("../mipy")
    from mipy import kernel, request_listener
    has_mipy = True
except ImportError:
    has_mipy = False
from incparser.astree import TextNode, EOS  #BOS, ImageNode, FinishSymbol
from grammar_parser.gparser import IndentationTerminal # BOS, MagicTerminal, Nonterminal
from PyQt5 import QtCore
from PyQt5.QtGui import QPen, QColor, QImage
from PyQt5.QtWidgets import QApplication

import math, os

class Renderer(object):

    def __init__(self, fontwt, fontht, fontd):
        self.fontwt = fontwt
        self.fontht = fontht
        self.fontd  = fontd

    def paint_node(self, paint, node, x, y, highlighter):
        raise NotImplementedError

    def nextNode(self, node):
        node = node.next_term
        if isinstance(node, EOS):
            return None

    def update_image(self, node):
        pass

    def setStyle(self, paint, style):
        f = paint.font()
        if style == "italic":
            f.setItalic(True)
            f.setBold(False)
        elif style == "bold":
            f.setItalic(False)
            f.setBold(True)
        else:
            f.setItalic(False)
            f.setBold(False)

        paint.setFont(f)

class NormalRenderer(Renderer):
    def paint_node(self, paint, node, x, y, highlighter):
        dx, dy = (0, 0)
        if node.symbol.name == "\r" or isinstance(node, EOS):
            return dx, dy
        if isinstance(node.symbol, IndentationTerminal):
            paint.setPen(QPen(QColor("#aa3333")))
            self.setStyle(paint, highlighter.get_style(node))
            if QApplication.instance().showindent is True:
                if node.symbol.name == "INDENT":
                    text = ">"
                elif node.symbol.name == "DEDENT":
                    text = "<"
                else:
                    return dx, dy
                paint.drawText(QtCore.QPointF(x, 3 + self.fontht + y*self.fontht - self.fontd), text)
                return 1*self.fontwt, dy
            else:
                return dx, dy
        if isinstance(node, TextNode):
            paint.setPen(QPen(QColor(highlighter.get_color(node))))
            self.setStyle(paint, highlighter.get_style(node))
            text = node.symbol.name
            if not (node.lookup == "<ws>" and node.symbol.name.startswith(" ")): # speedhack: don't draw invisible nodes
                paint.drawText(QtCore.QPointF(x, 3 + self.fontht + y*self.fontht - self.fontd), text)
            dx = len(text) * self.fontwt
            dy = 0
        return dx, dy

    def doubleClick(self):
        pass # select/unselect

class ImageRenderer(NormalRenderer):

    def paint_node(self, paint, node, x, y, highlighter):
        self.update_image(node)
        dx, dy = (0, 0)
        if node.image is not None and not node.plain_mode:
            paint.drawImage(QtCore.QPoint(x, 3 + y * self.fontht), node.image)
            dx = int(math.ceil(node.image.width() * 1.0 / self.fontwt) * self.fontwt)
            dy = int(math.ceil(node.image.height() * 1.0 / self.fontht))
        else:
            dx, dy = NormalRenderer.paint_node(self, paint, node, x, y, highlighter)
        return dx, dy

    def get_filename(self, node):
        return node.symbol.name

    def update_image(self, node):
        filename = self.get_filename(node)
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

class ChemicalRenderer(ImageRenderer):
    def get_filename(self, node):
        return "chemicals/" + node.symbol.name + ".png"

if not has_mipy:
    class IPythonRenderer(NormalRenderer):
        pass
else:
    class IPythonRenderer(NormalRenderer):
        proc = kernel.IPythonKernelProcess()

        def paint_node(self, paint, node, x, y, highlighter):
            lbox = node.get_root().get_magicterminal()
            if lbox.plain_mode:
                return NormalRenderer.paint_node(self, paint, node, x, y, highlighter)
            else:
                dx, dy = NormalRenderer.paint_node(self, paint, node, x, y, highlighter)
                if isinstance(node.next_term, EOS):
                    content = self.get_content(lbox)
                    try:
                        krn = IPythonRenderer.proc.connection

                        if krn is not None:
                            listener = IPythonExecuteListener()
                            krn.execute_request(content, listener=listener)
                            while not listener.finished:
                                krn.poll(-1)
                            text = str(listener.result)
                    except Exception as e:
                        text = e.message
                    paint.drawText(QtCore.QPointF(x+100, self.fontht + y*self.fontht), " | "+text)
                return dx, dy

        def get_content(self, lbox):
            node = lbox.symbol.ast.children[0].next_term
            l = []
            while not isinstance(node, EOS):
                if not isinstance(node.symbol, IndentationTerminal):
                    l.append(node.symbol.name)
                node = node.next_term
            return "".join(l)

    class IPythonExecuteListener(request_listener.ExecuteRequestListener):
        def __init__(self):
            self.result = None
            self.finished = False

        def on_execute_result(self, execution_count, data, metadata):
            self.result = data['text/plain']

        def on_execute_finished(self):
            self.finished = True

        def on_error(self, ename, value, traceback):
            raise Exception(ename)

def get_renderer(parent, fontwt, fontht, fontd):
    if parent == "Chemicals":
        return ChemicalRenderer(fontwt, fontht, fontd)
    if parent == "Image":
        return ImageRenderer(fontwt, fontht, fontd)
    if parent == "IPython":
        return IPythonRenderer(fontwt, fontht, fontd)
    return NormalRenderer(fontwt, fontht, fontd)
