from incparser import IncParser
from constants import LR0, LR1, LALR
from gparser import Terminal, Nonterminal

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

