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

from gparser import Parser, Terminal, Nonterminal, Epsilon
from syntaxtable import FinishSymbol
from state import State, StateSet, LR1Element
from production import Production
from helpers import follow, closure_0, goto_0, closure_1, Helper

grammar = """
Z ::= S
S ::= S "b"
    | "b" A "a"
    | "a"
A ::= "a" S "c"
    | "a"
    | "a" S "b"

B ::= A S

C ::= D A

D ::= "d"
    |

F ::= C D "f"
"""

p = Parser(grammar)
p.parse()
r = p.rules

grammar2 = """
    E ::= P
        | E "+" P
    P ::= "a"
"""

p = Parser(grammar2)
p.parse()
r2 = p.rules


a = Terminal("a")
b = Terminal("b")
c = Terminal("c")
d = Terminal("d")
f = Terminal("f")
plus = Terminal("+")
mul = Terminal("*")
epsilon = Epsilon()
finish = FinishSymbol()

Z = Nonterminal("Z")
S = Nonterminal("S")
A = Nonterminal("A")
B = Nonterminal("B")
C = Nonterminal("C")
D = Nonterminal("D")
E = Nonterminal("E")
F = Nonterminal("F")
G = Nonterminal("G")
P = Nonterminal("P")
T = Nonterminal("T")

helper1 = Helper(r)
first = helper1.first
follow = helper1.follow

def test_first():
    assert first(a) == set([a])
    assert first(b) == set([b])
    assert first(c) == set([c])
    assert first(S) == set([a, b])
    assert first(A) == set([a])
    assert first(B) == first(A)
    assert first(D) == set([d, epsilon])
    assert first(C) == set([d, a])
    assert first(F) == set([d, a])
    assert first([D, A]) == set([d, a])
    assert first([C, D, f]) == set([d, a])

    assert first([finish]) == set([finish])

def test_follow():
    assert follow(S) == set([b, c])
    assert follow(A) == set([a, b, d, f])
    assert follow(B) == set([])
    assert follow(C) == set([d, f])
    assert follow(D) == set([a, f])

def test_closure_0():
    s1 = StateSet()
    s =  State(Production(Nonterminal("Z"), [Nonterminal("S")]), 0) # first state Z ::= .S
    s1.add(s)
    closure = closure_0(r, s1)
    assert len(closure.elements) == 4
    assert State(Production(Z, [S]), 0) in closure
    assert State(Production(S, [S, b]), 0) in closure
    assert State(Production(S, [b, A, a]), 0) in closure
    assert State(Production(S, [a]), 0) in closure

    s2 = StateSet()
    s =  State(Production(F, [C, D, f]), 0)
    s2.add(s)
    closure = closure_0(r, s2)
    assert len(closure.elements) == 4
    assert State(Production(F, [C, D, f]), 0) in closure
    assert State(Production(C, [D, A]), 0) in closure
    assert State(Production(D, [d]), 0) in closure
    assert State(Production(D, [Epsilon()]), 1) in closure

    s3 = StateSet()
    s =  State(Production(C, [D, A]), 1)
    s3.add(s)
    closure = closure_0(r, s3)
    assert len(closure.elements) == 4
    assert State(Production(C, [D, A]), 1) in closure
    assert State(Production(A, [a, S, c]), 0) in closure
    assert State(Production(A, [a, S, b]), 0) in closure
    assert State(Production(A, [a]), 0) in closure

def test_goto_0():
    ss = StateSet([State(Production(Z, [S]), 0)])
    closure = closure_0(r, ss)
    g1 = goto_0(r, closure, b)
    expected = closure_0(r, StateSet([State(Production(S, [b, A, a]), 1)]))
    assert expected.elements == g1.elements
    g2 = goto_0(r, closure, a)
    assert [State(Production(S, [a]), 1)] == g2.elements

    assert goto_0(r, closure, c) == StateSet()
    assert goto_0(r, closure, d) == StateSet()
    assert goto_0(r, closure, f) == StateSet()

def test_closure_1():
    s1 = StateSet([LR1Element(Production(Z, [S]), 0, set([finish]))])
    closure = helper1.closure_1(s1)
    assert len(closure.elements) == 4
    assert LR1Element(Production(Z, [S]), 0, set([finish])) in closure
    assert LR1Element(Production(S, [S, b]), 0, set([b, finish])) in closure
    assert LR1Element(Production(S, [b, A, a]), 0, set([b, finish])) in closure
    assert LR1Element(Production(S, [a]), 0, set([b, finish])) in closure

    s2 = StateSet([LR1Element(Production(F, [C, D, f]), 0, set([finish]))])
    closure = closure_1(r, s2)
    assert len(closure.elements) == 4
    assert LR1Element(Production(F, [C, D, f]), 0, set([finish])) in closure
    assert LR1Element(Production(C, [D, A]), 0, set([d, f])) in closure
    assert LR1Element(Production(D, [d]), 0, set([a])) in closure
    assert LR1Element(Production(D, [epsilon]), 1, set([a])) in closure

def test_goto_1():
    lre = LR1Element(Production(Z, [S]), 0, set([finish]))
    clone = lre.clone()

    assert lre == clone

def test_closure_recursion():
    s1 = StateSet([LR1Element(Production(Z, [E]), 0, set([finish]))])

    closure = closure_1(r2, s1)
    assert len(closure.elements) == 4
    assert LR1Element(Production(Z, [E]), 0, set([finish])) in closure
    assert LR1Element(Production(E, [P]), 0, set([plus, finish])) in closure
    assert LR1Element(Production(E, [E, plus, P]), 0, set([plus, finish])) in closure
    assert LR1Element(Production(P, [a]), 0, set([plus, finish])) in closure


grammar3 = """
    E ::= T
        | E "+" T
    T ::= P
        | T "*" P
    P ::= "a"
    C ::= C "c"
        |
    D ::= D "d"
        | F
    F ::= "f" |
    G ::= C D
"""

p = Parser(grammar3)
p.parse()
r3 = p.rules

def test_first_bug():
    first_calc = Helper(r3)
    first = first_calc.first
    assert first(E) == set([a])
    assert first(P) == set([a])
    assert first(T) == set([a])
    assert first([mul, T, plus]) == set([mul])
    assert first([plus, T, plus]) == set([plus])
    assert first([T, plus]) == set([a])
    assert first(C) == set([c, epsilon])
    assert first(D) == set([f, d, epsilon])
    assert first(G) == set([c, d, f, epsilon])
