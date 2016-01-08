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



class GumtreeExporter (object):
    def __init__(self, tree_managers, compact=False):
        self.type_name_to_id = {}
        self.type_id_counter = 1
        self.languages = set()
        self.compact = compact

        # For each language in each tree manager
        for tree_manager in tree_managers:
            for pll in tree_manager.parsers:
                parser, lexer, lang, _ = pll[:4]
                # If the language has not yet been encountered:
                if lang not in self.languages:
                    self.languages.add(lang)

                    # Get its syntax table
                    syntaxtable = parser.syntaxtable

                    # Populate the rule to ID mapping
                    # Get the keys of the table that are of the form (state, symbol)
                    keys = syntaxtable.table.keys()
                    # Extract the symbols
                    symbols = [symbol for state, symbol in keys]
                    # Get the symbol names
                    symbol_names = [symbol.name for symbol in symbols]
                    # Sort to ensure consistent name -> index mapping
                    symbol_names.sort()
                    # Build the mapping
                    for symbol_name in symbol_names:
                        self._register_type_label(self.type_name(lang, symbol_name))
                    self._register_type_label(self.type_name(lang, 'Root'))

        self._register_type_label('__terminal__')
        self._register_type_label('__magic_terminal__')
        self._register_type_label('__ROOT__')


    def _register_type_label(self, type_label):
        self.type_name_to_id[type_label] = self.type_id_counter
        self.type_id_counter += 1


    def export_gumtree(self, tree_manager):
        root_node = tree_manager.get_bos().get_root()
        root_lang = tree_manager.parsers[0][2]
        root_ws = tree_manager.get_mainparser().whitespaces

        root_type_label = '__ROOT__'
        root_type_id = self.type_name_to_id[root_type_label]
        root_value = {'language': root_lang, 'whitespaces': root_ws}

        eco_subtree = self._export_subtree(root_node, root_lang, 0)
        children = [eco_subtree]
        if self.compact:
            children = self._filter_child_list(children)
        eco_tree = gumtree_driver.GumtreeNode(type_id=root_type_id, type_label=root_type_label,
                                              position=eco_subtree.position, length=eco_subtree.length,
                                              value=json.dumps(root_value, sort_keys=True), children=children)
        doc = gumtree_driver.GumtreeDocument(eco_tree)

        return doc

    def export_gumtree_as_string(self, tree_manager):
        doc = self.export_gumtree(tree_manager)
        js = doc.as_json()
        return json.dumps(js)

    def _export_subtree(self, node, lang, position):
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
                gumtree_child = self._export_subtree(child_node, lang, current_position)
                if gumtree_child is not None:
                    current_position += gumtree_child.length
                    children.append(gumtree_child)
            if self.compact:
                children = self._filter_child_list(children)
                if len(children) == 1:
                    return children[0]
                elif len(children) == 0:
                    return None

            type_label = self.type_name(lang, node.symbol.name)
            type_id = self.type_name_to_id[type_label]

            value = json.dumps(js_value, sort_keys=True)
            return gumtree_driver.GumtreeNode(type_id=type_id, type_label=type_label, position=position,
                                              length=current_position - position, value=value, children=children)
        elif isinstance(node.symbol, MagicTerminal):
            sub_lang = node.symbol.name[1:-1]
            root = self._export_subtree(node.symbol.ast, sub_lang, 0)
            type_label = '__magic_terminal__'
            type_id = self.type_name_to_id[type_label]

            js_value['language'] = sub_lang
            value = json.dumps(js_value, sort_keys=True)
            return gumtree_driver.GumtreeNode(type_id=type_id, type_label=type_label, position=node.position, length=1,
                                              value=value, children=[root])
        elif isinstance(node.symbol, (Terminal, FinishSymbol)):
            type_label = '__terminal__'
            type_id = self.type_name_to_id[type_label]

            value = json.dumps(js_value, sort_keys=True)
            return gumtree_driver.GumtreeNode(type_id=type_id, type_label=type_label, position=node.position, length=1,
                                              value=value, children=[])
        else:
            return None

    @staticmethod
    def type_name(lang, symbol_name):
        return '{0}::{1}'.format(lang, symbol_name)

    @staticmethod
    def _filter_child_list(children):
        return [c for c in children if c is not None]



class _GumtreeImporter (object):
    def __init__(self):
        self.__last_terminal = None
        self.language_boxes = []
        self.__whitespaces = True

    def _import_tree(self, root_gt):
        if root_gt.type_label != '__ROOT__':
            raise TypeError('Root node should have type label __ROOT__')
        root_value = json.loads(root_gt.value)
        root_lang = root_value['language']
        root_ws = root_value['whitespaces']

        root_node = self._import_subtree(root_gt[0])

        self.language_boxes.append((root_node, root_lang, root_ws))
        self.language_boxes.reverse()

        for lb in self.language_boxes:
            lb_root = lb[0]
            lb_root.mark_changed()
            lb_root.changed = False

        return root_node


    def _import_subtree(self, gt_node, unescape=False):
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
            lbox_root = self._import_subtree(gt_node[0])
            lbox_root.magic_backpointer = node
            node.symbol.ast = lbox_root
            node.symbol.parser = lbox_root
            self.__last_terminal = temp
            self.language_boxes.append((lbox_root, jsnode["language"], self.__whitespaces))
        else:
            last_child = None
            for c in gt_node:
                cnode = self._import_subtree(c)
                cnode.parent = node
                cnode.left = last_child
                if last_child:
                    last_child.right = cnode
                children.append(cnode)
                last_child = cnode
        node.children = children

        return node




def import_gumtree(doc):
    importer = _GumtreeImporter()

    root_node = importer._import_tree(doc.root)

    return root_node, importer.language_boxes

