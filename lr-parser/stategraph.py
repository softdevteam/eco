import sys
sys.path.append("../")

from state import StateSet, State
from production import Production
from helpers import first, follow, closure_0, goto_0

class StateGraph(object):

    def __init__(self, start_symbol, grammar):
        self.grammar = grammar
        self.start_symbol = start_symbol
        self.state_sets = []
        self.edges = {}

    def build(self):
        start_set = StateSet([State(Production(None, [self.start_symbol]), 0)])
        closure = closure_0(self.grammar, start_set)
        self.state_sets.append(closure)
        _id = 0
        while _id < len(self.state_sets):
            state_set = self.state_sets[_id]
            for symbol in state_set.get_next_symbols():
                new_state_set = goto_0(self.grammar, state_set, symbol)
                if not new_state_set.is_empty():
                    self.add(_id, symbol, new_state_set)

            _id += 1

    def add(self, from_id, symbol, state_set):
        if state_set not in self.state_sets:
            self.state_sets.append(state_set)
            _id = len(self.state_sets)-1
        else:
            _id = self.state_sets.index(state_set)
        self.edges[(from_id, symbol)] = _id

    def follow(self, from_id, symbol):
        try:
            _id = self.edges[(from_id, symbol)]
            return self.state_sets[_id]
        except KeyError:
            return None
