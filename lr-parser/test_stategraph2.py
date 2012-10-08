import sys
sys.path.append("../")

from gparser import Parser, Terminal, Nonterminal, Epsilon
from state import StateSet, State
from production import Production
from stategraph import StateGraph

grammar = """
    S ::= "b" A "d"
    A ::= "c"
        |
"""

p = Parser(grammar)
p.parse()
r = p.rules

b = Terminal("\"b\"")
c = Terminal("\"c\"")
d = Terminal("\"d\"")
S = Nonterminal("S")
A = Nonterminal("A")

None_S = Production(None, [S])
S_bAd = Production(S, [b, A, d])
A_c = Production(A, [c])
A_None = Production(A, [Epsilon()])

graph = StateGraph(p.start_symbol, p.rules)
graph.build()

def test_state_0():
    # State 0
    # Z ::= .S
    # S ::= .bAd
    s = StateSet()
    s.add(State(None_S, 0))
    s.add(State(S_bAd, 0))
    assert graph.state_sets[0] == s

def test_state_1():
    # State 1
    # Z ::= S.
    s = StateSet()
    s.add(State(None_S, 1))
    assert graph.state_sets[1] == s

def test_state_2():
    # State 2
    # S ::= b.Ad
    # A ::= .c
    # A ::= .
    s = StateSet()
    s.add(State(S_bAd, 1))
    s.add(State(A_c, 0))
    s.add(State(A_None, 1))
    assert graph.state_sets[2] == s

def test_state_4():
    # State 4
    # S ::= bA.d
    s = StateSet()
    s.add(State(S_bAd, 2))
    assert s in graph.state_sets

def test_state_6():
    # State 6
    # S ::= bAd.
    s = StateSet()
    s.add(State(S_bAd, 3))
    assert s in graph.state_sets

def test_state_5():
    # State 5
    # A ::= c.
    s = StateSet()
    s.add(State(A_c, 1))
    assert s in graph.state_sets

def test_edges():
    assert graph.follow(0, S) == 1
    assert graph.follow(0, b) == 2

    assert graph.follow(2, A) == 3
    assert graph.follow(2, c) == 4

    assert graph.follow(3, d) == 5

def test_get_symbols():
    assert graph.get_symbols() == set([b, c, d, S, A])
