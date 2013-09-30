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

from grammar_parser.gparser import Parser, Terminal, Nonterminal
from incparser.state import StateSet, State
from incparser.production import Production
from incparser.stategraph import StateGraph

import pytest

grammar = """
    S ::= S "b"
        | "b" A "a"
    A ::= "a" S "c"
        | "a"
        | "a" S "b"
"""

p = Parser(grammar)
p.parse()
r = p.rules

a = Terminal("a")
b = Terminal("b")
c = Terminal("c")
Z = Nonterminal("Z")
S = Nonterminal("S")
A = Nonterminal("A")

None_S  = State(Production(None, [S]), 0)
S_Sb    = State(Production(S, [S, b]), 0)
S_bAa   = State(Production(S, [b, A, a]), 0)
A_aSc   = State(Production(A, [a, S, c]), 0)
A_a     = State(Production(A, [a]), 0)
A_aSb   = State(Production(A, [a, S, b]), 0)

graph = StateGraph(p.start_symbol, p.rules, 1)
graph.build()

def move_dot(state, i):
    temp = state.clone()
    temp.d += i
    return temp

def test_state_0():
    # State 0
    # Z ::= .S
    # S ::= .Sb
    # S ::= .bAa
    s = StateSet()
    s.add(None_S)
    s.add(S_Sb)
    s.add(S_bAa)

    assert graph.state_sets[0] == s

def test_state_1():
    # State 1
    # Z ::= S.
    # S ::= S.b
    s = StateSet()
    s.add(move_dot(None_S, 1))
    s.add(move_dot(S_Sb, 1))

    assert graph.state_sets[1] == s

def test_state_2():
    # State 2
    # S ::= b.Aa
    # A ::= .aSc
    # A ::= .a
    # A ::= .aSb
    s = StateSet()
    s.add(move_dot(S_bAa, 1))
    s.add(A_aSc)
    s.add(A_a)
    s.add(A_aSb)

    assert graph.state_sets[2] == s

def test_edges():
    pytest.skip("Graph building algorithm changed")
    assert graph.follow(0, S) == 1
    assert graph.follow(0, b) == 2

    assert graph.follow(1, b) == 3

    assert graph.follow(2, A) == 4
    assert graph.follow(2, a) == 5

    assert graph.follow(3, S) == None
    assert graph.follow(3, a) == None
    assert graph.follow(3, b) == None
    assert graph.follow(3, c) == None

    assert graph.follow(4, a) == 6

    assert graph.follow(5, b) == 2
    assert graph.follow(5, S) == 7

    assert graph.follow(6, S) == None

    assert graph.follow(7, c) == 9
    assert graph.follow(7, b) == 8

def test_get_symbols():
    assert graph.get_symbols() == set([a, b, c, S, A])
