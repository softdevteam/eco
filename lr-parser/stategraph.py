from __future__ import print_function
import sys
sys.path.append("../")

from state import StateSet, State, LR1Element, LR0Element
from production import Production
from helpers import closure_0, goto_0, Helper
from syntaxtable import FinishSymbol
from constants import LR0, LR1, LALR
from time import time

class StateGraph(object):

    def __init__(self, start_symbol, grammar, lr_type=0):
        self.grammar = grammar
        self.start_symbol = start_symbol
        self.state_sets = []
        self.edges = {}
        self.ids = {}

        self.goto_time = 0
        self.add_time = 0
        self.closure_time = 0
        self.addcount = 0

        helper = Helper(grammar)
        if lr_type == LR0:
            self.closure = helper.closure_0
            self.goto = helper.goto_0
            self.start_set = StateSet([LR0Element(Production(None, [self.start_symbol]), 0)])
        elif lr_type == LR1 or lr_type == LALR:
            self.closure = helper.closure_1
            self.goto = helper.goto_1
            self.start_set = StateSet([LR1Element(Production(None, [self.start_symbol]), 0, set([FinishSymbol()]))])

    def build(self):
        State._hashtime = 0
        start = time()
        start_set = self.start_set
        closure = self.closure(start_set)
        self.state_sets.append(closure)
        self.ids[closure] = 0
        _id = 0
        todo = []
        todo.append(_id)
        while _id < len(self.state_sets):
            #print(_id)
            if _id % 1000 == 0:
                sys.stdout.write(".")
            if _id % 10000 == 0:
                sys.stdout.write("\n")
            sys.stdout.flush()
            state_set = self.state_sets[_id]
            new_gotos = {}
            goto_start = time()
            # create new sets first, then calculate closure
            for lrelement in state_set.elements:
                symbol = lrelement.next_symbol()
                if not symbol:
                    continue
                #XXX optimisation: create all configurations before building
                new_element = lrelement.clone()
                new_element.d += 1
                try:
                    # basically goto
                    new_gotos[symbol].add(new_element)
                except KeyError:
                    new_gotos[symbol] = set([new_element])
            # now calculate closure and add result to state_sets
            goto_end = time()
            self.goto_time += goto_end - goto_start
            for ss in new_gotos:
                closure_start = time()
                new_state_set = self.closure(StateSet(new_gotos[ss]))
                closure_end = time()
                #print("before", len(new_state_set.elements))
                #new_state_set.merge()
                #print("after", len(new_state_set.elements))
                self.closure_time += closure_end - closure_start
                self.add(_id, ss, new_state_set)


           #for symbol in state_set.get_next_symbols(): #XXX investigate speed
           #    goto_start = time()
           #    new_state_set = self.goto(state_set, symbol)
           #    goto_end = time()
           #    print("goto time", goto_end - goto_start)
           #    if not new_state_set.is_empty():
           #        add_start = time()
           #        self.add(_id, symbol, new_state_set)
           #        add_end = time()
           #        print("add time", add_end - add_start)
            _id += 1
            #print("elements", len(state_set.elements))
            #print("closure time", self.closure_time)
            #self.closure_time = 0
        end = time()
        print("add time", self.add_time)
        print("closure time", self.closure_time)
        print("goto time", self.goto_time)
        print("hashtime", StateSet._hashtime)
        print("addcount", self.addcount)
        print("Finished building Stategraph in ", end-start)
        self.closure = None
        self.goto = None

    def weakly_compatible(self, s1, s2):
        core = s1.elements
        if core != s2.elements:
            return False
        if len(core) == 1:
            return True
        core1 = list(core)
        core2 = list(s2.elements)
        for i in range(0, len(core)-1):
            for j in range(i+1, len(core)):
                if ((core1[i].lookahead & core2[j].lookahead or core1[j].lookahead & core2[i].lookahead)
                    and not core1[i].lookahead & core1[j].lookahead
                    and not core2[i].lookahead & core2[j].lookahead):
                    return False
        return True

    def find_stateset_without_lookahead(self, state_set):
        for ss in self.state_sets:
            if state_set.equals(ss, True):
                return ss
        return None

    def merge_lookahead(self, old, new):
        changed = False
        for e1 in new.elements:
            for e2 in old.elements:
                if e1 == e2: # compare without lookahead
                    #print("merging", e1, "and", e2)
                    if e1.lookahead - e2.lookahead:
                        changed = True
                    e2.lookahead |= e1.lookahead
        return changed

    def add(self, from_id, symbol, state_set):
        merged = False
        for candidate in self.state_sets:
            if self.weakly_compatible(state_set, candidate):
                # merge them
                changed = merge_lookahead(candidate, state_set)
                if changed:
                    # move state to todo list
        if not merged:
            # add normally and put on todo list

        # LALR way
       #ss = self.find_stateset_without_lookahead(state_set)
       #if ss:
       #    #print("found existing stateset -> merging")
       #    #print(ss)
       #    #print(state_set)
       #    self.merge_lookahead(ss, state_set)
       #    _id = self.state_sets.index(ss)
       #else:
       #    self.state_sets.append(state_set)
       #    _id = len(self.state_sets)-1
       #self.edges[(from_id, symbol)] = _id

        # normal LR(1) way
       #add_start = time()
       #_id = self.ids.get(state_set)
       #if _id is None: # new state
       #    self.addcount += 1
       #    self.state_sets.append(state_set)
       #    _id = len(self.state_sets)-1
       #    self.ids[state_set] = _id
       #self.edges[(from_id, symbol)] = _id
       #add_end = time()
       #self.add_time += add_end - add_start

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

