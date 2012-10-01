import sys
sys.path.append("../")

from production import Production
from gparser import Terminal, Nonterminal, Epsilon

class SyntaxTableElement(object):

    def __init__(self, action):
        self.action = action

    def __eq__(self, other):
        return self.action == other.action

    def __repr__(self):
        return "%s(%s)" % (self.__class__.__name__, self.action)

class FinishSymbol(object):
    def __eq__(self, other):
        return isinstance(other, FinishSymbol)

    def __hash__(self):
        # XXX hack: may cause errors if grammar consist of same symbol
        return hash("FinishSymbol123")

class Goto(SyntaxTableElement): pass
class Shift(SyntaxTableElement): pass
class Reduce(SyntaxTableElement): pass
class Accept(SyntaxTableElement):
    def __init__(self, action=None):
        self.action = None

class SyntaxTable(object):

    def __init__(self):
        self.table = {}

    def build(self, graph):
        start_production = Production(None, [graph.start_symbol])
        symbols = graph.get_symbols()
        symbols.add(FinishSymbol())
        for i in range(len(graph.state_sets)):
            # accept, reduce
            state_set = graph.get_state_set(i)
            for state in state_set:
                if state.isfinal():
                    if state.p == start_production:
                        self.table[(i, FinishSymbol())] = Accept()
                    else:
                        for s in symbols:
                            self.table[(i, s)] = Reduce(state.p)
            # shift, goto
            for s in symbols:
                dest = graph.follow(i, s)
                if dest:
                    if isinstance(s, Terminal) or isinstance(s, Epsilon):
                        action = Shift(dest)
                    if isinstance(s, Nonterminal):
                        action = Goto(dest)
                    self.table[(i, s)] = action

    def lookup(self, state_id, symbol):
        try:
            return self.table[(state_id, symbol)]
        except KeyError:
            return None
