import sys
sys.path.append("../")

from production import Production
from gparser import Terminal, Nonterminal, Epsilon
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
                                print("CONFLICT", (i,s), "before:", self.table[(i,s)], "now:", "Reduce(", state.p, ")")
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
        print("syntaxtable done")

    def lookup(self, state_id, symbol):
        try:
            return self.table[(state_id, symbol)]
        except KeyError:
            return None
