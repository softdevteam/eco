from lexer import Lexer

def test_rule_easy():
    l = Lexer("E ::= \"a\"")
    l.lex()
    assert l.tokens[0].name == "Nonterminal"
    assert l.tokens[0].value == "E"
    assert l.tokens[1].name == "Mapsto"
    assert l.tokens[2].name == "Terminal"
    assert l.tokens[2].value == "\"a\""

def test_multiple_symbols():
    l = Lexer("E ::= E \"+\" \"a\"")
    l.lex()
    assert l.tokens[2].name == "Nonterminal"
    assert l.tokens[3].name == "Terminal"
    assert l.tokens[4].name == "Terminal"

def test_alternatives():
    l = Lexer("E ::= E | T")
    l.lex()
    assert l.tokens[3].name == "Alternative"

def test_whitespaces():
    l = Lexer("""
    E ::= E
        | T
    """)
    l.lex()
    assert l.tokens[0].name == "Nonterminal"
    assert l.tokens[1].name == "Mapsto"
    assert l.tokens[2].name == "Nonterminal"
    assert l.tokens[3].name == "Alternative"
    assert l.tokens[4].name == "Nonterminal"

def test_multiple_rules():
    l = Lexer("""
    E ::= T
    T ::= \"a\"
    """)
    l.lex()
    assert l.tokens[0].name == "Nonterminal"
    assert l.tokens[1].name == "Mapsto"
    assert l.tokens[2].name == "Nonterminal"
    assert l.tokens[3].name == "Nonterminal"
    assert l.tokens[4].name == "Mapsto"
    assert l.tokens[5].name == "Terminal"

def test_grammar():
    l = Lexer("""
    name ::= "ID"
           | "&" "ID"
           | splice
           | insert
    """)
    l.lex()

    assert l.tokens[0].name == "Nonterminal"
    assert l.tokens[1].name == "Mapsto"
    assert l.tokens[2].name == "Terminal"
    assert l.tokens[3].name == "Alternative"
    assert l.tokens[4].name == "Terminal"
    assert l.tokens[5].name == "Terminal"
    assert l.tokens[6].name == "Alternative"
    assert l.tokens[7].name == "Nonterminal"
    assert l.tokens[8].name == "Alternative"
    assert l.tokens[9].name == "Nonterminal"
