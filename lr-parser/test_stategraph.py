import sys
sys.path.append("../")

from gparser import Parser, Terminal, Nonterminal
from state import StateSet, State
from production import Production
from stategraph import StateGraph

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

a = Terminal("\"a\"")
b = Terminal("\"b\"")
c = Terminal("\"c\"")
Z = Nonterminal("Z")
S = Nonterminal("S")
A = Nonterminal("A")

None_S  = State(Production(None, [S]), 0)
S_Sb    = State(Production(S, [S, b]), 0)
S_bAa   = State(Production(S, [b, A, a]), 0)
A_aSc   = State(Production(A, [a, S, c]), 0)
A_a     = State(Production(A, [a]), 0)
A_aSb   = State(Production(A, [a, S, b]), 0)

graph = StateGraph(p.start_symbol, p.rules)
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
    assert graph.follow(0, S) == graph.state_sets[1]
    assert graph.follow(0, b) == graph.state_sets[2]

    assert graph.follow(1, b) == graph.state_sets[3]

    assert graph.follow(2, A) == graph.state_sets[4]
    assert graph.follow(2, a) == graph.state_sets[5]

    assert graph.follow(3, S) == None
    assert graph.follow(3, a) == None
    assert graph.follow(3, b) == None
    assert graph.follow(3, c) == None

    assert graph.follow(4, a) == graph.state_sets[6]

    assert graph.follow(5, b) == graph.state_sets[2]
    assert graph.follow(5, S) == graph.state_sets[7]

    assert graph.follow(6, S) == None

    assert graph.follow(7, c) == graph.state_sets[9]
    assert graph.follow(7, b) == graph.state_sets[8]
