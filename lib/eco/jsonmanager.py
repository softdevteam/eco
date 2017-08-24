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

import json, gzip, sys
sys.setrecursionlimit(2000)

from grammar_parser.gparser import Terminal, MagicTerminal, IndentationTerminal, Nonterminal
from incparser.astree import TextNode, BOS, EOS, ImageNode, FinishSymbol
from PyQt4.QtGui import QImage

class JsonManager(object):
    def __init__(self, unescape=False):
        self.last_terminal = None
        self.language_boxes = []
        self.unescape = unescape

    def save(self, root, language, whitespaces, filename):
        main = {}
        root_json = self.node_to_json(root)
        main["root"] = root_json
        main["language"] = language
        main["whitespaces"] = whitespaces

        z = gzip.open(str(filename), "w")
        z.write(json.dumps(main))
        z.close()

    def load(self, filename):
        try:
            z = gzip.open(str(filename), "r")
            main = json.loads(z.read())
            z.close()
        except IOError:
            # backwards compatibility
            fp = open(filename, "r")
            main = json.load(fp)
            fp.close()

        language = main["language"]
        root_json = main["root"]
        whitespaces = main["whitespaces"]
        root = self.json_to_node(root_json)
        self.language_boxes.append((root, language, whitespaces))
        self.language_boxes.reverse()
        return self.language_boxes

    # XXX create Class for this task
    def node_to_json(self, node):
        # need lookup, image, symbol
        jsnode = {}
        jsnode["class"] = node.__class__.__name__
        jsnode["symbol"] = node.symbol.__class__.__name__
        jsnode["text"] = node.symbol.name
        jsnode["lookup"] = node.lookup
        jsnode["local_error"] = node.local_error
        jsnode["nested_errors"] = node.nested_errors
        jsnode["image_src"] = node.image_src

        children = []
        for c in node.children:
            c_json = self.node_to_json(c)
            children.append(c_json)

        if isinstance(node.symbol, MagicTerminal):
            root = self.node_to_json(node.symbol.ast)
            jsnode["lbox"] = root
            jsnode["language"] = node.symbol.name[1:-1]
            jsnode["whitespaces"] = True

        jsnode["children"] = children
        return jsnode

    def json_to_node(self, jsnode):
        node_class = globals()[jsnode["class"]]
        node_symbol = globals()[jsnode["symbol"]]

        symbol = node_symbol()
        symbol.name = jsnode["text"].encode("utf-8")
        if self.unescape:
            symbol.name = symbol.name.decode("string-escape")
        node = node_class(symbol)
        assert node.symbol is symbol
        node.lookup = jsnode["lookup"]
        try:
            node.local_error = jsnode["local_error"]
            node.nested_errors = jsnode["nested_errors"]
        except KeyError:
            pass # Backwards compatibility for old Eco files
        node.image_src = jsnode["image_src"]
        if node.image_src is not None:
            node.image = QImage(node.image_src)

        if isinstance(symbol, Terminal) or isinstance(symbol, FinishSymbol):
            node.prev_term = self.last_terminal
            if self.last_terminal is not None:
                self.last_terminal.next_term = node
                self.last_terminal.save(0)
            self.last_terminal = node

        if "lbox" in jsnode:
            temp = self.last_terminal
            self.last_terminal = None
            lbox_root = self.json_to_node(jsnode["lbox"])
            lbox_root.magic_backpointer = node
            node.symbol.ast = lbox_root
            node.symbol.parser = lbox_root
            self.last_terminal = temp
            self.language_boxes.append((lbox_root, jsnode["language"], jsnode["whitespaces"]))

        children = []
        last_child = None
        for c in jsnode["children"]:
            cnode = self.json_to_node(c)
            cnode.parent = node
            cnode.left = last_child
            if last_child:
                last_child.right = cnode
                last_child.save(0)
            cnode.save(0)
            children.append(cnode)
            last_child = cnode
        node.children = children
        node.calc_textlength()
        node.save(0)

        return node
