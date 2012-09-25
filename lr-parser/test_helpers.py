import sys
sys.path.append("../")

from gparser import Parser, Terminal, Nonterminal
from helpers import first, follow, goto

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
