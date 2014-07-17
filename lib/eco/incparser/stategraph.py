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

from __future__ import print_function

from state import StateSet, State, LR1Element, LR0Element
from production import Production
from helpers import closure_0, goto_0, Helper
from syntaxtable import FinishSymbol
from constants import LR0, LR1, LALR
from time import time
import logging

class StateGraph(object):

    def __init__(self, start_symbol, grammar, lr_type=0):
        self.grammar = grammar
        self.start_symbol = start_symbol
        self.state_sets = []
        self.edges = {}
        self.ids = {}
        self.todo = []
        self.done = set()
        self.maybe_compatible = {}

        self.goto_time = 0
        self.add_time = 0
        self.closure_time = 0
        self.closure_count = 0
        self.addcount = 0
        self.weakly = 0
        self.weakly_count = 0
        self.mergetime = 0

        helper = Helper(grammar)
        self.helper = helper
        if lr_type == LR0:
            self.closure = helper.closure_0
            self.goto = helper.goto_0
            self.start_set = StateSet([LR0Element(Production(None, [self.start_symbol]), 0)])
        elif lr_type == LR1 or lr_type == LALR:
            self.closure = helper.closure_1
            self.goto = helper.goto_1
            self.start_set = StateSet()
            self.start_set.add(LR0Element(Production(None, [self.start_symbol]), 0), set([FinishSymbol()]))

    def build(self):
        State._hashtime = 0
        start = time()
        start_set = self.start_set
        closure = start_set
        #closure = self.closure(start_set)
        self.state_sets.append(closure)
        self.ids[closure] = 0
        _id = 0
        self.todo.append(_id)
        while self.todo:
            self.addcount += 1
            _id = self.todo.pop()
            self.done.add(_id)
            #print("id:", _id)
            closure_start = time()
            state_set = self.closure(self.state_sets[_id])
            self.closure_count += 1
            closure_end = time()
            self.closure_time += closure_end - closure_start
            #state_set = self.state_sets[_id]
            new_gotos = {}
            goto_start = time()
            # create new sets first, then calculate closure
            for lrelement in state_set.elements:
                symbol = lrelement.next_symbol()
                if not symbol: # state is final
                    continue
                #XXX optimisation: create all configurations before building
                new_element = lrelement.clone()
                new_element.d += 1
                new_element_la = state_set.get_lookahead(lrelement)
                stateset = new_gotos.setdefault(symbol, StateSet())
                stateset.add(new_element, new_element_la)

            # now calculate closure and add result to state_sets
            goto_end = time()
            self.goto_time += goto_end - goto_start

            for ss in new_gotos:
                new_state_set = new_gotos[ss]
                #new_state_set = self.closure(new_gotos[ss])
                add_start = time()
                self.add(_id, ss, new_state_set)
                add_end = time()
                self.add_time += add_end - add_start

        end = time()
        logging.info("add time %s", self.add_time)
        logging.info("closure time %s", self.closure_time)
        logging.info("closure time helper %s", self.helper.closure_time)
        logging.info("goto time %s", self.goto_time)
        logging.info("hashtime %s", StateSet._hashtime)
        logging.info("addcount %s", self.addcount)
        logging.info("states %s", len(self.state_sets))
        logging.info("weakly %s", self.weakly)
        logging.info("weakly count %s", self.weakly_count)
        logging.info("mergetime %s", self.mergetime)
        #print("maybe", self.maybe_compatible)
        #for key in self.maybe_compatible:
        #    print(key, len(self.maybe_compatible[key]))


        # apply closure
        logging.info("Apply closure to states")
        clstart = time()
        new_state_sets = []
        new_ids = {}
        for state in self.state_sets:
            _id = self.ids[state]
            new_state = self.closure(state)
            new_state_sets.append(new_state)
            new_ids[new_state] = new_state
        self.state_sets = new_state_sets
        logging.info("after closure %s", len(new_state_sets))
        logging.info("edges %s", len(set(self.edges.values())))
        self.ids = new_ids
        logging.info(time() - clstart)

        logging.info("Finished building Stategraph in %s", end-start)
        self.closure = None
        self.goto = None

    def weakly_compatible(self, s1, s2):
        self.weakly_count += 1
        core = s1.elements
        if core != s2.elements:
            return False
        if len(core) == 1:
            return True
        self.weakly -= time()
        core = list(core)
        for i in range(0, len(core)-1):
            I = core[i]
            for j in range(i+1, len(core)):
                J = core[j]
                if ((s1.lookaheads[I] & s2.lookaheads[J] or s1.lookaheads[J] & s2.lookaheads[I])
                    and not s1.lookaheads[I] & s1.lookaheads[J]
                    and not s2.lookaheads[I] & s2.lookaheads[J]):
                    self.weakly += time()
                    return False
        self.weakly += time()
        return True

    def find_stateset_without_lookahead(self, state_set):
        for ss in self.state_sets:
            if state_set.equals(ss, True):
                return ss
        return None

    def merge_lookahead(self, old, new):
        self.mergetime -= time()
        changed = False
       #for e1 in new.elements:
       #    for e2 in old.elements:
       #        if e1 == e2: # compare without lookahead
       #            #print("merging", e1, "and", e2)
       #            if e1.lookahead - e2.lookahead:
       #                changed = True
       #            e2.lookahead |= e1.lookahead
        for element in new.elements:
            la1 = new.get_lookahead(element)
            la2 = old.get_lookahead(element)
            if la1 - la2:
                changed = True
                new_la = la2 | la1
                old.lookaheads[element] = new_la

        self.mergetime += time()
        return changed

    def add(self, from_id, symbol, state_set):
        merged = False
        #for candidate in self.state_sets: # only check states that can be reached by symbol
        for _id in self.maybe_compatible.setdefault(symbol,set()):
            candidate = self.state_sets[_id]
            if self.weakly_compatible(state_set, candidate):
                # merge them
                merged = True
                changed = self.merge_lookahead(candidate, state_set)
                self.edges[(from_id, symbol)] = _id
                if changed and _id in self.done:
                    # move state to todo list
                    self.todo.append(_id) #XXX only need to to that if this state is already done (moving not necessary if it hasn't been looked at anyway (e.g. state at the end of list)
                    self.done.remove(_id)

        if not merged:
            # add normally and put on todo list
            self.state_sets.append(state_set)
            _id = len(self.state_sets)-1
            self.edges[(from_id, symbol)] = _id
            self.ids[state_set] = _id
            self.todo.append(_id)

            # add to maybe compatible
            mc = self.maybe_compatible.setdefault(symbol, set())
            mc.add(_id)

    def oldadd(self, from_id, symbol, state_set):
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
        add_start = time()
        _id = self.ids.get(state_set)
        if _id is None: # new state
            self.addcount += 1
            self.state_sets.append(state_set)
            _id = len(self.state_sets)-1
            self.ids[state_set] = _id
            self.todo.append(_id)
        self.edges[(from_id, symbol)] = _id
        add_end = time()
        self.add_time += add_end - add_start

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

