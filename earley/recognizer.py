from gparser import Nonterminal, Terminal

class Production(object):

    def __init__(self, left, right):
        self.left = left
        self.right = right

    def __eq__(self, other):
        return self.left == other.left and self.right == other.right

    def __hash__(self):
        # XXX: this is not safe
        s = "%s|%s" % (self.left, self.right)
        return hash(s)

    def __repr__(self):
        return "Production(%s, %s)" % (self.left, self.right)

class State(object):

    def __init__(self, production, pos, backpointer, lookaheadsymbol):
        self.p = production
        self.d = pos
        self.b = backpointer
        self.k = lookaheadsymbol

    def next_symbol(self):
        return self.p.right[self.d]

    def end_of_production(self):
        return len(self.p.right) == self.d

    def get_left(self):
        return self.p.left

    def get_lookahead(self):
        if self.d+1 >= len(self.p.right):
            return self.k
        return self.p.right[self.d+1].name

    def get_backpointer(self):
        return self.b

    def get_lookahead_raw(self):
        return self.get_lookahead().strip("\"")

    def clone(self):
        return State(self.p, self.d, self.b, self.k)

    def __repr__(self):
        return "State(%s, %s, %s, %s)" % (self.p, self.d, self.b, self.k)

    def __str__(self):
        """Displays the state in readable form as used in the Earley paper"""
        if not self.p.left:
            left = "None"
        else:
            left = self.p.left.name
        right = [x.name for x in self.p.right]
        right.insert(self.d, ".")
        right = "".join(right)
        s = "%s ::= %s %s %s" % (left, right, self.k, self.b)
        return s

    def equals_str(self, s):
        return self.__str__() == s

    def __eq__(self, other):
        return self.p == other.p and self.d == other.d and self.b == other.b and self.k == other.k

class StateSet(object):

    def __init__(self):
        self.elements = []

    def __contains__(self, element):
        return element in self.elements

class Recognizer(object):

    terminal = "|"

    def __init__(self, grammar, inputstring, lookahead=1):
        self.grammar = grammar
        self.inputstring = inputstring
        self.lookahead = lookahead
        self.statesets = []
        self.pos = 0
        self._init_statesets()

    def isvalid(self):
        """
        PREDICTOR:
        Condition:
            - First symbol read from input string
        Then:
            - Fill current state with all possible productions that match that
              symbol

        SCANNER:
        Condition:
            - current symbol is a terminal
        Then:
            - add current state to next Stateset and move the dot

        COMPLETER
        Condition:
          - Current position at the end of a production
          - e.g. R -> a.
        Then:
          1) Compare look-ahead symbols from current state with next symbol from input string
          2) If they match
            a) Go back to the last stateset
            b) Add all states from that state to this state where R comes after the dot
            c) Do this recursively with all added states
        """

        while self.pos < len(self.inputstring):
            print("--------------------")
            print("Step:", self.pos)
            print("Current StateSet:", self.get_current_stateset().elements)
            self.predict()
            self.complete()
            self.scan()
            if self.get_next_stateset() == []:
                return False
            self.pos += 1
        if self.get_next_stateset().elements == [State(0, 2, 0, Recognizer.terminal)]:
            return True
        else:
            raise Exception("Something went wrong")

    def get_current_stateset(self):
        return self.statesets[self.pos]

    def get_current_input(self):
        return self.inputstring[self.pos]

    def get_next_stateset(self):
        return self.statesets[self.pos+1]

    def _init_statesets(self):
        for _ in self.inputstring:
            ss = StateSet()
            self.statesets.append(ss)

        # XXX get start symbol from parser
        p = Production(None, [Nonterminal("E")])
        state = State(p, 0, 0, self.terminal)
        s0 = self.statesets[0]
        s0.elements.append(state)

    def predict(self):
        currentstateset = self.get_current_stateset()
        for s in currentstateset.elements:
            print("Predicting", s)
            symbol = s.next_symbol()
            lookahead = s.get_lookahead()
            if isinstance(symbol, Nonterminal):
                # add alternatives of that Nonterminal to stateset
                rule = self.grammar[symbol]
                alternatives = rule.alternatives
                for a in alternatives:
                    p = Production(symbol, a)
                    s = State(p, 0, self.pos, lookahead)
                    if s not in currentstateset.elements:
                        # since we add new states to the set we are iterating over
                        # we automatically process the new states, too
                        currentstateset.elements.append(s)

    def scan(self):
        for s in self.get_current_stateset().elements:
            print("Scanning", s)
            if isinstance(s.next_symbol(), Terminal):
                if s.next_symbol().raw == self.get_current_input():
                    newstate = s.clone()
                    newstate.d += 1
                    print("    Adding", newstate)
                    self.get_next_stateset().elements.append(newstate)
        if self.get_next_stateset() == []:
            raise Exception("Stateset remained empty after scanning")

    def complete(self):
        for s in self.get_current_stateset().elements:
            print("Completing", s)
            if s.end_of_production():
                print("    reached end of production")
                if s.get_lookahead_raw() == self.get_current_input():
                    print("    current_symbol == lookahead")
                    old_state_set = self.statesets[s.get_backpointer()]
                    for old_state in old_state_set.elements:
                        if old_state.next_symbol() == s.get_left():
                            print("        Adding from fromer state:", old_state)
                            newstate = old_state.clone()
                            newstate.d += 1
                            self.get_current_stateset().elements.append(newstate)
