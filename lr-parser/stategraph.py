import sys
sys.path.append("../")

from state import StateSet, State, LR1Element
from production import Production
from helpers import first, follow, closure_0, goto_0, closure_1, goto_1
from syntaxtable import FinishSymbol
from constants import LR0, LR1, LALR

class StateGraph(object):

    def __init__(self, start_symbol, grammar, lr_type=0):
        self.grammar = grammar
        self.start_symbol = start_symbol
        self.state_sets = []
        self.edges = {}

        if lr_type == LR0:
            self.closure = closure_0
            self.goto = goto_0
            self.start_set = StateSet([State(Production(None, [self.start_symbol]), 0)])
        elif lr_type == LR1 or lr_type == LALR:
            self.closure = closure_1
            self.goto = goto_1
            self.start_set = StateSet([LR1Element(Production(None, [self.start_symbol]), 0, set([FinishSymbol()]))])

    def build(self):
        start_set = self.start_set
        closure = self.closure(self.grammar, start_set)
        self.state_sets.append(closure)
        _id = 0
        while _id < len(self.state_sets):
            state_set = self.state_sets[_id]
            for symbol in state_set.get_next_symbols():
                new_state_set = self.goto(self.grammar, state_set, symbol)
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
            return _id
        except KeyError:
            return None

    def get_symbols(self):
        s = set()
        for _, symbol in self.edges.keys():
            s.add(symbol)
        return s

    def get_state_set(self, i):
        return self.state_sets[i]

    def convert_lalr(self):
        removelist = set([])
        l = len(self.state_sets)
        for i in range(l):
            if i in removelist:
                continue
            for j in range(l):
                if j in removelist:
                    continue
                s1 = self.state_sets[i]
                s2 = self.state_sets[j]
                if s1 is not s2 and s1.equals(s2, False):
                    for e in s2:
                        s1.add(e) # this should automatically merge the lookahead of the states
                    s1.merge()
                    for key in self.edges:
                        fromid, symbol = key
                        to = self.edges[key]
                        if fromid == j:
                            fromid == i
                        if to == j:
                            to == i
                        self.edges.pop(key)
                        self.edges[(fromid, symbol)] = to
                    removelist.add(j)
        l = list(removelist)
        l.sort()
        l.reverse()
        for j in l:
            self.state_sets.pop(j)

