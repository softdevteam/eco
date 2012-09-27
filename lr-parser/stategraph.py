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

    def build(self):
        start_set = StateSet([State(Production(None, [self.start_symbol]), 0)])
        closure = closure_0(self.grammar, start_set)
        self.state_sets.append(closure)
        for state_set in self.state_sets:
            for symbol in state_set.get_next_symbols():
                new_state_set = goto_0(self.grammar, state_set, symbol)
                if not new_state_set.is_empty():
                    self.add(new_state_set)

    def add(self, state_set):
        if state_set not in self.state_sets:
            self.state_sets.append(state_set)
