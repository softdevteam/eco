from __future__ import print_function
import sys
sys.path.append("../")

from state import StateSet, State, LR1Element
from production import Production
from helpers import closure_0, goto_0, Helper
from syntaxtable import FinishSymbol
from constants import LR0, LR1, LALR

class StateGraph(object):

    def __init__(self, start_symbol, grammar, lr_type=0):
        self.grammar = grammar
        self.start_symbol = start_symbol
        self.state_sets = []
        self.edges = {}

        helper = Helper(grammar)
        if lr_type == LR0:
            self.closure = helper.closure_0
            self.goto = helper.goto_0
            self.start_set = StateSet([State(Production(None, [self.start_symbol]), 0)])
        elif lr_type == LR1 or lr_type == LALR:
            self.closure = helper.closure_1
            self.goto = helper.goto_1
            self.start_set = StateSet([LR1Element(Production(None, [self.start_symbol]), 0, set([FinishSymbol()]))])

    def build(self):
        print("go")
        start_set = self.start_set
        closure = self.closure(start_set)
        self.state_sets.append(closure)
        _id = 0
        while _id < len(self.state_sets):
            print(_id)
            state_set = self.state_sets[_id]
            for symbol in state_set.get_next_symbols():
                new_state_set = self.goto(state_set, symbol)
                if not new_state_set.is_empty():
                    self.add(_id, symbol, new_state_set)
            _id += 1

    def find_stateset_without_lookahead(self, state_set):
        for ss in self.state_sets:
            if state_set.equals(ss, False):
                return ss
        return None

    def merge_lookahead(self, old, new):
        for e1 in new:
            for e2 in old:
                if State.__eq__(e1, e2): # compare without lookahead
                    #print("merging", e1, "and", e2)
                    e2.lookahead |= e1.lookahead

    def add(self, from_id, symbol, state_set):
        #XXX lalr hack: merge states that only differ in there lookahead

        ss = self.find_stateset_without_lookahead(state_set)
        if ss:
            #print("found existing stateset -> merging")
            #print(ss)
            #print(state_set)
            self.merge_lookahead(ss, state_set)
            _id = self.state_sets.index(ss)
        else:
            self.state_sets.append(state_set)
            _id = len(self.state_sets)-1
        self.edges[(from_id, symbol)] = _id

       #if state_set not in self.state_sets:
       #    self.state_sets.append(state_set)
       #    _id = len(self.state_sets)-1
       #else:
       #    _id = self.state_sets.index(state_set)
       #self.edges[(from_id, symbol)] = _id

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

