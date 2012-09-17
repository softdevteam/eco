from gparser import Nonterminal, Terminal
from recognizer import Production, State, StateSet

class AdvancedRecognizer(object):

    def __init__(self, start_symbol, grammar, inputstring, lookahead=1):
        self.start_symbol = start_symbol
        self.grammar = grammar
        self.inputstring = inputstring
        self.lookahead = lookahead
        self.statesets = []
        self.pos = 0
        self._init_statesets()

    def read_current_input_symbol(self):
        current_stateset = self.get_current_stateset()

        for s in current_stateset.elements:
            self.scan(s)
            self.predict(s)
            self.complete(s)
            if self.pos < len(self.inputstring) and self.get_next_stateset() == []:
                raise Exception("Stateset remained empty after scanning")


    def isvalid(self):
        while self.pos <= len(self.inputstring):
            self.read_current_input_symbol()
            self.pos += 1

        if State(Production(None, [self.start_symbol]), 1, 0) in self.statesets[self.pos-1]:
            return True

        return False

    def end_of_string(self):
        return self.pos >= len(self.inputstring)

    def get_current_stateset(self):
        return self.statesets[self.pos]

    def get_current_input(self):
        return self.inputstring[self.pos]

    def get_next_stateset(self):
        return self.statesets[self.pos+1]

    def _init_statesets(self):
        for _ in range(len(self.inputstring)+1):
            ss = StateSet()
            self.statesets.append(ss)

        # create startset
        p = Production(None, [self.start_symbol])
        state = State(p, 0, 0)
        s0 = self.statesets[0]
        s0.elements.append(state)

    def predict(self, s):
        if s.isfinal() or self.end_of_string() or not isinstance(s.next_symbol(), Nonterminal):
            return

        print("Predicting", s)
        current_stateset = self.get_current_stateset()
        symbol = s.next_symbol()
        # add alternatives of that Nonterminal to stateset
        rule = self.grammar[symbol]
        alternatives = rule.alternatives
        for a in alternatives:
            p = Production(symbol, a)
            s = State(p, 0, self.pos)
            if s not in current_stateset.elements:
                # since we add new states to the set we are iterating over
                # we automatically process the new states, too
                print("    adding", s)
                current_stateset.elements.append(s)

    def scan(self, s):
        if s.isfinal() or self.end_of_string() or not isinstance(s.next_symbol(), Terminal):
            return

        print("Scanning", s)
        if s.next_symbol().raw == self.get_current_input():
            newstate = s.clone()
            newstate.d += 1
            print("    Adding", newstate)
            self.get_next_stateset().elements.append(newstate)

    def complete(self, s):
        if not s.isfinal():
            return

        print("Completing", s)
        old_state_set = self.statesets[s.get_backpointer()]
        for old_state in old_state_set.elements:
            if old_state.next_symbol() == s.get_left():
                print("        Adding from fromer state:", old_state)
                newstate = old_state.clone()
                newstate.d += 1
                self.get_current_stateset().elements.append(newstate)
