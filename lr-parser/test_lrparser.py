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

def test_calc1():
    grammar = """
        E ::= P
            | E "+" P
        P ::= "1" | "2"
    """
    lrp = LRParser(grammar, 0)
    assert lrp.check("1") == True
    assert lrp.check("1 + 2") == True
    print("NOW WITH LR(1)")
    lrp = LRParser(grammar, 1)
    assert lrp.check("1 + 2") == True

def test_calc2():
    grammar = """
        E ::= T
            | E "+" T
        T ::= P
            | T "*" P
        P ::= "1" | "2" | "3" | "4" | "5" | "6" | "7" | "8" | "9"
    """
    lrp = LRParser(grammar, 0)
    assert lrp.check("1 + 2") == True
    assert lrp.check("1 + 2 * 3") == True
    assert lrp.check("1 * 2 * 3 + 4") == True

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
    assert lrp.check("b d") == True

def test_epsilon2():
    grammar = """
        S ::= A B "c"
        A ::= "a"
        B ::= "b"
            |
    """
    lrp = LRParser(grammar, 1)
    assert lrp.check("a b c") == True
    assert lrp.check("a c") == True
    assert lrp.check("a b b") == False

def test_recursion():
    grammar = """
        S ::= "b" S
            |
    """
    lrp = LRParser(grammar, 1)
    assert lrp.check("b b b b b b b b b b b") == True
    assert lrp.check("b b") == True
    assert lrp.check("b") == True
    assert lrp.check("") == False

def test_recursion2():
    grammar = """
        S ::= "b" A
        A ::= S
            |
    """
    lrp = LRParser(grammar, 1)
    assert lrp.check("b b b b b b b b b b b") == True
    assert lrp.check("b b") == True
    assert lrp.check("b") == True
    assert lrp.check("") == False
