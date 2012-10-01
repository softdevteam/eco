import sys
sys.path.append("../")

from syntaxtable import SyntaxTable, Goto, Shift, Reduce, Accept, FinishSymbol
from stategraph import StateGraph
from gparser import Parser, Terminal, Nonterminal
from production import Production

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

S_bAd = Production(S, [b, A, d])
A_c = Production(A, [c])
A_None = Production(A, [None])

syntaxtable = {
    (0, b): Shift(2),
    (0, S): Goto(1),
    (1, FinishSymbol()): Accept(),
    (2, None): Shift(5),
    (2, c): Shift(4),
    (2, A): Goto(3),
    (3, d): Shift(6),
    (4, b): Reduce(A_c),
    (4, None): Reduce(A_c),
    (4, c): Reduce(A_c),
    (4, d): Reduce(A_c),
    (4, FinishSymbol()): Reduce(A_c),
    (5, b): Reduce(A_None),
    (5, None): Reduce(A_None),
    (5, c): Reduce(A_None),
    (5, d): Reduce(A_None),
    (5, FinishSymbol()): Reduce(A_None),
    (6, b): Reduce(S_bAd),
    (6, None): Reduce(S_bAd),
    (6, c): Reduce(S_bAd),
    (6, d): Reduce(S_bAd),
    (6, FinishSymbol()): Reduce(S_bAd),
}

def test_build():
    graph = StateGraph(p.start_symbol, p.rules)
    graph.build()
    st = SyntaxTable()
    st.build(graph)
    assert st.table == syntaxtable

def test_lookup():
    pass
