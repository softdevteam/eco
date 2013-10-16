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

from production import Production
from grammar_parser.gparser import Terminal, Nonterminal, Epsilon
from constants import LR0, LR1, LALR

class SyntaxTableElement(object):

    def __init__(self, action):
        self.action = action

    def __eq__(self, other):
        return self.action == other.action

    def __repr__(self):
        return "%s(%s)" % (self.__class__.__name__, self.action)

class FinishSymbol(object):
    def __init__(self):
        self.name = "eos"

    def __eq__(self, other):
        return isinstance(other, FinishSymbol)

    def __hash__(self):
        # XXX hack: may cause errors if grammar consist of same symbol
        return hash("FinishSymbol123")

    def __repr__(self):
        return "$"

class Goto(SyntaxTableElement): pass
class Shift(SyntaxTableElement): pass

class Reduce(SyntaxTableElement):
    def amount(self):
        if self.action.right == [Epsilon()]:
            return 0
        return len(self.action.right)

class Accept(SyntaxTableElement):
    def __init__(self, action=None):
        self.action = None

class SyntaxTable(object):

    def __init__(self, lr_type=LR0):
        self.table = {}
        self.lr_type = lr_type

    def build(self, graph):
        start_production = Production(None, [graph.start_symbol])
        symbols = graph.get_symbols()
        symbols.add(FinishSymbol())
        for i in range(len(graph.state_sets)):
            # accept, reduce
            state_set = graph.get_state_set(i)
            for state in state_set.elements:
                if state.isfinal():
                    if state.p == start_production:
                        self.table[(i, FinishSymbol())] = Accept()
                    else:
                        if self.lr_type in [LR1, LALR]:
                            lookahead = state_set.lookaheads[state]
                        else:
                            lookahead = symbols
                        for s in lookahead:
                            if self.table.has_key((i,s)):
                                msg = "Conflict at %s for %s: %s => Reduce(%s)"
                                print msg % (i, s, self.table[(i,s)], state.p)
                                #print("CONFLICT", (i,s), "before:", self.table[(i,s)], "now:", "Reduce(", state.p, ")")
                            self.table[(i, s)] = Reduce(state.p)
            # shift, goto
            for s in symbols:
                dest = graph.follow(i, s)
                if dest:
                    if isinstance(s, Terminal):
                        action = Shift(dest)
                    if isinstance(s, Nonterminal):
                        action = Goto(dest)
                    if self.table.has_key((i,s)):
                        print("CONFLICT", (i,s), "before:", self.table[(i,s)], "now:", action)
                    self.table[(i, s)] = action

    def lookup(self, state_id, symbol):
        try:
            return self.table[(state_id, symbol)]
        except KeyError:
            return None
