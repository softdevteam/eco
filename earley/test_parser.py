from gparser import Parser, Nonterminal, Terminal

def test_simple():
    p = Parser("E ::= \"a\"")
    p.parse()
    assert p.rules[0].symbol == Nonterminal("E")
    assert p.rules[0].alternatives == [[Terminal("\"a\"")]]

def test_multiple_symbols():
    p = Parser("E ::= A \"a\"")
    p.parse()
    assert p.rules[0].alternatives == [[Nonterminal("A"), Terminal("\"a\"")]]

def test_alternatives():
    p = Parser("E ::= A | \"a\"")
    p.parse()
    assert p.rules[0].alternatives == [[Nonterminal("A")], [Terminal("\"a\"")]]

def test_multiple_rules():
    p = Parser("""
        E ::= A
        A ::= \"a\"
    """)
    p.parse()
    assert p.rules[0].alternatives == [[Nonterminal("A")]]
    assert p.rules[1].alternatives == [[Terminal("\"a\"")]]

def test_more_complex_grammar():
    p = Parser("""
    name ::= "ID"
           | "&" "ID"
           | splice
           | insert
    """)
    p.parse()
    assert p.rules[0].alternatives == [
        [Terminal("\"ID\"")],
        [Terminal("\"&\""), Terminal("\"ID\"")],
        [Nonterminal("splice")],
        [Nonterminal("insert")]
    ]
