import json
from grammar_parser.gparser import Nonterminal, Terminal, MagicTerminal, IndentationTerminal
from incparser.astree import TextNode, BOS, EOS, ImageNode, FinishSymbol
from version_control import gumtree_driver
from PyQt4.QtGui import QImage

# Handles trees of the form:
# 
# {
#     "__type__": "EcoTree",
#     "tree": <tree>
# }
# 
# where <tree> is an ordered tree of nodes, of the form:
# 
# {
#     "__type__": "TreeNode",
#     "label": string,
#     "type": integer,
#     "type_label": string,
#     "pos": integer,
#     "length": integer,
#     "children": [array of child nodes]
# }



_name_to_symbol_class = {
    'Nonterminal': Nonterminal,
    'Terminal': Terminal,
    'MagicTerminal': MagicTerminal,
    'IndentationTerminal': IndentationTerminal,
    'FinishSymbol': FinishSymbol,
}

_name_to_eco_node_class = {
    'TextNode': TextNode,
    'BOS': BOS,
    'EOS': EOS,
    'ImageNode': ImageNode,
    'FinishSymbol': FinishSymbol,
}


class _GumtreeImporter (object):
    def __init__(self):
        self.__last_terminal = None
        self.language_boxes = []

    def import_subtree(self, gt_node, unescape=False):
        jsnode = json.loads(gt_node.value)

        node_class = _name_to_eco_node_class[jsnode["class"]]
        node_symbol = _name_to_symbol_class[jsnode["symbol"]]

        symbol = node_symbol()
        symbol.name = jsnode["text"].encode("utf-8")
        if unescape:
            symbol.name = symbol.name.decode("string-escape")
        node = node_class(symbol)
        assert node.symbol is symbol
        node.lookup = jsnode["lookup"]
        node.image_src = jsnode["image_src"]
        if node.image_src is not None:
            node.image = QImage(node.image_src)

        if isinstance(symbol, Terminal) or isinstance(symbol, FinishSymbol):
            node.prev_term = self.__last_terminal
            if self.__last_terminal is not None:
                self.__last_terminal.next_term = node
            self.__last_terminal = node

        children = []
        if "language" in jsnode:
            temp = self.__last_terminal
            self.__last_terminal = None
            lbox_root = self.import_subtree(gt_node[0])
            lbox_root.magic_backpointer = node
            node.symbol.ast = lbox_root
            node.symbol.parser = lbox_root
            self.__last_terminal = temp
            self.language_boxes.append((lbox_root, jsnode["language"], jsnode["whitespaces"]))
        else:
            last_child = None
            for c in gt_node:
                cnode = self.import_subtree(c)
                cnode.parent = node
                cnode.left = last_child
                if last_child:
                    last_child.right = cnode
                children.append(cnode)
                last_child = cnode
        node.children = children

        return node


def _export_subtree(node, symbol_name_to_id, position):
    js_value = {}
    js_value["class"] = node.__class__.__name__
    js_value["symbol"] = node.symbol.__class__.__name__
    js_value["lookup"] = node.lookup
    js_value["image_src"] = node.image_src
    js_value['text'] = node.symbol.name

    if isinstance(node.symbol, Nonterminal):
        children = []
        current_position = position
        for child_node in node.children:
            gumtree_child = _export_subtree(child_node, symbol_name_to_id, current_position)
            if gumtree_child is not None:
                current_position += gumtree_child.length
                children.append(gumtree_child)
        type_id = symbol_name_to_id[node.symbol.name]

        value = json.dumps(js_value, sort_keys=True)
        return gumtree_driver.GumtreeNode(type_id=type_id, type_label=node.symbol.name, position=position,
                                          length=current_position - position, value=value, children=children)
    elif isinstance(node.symbol, Terminal):
        type_label = '__terminal__'
        type_id = symbol_name_to_id[type_label]

        value = json.dumps(js_value, sort_keys=True)
        return gumtree_driver.GumtreeNode(type_id=type_id, type_label=type_label, position=node.position, length=1,
                                          value=value, children=[])
    elif isinstance(node.symbol, MagicTerminal):
        root = _export_subtree(node.symbol.ast, symbol_name_to_id, 0)
        type_label = '__magic_terminal__'
        type_id = symbol_name_to_id[type_label]

        js_value['language'] = node.symbol.name[1:-1]
        value = json.dumps(js_value, sort_keys=True)
        return gumtree_driver.GumtreeNode(type_id=type_id, type_label=type_label, position=node.position, length=1,
                                          value=value, children=[root])
    else:
        return None



def import_gumtree(doc):
    importer = _GumtreeImporter()
    return importer.import_subtree(doc.root)


def export_gumtree(root_node, syntaxtable):
    # Build the rule to ID mapping
    # Get the keys of the table that are of the form (state, symbol)
    keys = syntaxtable.table.keys()
    # Extract the symbols
    symbols = [symbol for state, symbol in keys]
    # Get the symbol names
    symbol_names = [symbol.name for symbol in symbols]
    # Sort to ensure consistent name -> index mapping
    symbol_names.sort()
    # Build the mapping
    symbol_name_to_id = {symbol_name: i for i, symbol_name in enumerate(symbol_names)}
    symbol_name_to_id['__terminal__'] = len(symbol_name_to_id)
    symbol_name_to_id['__magic_terminal__'] = len(symbol_name_to_id)
    symbol_name_to_id['Root'] = len(symbol_name_to_id)

    eco_subtree = _export_subtree(root_node, symbol_name_to_id, 0)
    doc = gumtree_driver.GumtreeDocument(eco_subtree)

    return doc


def export_gumtree_as_string(root_node, syntaxtable):
    doc = export_gumtree(root_node, syntaxtable)
    js = doc.as_json()
    return json.dumps(js)