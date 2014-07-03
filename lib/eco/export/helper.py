# Copyright (c) 2014 King's College London
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


from PyQt4 import QtGui

from incparser.astree import BOS, EOS, TextNode
from grammar_parser.gparser import MagicTerminal, IndentationTerminal


class Generic:
    def __init__(self):
        self.buf = []

    def pp(self, node):
        self.walk(node)
        return "".join(self.buf)

    def walk(self, node):
        while True:
            node = node.next_term
            sym = node.symbol
            print type(node), type(sym), sym.name
            if isinstance(node, EOS):
                break
            assert isinstance(node, TextNode)
            if isinstance(sym, MagicTerminal):
                self.language_box(sym.name, node.symbol.ast.children[0])
            elif isinstance(sym, IndentationTerminal):
                pass
            elif sym.name == "\r":
                self.text("\n")
            else:
                self.text(sym.name)

    def language_box(self, name, node):
        error("Incorrectly nested language box '%s'." % name)

    def text(self, text):
        self.buf.append(text)


def error(msg):
    d = QtGui.QMessageBox(QtGui.QMessageBox.Warning, "Warning", "Unexpected node type: %s" % msg,
      QtGui.QMessageBox.NoButton)
    d.addButton("&Abort", QtGui.QMessageBox.RejectRole)
    d.exec_()
    raise Exception("Export abort")


def bad_node(name):
    error("Not expecting to see node of type '%s'." % name)
