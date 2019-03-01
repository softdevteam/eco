# Copyright (c) 2012--2014 King's College London
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
    def __init__(self, name="eos"):
        self.name = name

    def __eq__(self, other):
        return isinstance(other, FinishSymbol)

    def __hash__(self):
        # XXX hack: may cause errors if grammar consist of same symbol
        return hash("FinishSymbol(%s)" % (self.name))

    def __repr__(self):
        return "$(%s)" % self.name

class Goto(SyntaxTableElement): pass
class Shift(SyntaxTableElement): pass

class Reduce(SyntaxTableElement):
    def __init__(self, action):
        self.action = action

    def amount(self):
        if len(self.action.right) > 0 and self.action.right[-1] == Terminal("<eos>"):
            return len(self.action.right) - 1
        if self.action.right == [Epsilon()]:
            return 0
        return len(self.action.right)

class Accept(SyntaxTableElement):
    def __init__(self, action=None):
        self.action = None

class SyntaxTable(object):

    def __init__(self, prod_ids, lr_type=LR0):
        self.lr_type = lr_type
        self.prod_ids = prod_ids

    def build(self, graph, precedences=[]):
        self.table = [{} for _ in range(len(graph.state_sets))]
        symbols = graph.get_symbols()
        symbols.add(FinishSymbol())
        for i in range(len(graph.state_sets)):
            # accept, reduce
            state_set = graph.get_state_set(i)
            for state in state_set.elements:
                if state.isfinal():
                    if state.p.left is None:
                        self.table[i][FinishSymbol()] = Accept()
                    else:
                        if self.lr_type in [LR1, LALR]:
                            lookahead = state_set.lookaheads[state]
                        else:
                            lookahead = symbols
                        for s in lookahead:
                            newaction = Reduce(state.p)
                            if self.table[i].has_key(s):
                                oldaction = self.table[i][s]
                                newaction = self.resolve_conflict(i, s, oldaction, newaction, precedences)
                            if newaction:
                                self.table[i][s] = newaction
                            else:
                                del self.table[i][s]
            # shift, goto
            for s in symbols:
                dest = graph.follow(i, s)
                if dest:
                    if isinstance(s, Terminal):
                        action = Shift(dest)
                    if isinstance(s, Nonterminal):
                        action = Goto(dest)
                    if self.table[i].has_key(s):
                        action = self.resolve_conflict(i, s, self.table[i][s], action, precedences)
                    if action:
                        self.table[i][s] = action
                    else:
                        del self.table[i][s]

    def resolve_conflict(self, state, symbol, oldaction, newaction, precedences):
        # input: old_action, lookup_symbol, new_action
        # return: action/error
        # shift/reduce or reduce/shift

        # get precedence and associativity
        newassoc = self.find_assoc(symbol, precedences)
        if oldaction.action.prec:
            # old production has a precedence attached to it
            symbol = Terminal(oldaction.action.prec)
            oldassoc = self.find_assoc(symbol, precedences)
        else:
            # otherwise use precedence from last terminal in production body
            prev_terminal = self.get_last_terminal(oldaction)
            oldassoc = self.find_assoc(prev_terminal, precedences)

        # if oldaction and lookup symbol have precedences & associativity
        # and conflict is shift/reduce
        if oldassoc and newassoc and not self.is_reduce_reduce(oldaction, newaction):
            if oldassoc[1] > newassoc[1]:
                # previous action has higher precedence -> do nothing
                return oldaction
            elif oldassoc[1] < newassoc[1]:
                # previous action has lower precedenec -> override action
                return newaction
            else:
                # both precedences are equal, use associativity
                if newassoc[0] == "%left":
                    # left binding -> reduce
                    return self.get_reduce(oldaction, newaction)
                elif newassoc[0] == "%right":
                    # right binding -> shift
                    return self.get_shift(oldaction, newaction)
                elif newassoc[0] == "%nonassoc":
                    # parsing error
                    return None
        else:
            # use built in fixes and print warning
            # shift/reduce: shift
            # reduce/reduce: use earlier reduce
            if self.is_reduce_reduce(oldaction, newaction):
                if self.prod_ids:
                    action = oldaction if self.prod_ids[oldaction.action] < self.prod_ids[newaction.action] else newaction
                else:
                    action = oldaction
                print("Warning: Reduce/Reduce conflict in state %s with %s: %s vs. %s => Solved in favour of %s." % (state, symbol, oldaction, newaction, action))
                return action
            else:
                print("Warning: Shift/Reduce conflict in state %s with %s: %s vs. %s => Solved by shift." % (state, symbol, oldaction, newaction))
                return self.get_shift(oldaction, newaction)
        print("Error: Shift/Reduce conflict in state %s with %s: %s vs. %s => Unsolved!" % (state, symbol, oldaction, newaction))

    def is_reduce_reduce(self, a1, a2):
        return isinstance(a1, Reduce) and isinstance(a2, Reduce)

    def get_reduce(self, a1, a2):
        if isinstance(a1, Reduce):
            return a1
        assert isinstance(a2, Reduce)
        return a2

    def get_shift(self, a1, a2):
        if isinstance(a1, Shift):
            return a1
        assert isinstance(a2, Shift)
        return a2

    def find_assoc(self, symbol, precedences):
        if not symbol:
            return None
        i = 0
        for p in precedences:
            name, terminals = p
            if symbol.name in terminals:
                return (name, i)
            i += 1

    def get_last_terminal(self, rule):
        for symbol in reversed(rule.action.right):
            if isinstance(symbol, Terminal):
                return symbol
        return None

    def lookup(self, state_id, symbol):
        try:
            return self.table[state_id][symbol]
        except KeyError:
            return None
