from incparser import IncParser
from constants import LR0, LR1, LALR

grammar = """
    E ::= E "+" T
        | T
    T ::= T "*" P
        | P
    P ::= "1" | "2"
"""

def test_input():
    lrp = IncParser(grammar, LR1)
    assert lrp.inc_parse("1 + 2") == True
    assert lrp.inc_parse("1 + 2") == True

