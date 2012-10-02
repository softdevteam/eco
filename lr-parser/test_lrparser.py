from lrparser import LRParser

grammar = """
    S ::= "a" B "d"
    B ::= "b"
        | C
    C ::= "c"
"""

def test_input():
    lrp = LRParser(grammar)
    assert lrp.check("abd") == True
    assert lrp.check("acd") == True
    assert lrp.check("aad") == False
