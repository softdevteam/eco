from simplelexer import Lexer


def test_identifier():
    l = Lexer("E")
    l.lex()
    assert len(l.tokens) == 1
    assert l.tokens[0].name == "Identifier"
    assert l.tokens[0].value == "E"

def test_assignment():
    l = Lexer("E :=")
    l.lex()
    assert len(l.tokens) == 2
    assert l.tokens[1].name == "Assignment"
    assert l.tokens[1].value == ":="

def test_assignment2():
    l = Lexer("E := E")
    l.lex()
    assert len(l.tokens) == 3
    assert l.tokens[2].name == "Identifier"
    assert l.tokens[2].value == "E"

def test_expression():
    l = Lexer("E := E + E")
    l.lex()
    assert len(l.tokens) == 5
    assert l.tokens[3].name == "Operation"
    assert l.tokens[3].value == "+"

def test_newrule():
    l = Lexer("E := E + E; E := ")
    l.lex()
    assert len(l.tokens) == 8
    assert l.tokens[5].name == "Newrule"
    assert l.tokens[5].value == ";"

def test_newrule():
    l = Lexer("E := E + E; E := INT")
    l.lex()
    assert len(l.tokens) == 9
    assert l.tokens[8].name == "Integer"
    assert l.tokens[8].value == "INT"
