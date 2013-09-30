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
def test_option_rule():
    p = Parser("""
        A ::= "a" [ "b" ] "g"
    """)
    p.parse()
    print(p.rules)
    assert p.rules[Nonterminal("A")].alternatives == [[Terminal("a"), Nonterminal("A_option")]]
    assert p.rules[Nonterminal("A_option")].alternatives == [[Terminal("b"), Terminal("g")],
                                                            [Terminal("g")]]
def test_group_rule():
    p = Parser("""
        A ::= "a" ( "b" | "c" ) "g"
    """)
    p.parse()
    print(p.rules)
    assert p.rules[Nonterminal("A")].alternatives == [[Terminal("a"), Nonterminal("A_group1")]]
    assert p.rules[Nonterminal("A_group1")].alternatives == [[Terminal("b"), Nonterminal("A_group2")],
                                                             [Terminal("c"), Nonterminal("A_group2")]]
    assert p.rules[Nonterminal("A_group2")].alternatives == [[Terminal("g")]]
