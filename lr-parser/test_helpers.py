import sys
sys.path.append("../")

from gparser import Parser, Terminal, Nonterminal
from state import State, StateSet
from production import Production
from helpers import first, follow, closure_0, goto_0

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

a = Terminal("\"a\"")
b = Terminal("\"b\"")
c = Terminal("\"c\"")
d = Terminal("\"d\"")
f = Terminal("\"f\"")
Z = Nonterminal("Z")
S = Nonterminal("S")
A = Nonterminal("A")
B = Nonterminal("B")
C = Nonterminal("C")
D = Nonterminal("D")
F = Nonterminal("F")

def test_first():
    assert first(r, a) == set([a])
    assert first(r, b) == set([b])
    assert first(r, c) == set([c])
    assert first(r, S) == set([a, b])
    assert first(r, A) == set([a])
    assert first(r, B) == first(r, A)
    assert first(r, C) == set([d, a])
    assert first(r, D) == set([d, None])

def test_follow():
    assert follow(r, S) == set([b, c])
    assert follow(r, A) == set([a]).union(first(r, S))
    assert follow(r, B) == set([])
    assert follow(r, C) == set([d, f])
    assert follow(r, D) == set([a, f])

def test_closure_0():
    s1 = StateSet()
    s =  State(Production(Nonterminal("Z"), [Nonterminal("S")]), 0) # first state Z ::= .S
    s1.add(s)
    closure = closure_0(r, s1)
    assert len(closure.elements) == 4
    assert State(Production(Nonterminal("Z"), [Nonterminal("S")]), 0) in closure
    assert State(Production(Nonterminal("S"), [Nonterminal("S"), Terminal("\"b\"")]), 0) in closure
    assert State(Production(Nonterminal("S"), [Terminal("\"b\""), Nonterminal("A"), Terminal("\"a\"")]), 0) in closure
    assert State(Production(Nonterminal("S"), [Terminal("\"a\"")]), 0) in closure

    s2 = StateSet()
    s =  State(Production(F, [C, D, f]), 0)
    s2.add(s)
    closure = closure_0(r, s2)
    assert len(closure.elements) == 4
    assert State(Production(F, [C, D, f]), 0) in closure
    assert State(Production(C, [D, A]), 0) in closure
    assert State(Production(D, [d]), 0) in closure
    assert State(Production(D, []), 0) in closure

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
    ss = StateSet([State(Production(Nonterminal("Z"), [Nonterminal("S")]), 0)])
    closure = closure_0(r, ss)
    g1 = goto_0(r, closure, b)
    expected = closure_0(r, StateSet([State(Production(S, [b, A, a]), 1)]))
    assert expected.elements == g1.elements
    g2 = goto_0(r, closure, a)
    assert [State(Production(S, [a]), 1)] == g2.elements
