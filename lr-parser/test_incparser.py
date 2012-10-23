from incparser import IncParser
from constants import LR0, LR1, LALR
from gparser import Terminal, Nonterminal
from astree import Node

grammar = """
    E ::= E "+" T
        | T
    T ::= T "*" P
        | P
    P ::= "1" | "2"
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
    a = Terminal("\"a\"")
    b = Terminal("\"b\"")
    changed_node = C.children[0]
    changed_node.symbol.name = "b b a"
    lrp.all_changes.append(changed_node)
    while(changed_node.parent):
        changed_node = changed_node.parent
        lrp.all_changes.append(changed_node)
    lrp.previous_version.pprint()
    lrp.inc_parse()
    lrp.stack[1].pprint()
    assert False
