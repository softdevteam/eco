from lrparser import LRParser

grammar = """
    S ::= "a" B "d"
    B ::= "b"
        | C
    C ::= "c"
"""

def test_input():
    lrp = LRParser(grammar)
    assert lrp.check("a b d") == True
    assert lrp.check("a c d") == True
    assert lrp.check("a a d") == False

def test_input2():
    lrp = LRParser(grammar, 1)
    assert lrp.check("a b d") == True
    assert lrp.check("a c d") == True
    assert lrp.check("a a d") == False

def test_input3():
    grammar = """
        E ::= T
            | E "+" T
        T ::= P
            | T "*" P
        P ::= "1" | "2" | "3" | "4" | "5" | "6" | "7" | "8" | "9"
    """
    lrp = LRParser(grammar, 1)
    assert lrp.check("1 + 2") == True
    assert lrp.check("1 + 2 * 3") == True
    assert lrp.check("1 * 2 * 3 + 4") == True

def test_epsilon():
    grammar = """
        S ::= "b" A "d"
        A ::= "c"
            |
    """
    lrp = LRParser(grammar, 1)
    assert lrp.check("b c d") == True
    print("---")
    assert lrp.check("b d") == True
