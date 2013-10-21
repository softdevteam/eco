import json

from grammar_parser.gparser import Terminal, MagicTerminal, IndentationTerminal, Nonterminal
from incparser.astree import TextNode, BOS, EOS, ImageNode, FinishSymbol

class JsonManager(object):
    def __init__(self):
        self.last_terminal = None
        self.language_boxes = []

    def save(self, root, language, whitespaces, filename):
        main = {}
        root_json = self.node_to_json(root)
        main["root"] = root_json
        main["language"] = language
        main["whitespaces"] = whitespaces

        fp = open(filename, "w")
        json.dump(main, fp, indent=4)
        fp.close()

    def load(self, filename):
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
        jsnode["image"] = node.image

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
        node_class = eval(jsnode["class"])
        node_symbol = eval(jsnode["symbol"])

        symbol = node_symbol()
        symbol.name = jsnode["text"]
        node = node_class(symbol)
        assert node.symbol is symbol
        node.lookup = jsnode["lookup"]
        node.image = jsnode["image"]

        if isinstance(symbol, Terminal) or isinstance(symbol, FinishSymbol):
            node.prev_term = self.last_terminal
            if self.last_terminal is not None:
                self.last_terminal.next_term = node
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
            children.append(cnode)
            last_child = cnode
        node.children = children

        return node
