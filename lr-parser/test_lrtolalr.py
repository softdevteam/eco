import sys
sys.path.append("../")

from gparser import Parser, Terminal, Nonterminal
from state import StateSet, State, LR1Element
from production import Production
from stategraph import StateGraph
from syntaxtable import FinishSymbol

grammar = """
    S ::= "b" A "c"
    A ::= S
        | "a"
"""

p = Parser(grammar)
p.parse()
r = p.rules

a = Terminal("\"a\"")
b = Terminal("\"b\"")
c = Terminal("\"c\"")
S = Nonterminal("S")
A = Nonterminal("A")
f = FinishSymbol()

def test_graph():
    graph = StateGraph(p.start_symbol, p.rules, 1)
    graph.build()

    s0 = StateSet([
        LR1Element(Production(None, [S]), 0, set([f])),
        LR1Element(Production(S, [b, A, c]), 0, set([f])),
    ])

    s1 = StateSet([
        LR1Element(Production(S, [b, A, c]), 1, set([f])),
        LR1Element(Production(A, [S]), 0, set([c])),
        LR1Element(Production(A, [a]), 0, set([c])),
        LR1Element(Production(S, [b, A, c]), 0, set([c])),
    ])

    s2 = StateSet([
        LR1Element(Production(S, [b, A, c]), 1, set([c])),
        LR1Element(Production(A, [S]), 0, set([c])),
        LR1Element(Production(A, [a]), 0, set([c])),
        LR1Element(Production(S, [b, A, c]), 0, set([c])),
    ])

    s3 = StateSet([
        LR1Element(Production(A, [a]), 1, set([c])),
    ])

    s4 = StateSet([
        LR1Element(Production(None, [S]), 1, set([f])),
    ])

    s5 = StateSet([
        LR1Element(Production(S, [b, A, c]), 2, set([f])),
    ])

    s6 = StateSet([
        LR1Element(Production(S, [b, A, c]), 2, set([c])),
    ])

    s7 = StateSet([
        LR1Element(Production(A, [S]), 1, set([c])),
    ])

    s8 = StateSet([
        LR1Element(Production(S, [b, A, c]), 3, set([f])),
    ])

    s9 = StateSet([
        LR1Element(Production(S, [b, A, c]), 3, set([c])),
    ])

    assert len(graph.state_sets) == 10
    assert s0 in graph.state_sets
    assert s1 in graph.state_sets
    assert s2 in graph.state_sets
    assert s3 in graph.state_sets
    assert s4 in graph.state_sets
    assert s6 in graph.state_sets
    assert s7 in graph.state_sets
    assert s8 in graph.state_sets
    assert s9 in graph.state_sets

    graph.convert_lalr()

    s0 = StateSet([
        LR1Element(Production(None, [S]), 0, set([f])),
        LR1Element(Production(S, [b, A, c]), 0, set([f])),
    ])

    s1 = StateSet([
        LR1Element(Production(S, [b, A, c]), 1, set([f, c])),
        LR1Element(Production(A, [S]), 0, set([c])),
        LR1Element(Production(A, [a]), 0, set([c])),
        LR1Element(Production(S, [b, A, c]), 0, set([c])),
    ])

    s2 = StateSet([
        LR1Element(Production(A, [a]), 1, set([c])),
    ])

    s3 = StateSet([
        LR1Element(Production(None, [S]), 1, set([f])),
    ])

    s4 = StateSet([
        LR1Element(Production(S, [b, A, c]), 2, set([f, c])),
    ])

    s5 = StateSet([
        LR1Element(Production(A, [S]), 1, set([c])),
    ])

    s6 = StateSet([
        LR1Element(Production(S, [b, A, c]), 3, set([f, c])),
    ])

    assert len(graph.state_sets) == 7
    assert s0 in graph.state_sets
    assert s1 in graph.state_sets
    assert s2 in graph.state_sets
    assert s3 in graph.state_sets
    assert s4 in graph.state_sets
    assert s6 in graph.state_sets

def test_edges():
    pass

