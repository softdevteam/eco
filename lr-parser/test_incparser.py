from incparser import IncParser
from constants import LR0, LR1, LALR
from gparser import Terminal, Nonterminal
from astree import Node
from viewer import Viewer

grammar = """
    E ::= E "+" T
        | T
    T ::= T "*" P
        | P
    P ::= "1" | "2" | "3" | "4"
"""

def test_input():
    lrp = IncParser(grammar, LR1)
    assert lrp.inc_parse("1 * 2") == True
    lrp.get_ast().pprint()
    parse_root = lrp.ast_stack[0]
    assert lrp.inc_parse("1 + 2") == True
    lrp.stack[1].pprint()
    assert parse_root is lrp.ast_stack[0]
    assert False

def test_empty_start():
    grammar = """
        S ::= "a"
            |
    """
    lrp = IncParser(grammar, LR1)
    assert lrp.inc_parse("") == True
    lrp.get_ast().pprint()
    assert lrp.inc_parse("a") == True
    lrp.stack[1].pprint()
    assert False

def test_multiple_changes_at_once():
    grammar = """
        S ::= C S
            | C
        C ::= "a" | "b"
    """
    lrp = IncParser(grammar, LR1)
    lrp.check("a a a")
    lrp.previous_version = lrp.get_ast()
    ast = lrp.previous_version
    #root
    #    bos
    #    S
    #        C a
    #        S
    #            C a
    #            ...
    C = ast.parent.children[1].children[1].children[0]
    assert C.symbol == Nonterminal("C")
    assert C.children[0].symbol == Terminal("\"a\"")
    # put insertion into this Node
    changed_node = C.children[0]
    changed_node.symbol.name = "b b a"
    apply_change(lrp, changed_node)
    lrp.previous_version.pprint()
    lrp.inc_parse()
    lrp.stack[1].pprint()
    assert False

def test_deletion():
    grammar = """
        S ::= C S
            | C
        C ::= "a" | "b"
    """
    lrp = IncParser(grammar, LR1)
    lrp.check("a a a")
    lrp.previous_version = lrp.get_ast()
    ast = lrp.previous_version
    Viewer().show_tree(lrp.previous_version.parent)

    C = ast.parent.children[1].children[1].children[0]
    assert C.symbol == Nonterminal("C")
    assert C.children[0].symbol == Terminal("\"a\"")
    # delete terminal node
    C.children.pop(0)
    apply_change(lrp, C)
    lrp.inc_parse()
    Viewer().show_tree(lrp.stack[1])
    assert False

def apply_change(lrp, node):
    lrp.all_changes.append(node)
    while(node.parent):
        node = node.parent
        lrp.all_changes.append(node)

def test_multiple_changes_2():
    lrp = IncParser(grammar, LR1)
    lrp.check("1 + 2")
    lrp.previous_version = lrp.get_ast()
    ast = lrp.previous_version
    Viewer().show_tree(lrp.previous_version.parent.children[1])
    i2 = ast.parent.children[1].children[2].children[0].children[0]
    assert i2.symbol == Terminal("\"2\"")
    i2.symbol.name = "3 * 4"
    apply_change(lrp, i2)
    lrp.inc_parse()
    lrp.stack[1].pprint()
    Viewer().show_tree(lrp.stack[1])
    assert False

def test_multiple_changes_3():
    lrp = IncParser(grammar, LR1)
    lrp.check("1 + 2")
    lrp.previous_version = lrp.get_ast()
    ast = lrp.previous_version
    Viewer().show_tree(lrp.previous_version.parent.children[1])
    i2 = ast.parent.children[1].children[1]
    assert i2.symbol == Terminal("\"+\"")
    i2.symbol.name = "*"
    apply_change(lrp, i2)
    lrp.inc_parse()
    lrp.stack[1].pprint()
    Viewer().show_tree(lrp.stack[1])
    assert False
