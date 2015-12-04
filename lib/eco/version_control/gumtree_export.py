import json
from grammar_parser.gparser import Nonterminal, Terminal

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



class EcoTreeNode (object):
    def __init__(self, type_id, type_label, position, length, value, children):
        if value is None:
            value = ''
        if not isinstance(type_id, int):
            raise TypeError('type_id must be an int')
        if not isinstance(type_label, str):
            raise TypeError('type_label must be a str')
        if not isinstance(position, int):
            raise TypeError('position must be an int')
        if not isinstance(length, int):
            raise TypeError('length must be an int')
        if not isinstance(value, str):
            raise TypeError('value must be None or a str')
        for child in children:
            if not isinstance(child, EcoTreeNode):
                raise TypeError('children must be a sequence of EcoTreeNode instances')
        self.type_id = type_id
        self.type_label = type_label
        self.position = position
        self.length = length
        self.value = value
        self.children = children

    def as_json(self):
        return {
            '__type__': 'TreeNode',
            'label': self.value,
            'type': self.type_id,
            'type_label': self.type_label,
            'pos': self.position,
            'length': self.length,
            'children': [child.as_json() for child in self.children],
        }


class EcoTreeDocument (object):
    def __init__(self, root):
        self.root = root
        
        
    def as_json(self):
        return {
            '__type__': 'EcoTree',
            'tree': self.root.as_json()
        }

    def as_str(self):
        return json.dumps(self.as_json())


def _export_subtree(node, symbol_name_to_id, position):
    symbol = node.symbol
    if isinstance(symbol, Nonterminal):
        children = []
        current_position = position
        for child_node in node.children:
            eco_child = _export_subtree(child_node, symbol_name_to_id, current_position)
            if eco_child is not None:
                current_position += eco_child.length
                children.append(eco_child)
        type_id = symbol_name_to_id[symbol.name]
        return EcoTreeNode(type_id=type_id, type_label=symbol.name, position=position,
                           length=current_position - position, value='', children=children)
    elif isinstance(symbol, Terminal):
        type_label = '__terminal__'
        type_id = symbol_name_to_id[type_label]
        return EcoTreeNode(type_id=type_id, type_label=type_label, position=node.position, length=1,
                           value=symbol.name, children=[])
    else:
        return None



def export_ecotree(root_node, syntaxtable):
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
    symbol_name_to_id['Root'] = len(symbol_name_to_id)

    eco_subtree = _export_subtree(root_node, symbol_name_to_id, 0)
    doc = EcoTreeDocument(eco_subtree)

    js = doc.as_json()

    return json.dumps(js)