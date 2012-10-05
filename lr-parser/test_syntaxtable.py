import sys
sys.path.append("../")

from syntaxtable import SyntaxTable, Goto, Shift, Reduce, Accept, FinishSymbol
from stategraph import StateGraph
from gparser import Parser, Terminal, Nonterminal, Epsilon
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
A_None = Production(A, [Epsilon()])

syntaxtable = {
    (0, b): Shift(2),
    (0, S): Goto(1),

    (1, FinishSymbol()): Accept(),

    (2, c): Shift(4),
    (2, A): Goto(3),
    (2, d): Reduce(A_None),

    (3, d): Shift(5),

    (4, d): Reduce(A_c),

    (5, FinishSymbol()): Reduce(S_bAd),
}

def test_build():
    graph = StateGraph(p.start_symbol, p.rules, 1)
    graph.build()
    st = SyntaxTable(1)
    st.build(graph)
    for key in syntaxtable.keys():
        assert st.table[key] == syntaxtable[key]
