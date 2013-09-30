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

from syntaxtable import SyntaxTable, Goto, Shift, Reduce, Accept, FinishSymbol
from stategraph import StateGraph
from grammar_parser.gparser import Parser, Terminal, Nonterminal, Epsilon
from production import Production

grammar = """
    S ::= "b" A "d"
    A ::= "c"
        |
"""

p = Parser(grammar)
p.parse()
r = p.rules

b = Terminal("b")
c = Terminal("c")
d = Terminal("d")
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
