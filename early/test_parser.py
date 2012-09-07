from gparser import Parser, Nonterminal, Terminal

def test_simple():
    p = Parser("E ::= \"a\"")
    p.parse()
    assert p.rules[0].symbol == Nonterminal("E")
    assert p.rules[0].alternatives == [[Terminal("\"a\"")]]

