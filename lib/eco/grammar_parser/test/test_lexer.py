# Copyright (c) 2012--2013 King's College London
# Created by the Software Development Team <http://soft-dev.org/>
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to
# deal in the Software without restriction, including without limitation the
# rights to use, copy, modify, merge, publish, distribute, sublicense, and/or
# sell copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
# FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS
# IN THE SOFTWARE.

from grammar_parser.lexer import Lexer

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

def test_ebnf_rules():
    l = Lexer("""
    A ::= "a" ("b" | "c")
        | "b" {"c"}
        | "c" ["d"]
    """)
    l.lex()

    assert l.tokens[0].name == "Nonterminal"
    assert l.tokens[1].name == "Mapsto"
    assert l.tokens[2].name == "Terminal"
    assert l.tokens[3].name == "Group_Start"
    assert l.tokens[4].name == "Terminal"
    assert l.tokens[5].name == "Alternative"
    assert l.tokens[6].name == "Terminal"
    assert l.tokens[7].name == "Group_End"
    assert l.tokens[8].name == "Alternative"
    assert l.tokens[9].name == "Terminal"
    assert l.tokens[10].name == "Loop_Start"
    assert l.tokens[11].name == "Terminal"
    assert l.tokens[12].name == "Loop_End"
    assert l.tokens[13].name == "Alternative"
    assert l.tokens[14].name == "Terminal"
    assert l.tokens[15].name == "Option_Start"
    assert l.tokens[16].name == "Terminal"
    assert l.tokens[17].name == "Option_End"
