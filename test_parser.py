import sys
sys.path.append("../")
from gparser import Parser, Nonterminal, Terminal, Epsilon


def test_terminal():
    t1 = Nonterminal("E")
    t2 = Nonterminal("E")
    assert t1 == t2

    t1 = Terminal("a")
    t2 = Terminal("a")
    assert t1 == t2

def test_simple():
    p = Parser("E ::= \"a\"")
    p.parse()
    assert p.rules[Nonterminal("E")].symbol == Nonterminal("E")
    assert p.rules[Nonterminal("E")].alternatives == [[Terminal("a")]]

def test_multiple_symbols():
    p = Parser("E ::= A \"a\"")
    p.parse()
    assert p.rules[Nonterminal("E")].alternatives == [[Nonterminal("A"), Terminal("a")]]

def test_alternatives():
    p = Parser("E ::= A | \"a\"")
    p.parse()
    assert p.rules[Nonterminal("E")].alternatives == [[Nonterminal("A")], [Terminal("a")]]

def test_multiple_rules():
    p = Parser("""
        E ::= A
        A ::= \"a\"
    """)
    p.parse()
    assert p.rules[Nonterminal("E")].alternatives == [[Nonterminal("A")]]
    assert p.rules[Nonterminal("A")].alternatives == [[Terminal("a")]]

def test_more_complex_grammar():
    p = Parser("""
    name ::= "ID"
           | "&" "ID"
           | splice
           | insert
    """)
    p.parse()
    assert p.rules[Nonterminal("name")].alternatives == [
        [Terminal("ID")],
        [Terminal("&"), Terminal("ID")],
        [Nonterminal("splice")],
        [Nonterminal("insert")]
    ]

def test_empty_alternative():
    p = Parser("""
        E ::= "a"
            |
    """)
    p.parse()
    assert p.rules[Nonterminal("E")].alternatives == [[Terminal("a")],[]]

def test_loop_rule():
    p = Parser("""
        A ::= "a" { "b" } "g"
    """)
    p.parse()
    print(p.rules)
    assert p.rules[Nonterminal("A")].alternatives == [[Terminal("a"), Nonterminal("A_loop")]]
    assert p.rules[Nonterminal("A_loop")].alternatives == [[Terminal("b"), Nonterminal("A_loop")],
                                                            [Terminal("g")]]

def test_loop_nested():
    p = Parser("""
        A ::= "a" { "b" {"c"} } "g"
    """)
    p.parse()
    print(p.rules)
    assert p.rules[Nonterminal("A")].alternatives == [[Terminal("a"), Nonterminal("A_loop")]]
    assert p.rules[Nonterminal("A_loop")].alternatives == [[Terminal("b"), Nonterminal("A_loop_loop")],
                                                            [Terminal("g")]]
    assert p.rules[Nonterminal("A_loop_loop")].alternatives == [[Terminal("c"), Nonterminal("A_loop_loop")],
                                                                [Nonterminal("A_loop")]]

def test_loop_multiple():
    p = Parser("""
        A ::= "a" { "b" } {"g"}
    """)
    p.parse()
    print(p.rules)
    assert p.rules[Nonterminal("A")].alternatives == [[Terminal("a"), Nonterminal("A_loop")]]
    assert p.rules[Nonterminal("A_loop")].alternatives == [[Terminal("b"), Nonterminal("A_loop")],
                                                            [Nonterminal("A_loop_loop")]]
    assert p.rules[Nonterminal("A_loop_loop")].alternatives == [[Terminal("g"), Nonterminal("A_loop_loop")],
                                                            []]
