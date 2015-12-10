import json
from grammar_parser.gparser import Nonterminal, Terminal
from version_control import gumtree_driver

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
        return gumtree_driver.GumtreeNode(type_id=type_id, type_label=symbol.name, position=position,
                                          length=current_position - position, value='', children=children)
    elif isinstance(symbol, Terminal):
        type_label = '__terminal__'
        type_id = symbol_name_to_id[type_label]
        return gumtree_driver.GumtreeNode(type_id=type_id, type_label=type_label, position=node.position, length=1,
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
    doc = gumtree_driver.GumtreeDocument(eco_subtree)

    js = doc.as_json()

    return json.dumps(js)