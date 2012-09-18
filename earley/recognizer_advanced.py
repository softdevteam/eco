from gparser import Nonterminal, Terminal
from recognizer import Production, State, StateSet

class RecognitionError(Exception):
    pass

class AdvancedRecognizer(object):

    def __init__(self, start_symbol, grammar, inputstring, lookahead=1):
        self.start_symbol = start_symbol
        self.grammar = grammar
        self.inputstring = inputstring
        self.lookahead = lookahead
        self.statesets = []
        self.pos = 0
        self.s_pos = 0
        self._init_statesets()

    def read_current_input_symbol(self):
        current_stateset = self.get_current_stateset()

        for s in current_stateset.elements:
            self.scan(s)
            self.predict(s)
            self.complete(s)
        if self.s_pos < len(self.inputstring) and self.get_next_stateset() == None:
            raise RecognitionError("Stateset remained empty after scanning")


    def isvalid(self):
        while self.s_pos < len(self.inputstring):
            try:
                self.read_current_input_symbol()
            except RecognitionError:
                return False
            self.pos += 1

        self.read_current_input_symbol()
        if State(Production(None, [self.start_symbol]), 1, 0) in self.statesets[-1]:
            return True

        return False

    def end_of_string(self):
        return self.pos >= len(self.inputstring)

    def get_current_stateset(self):
        try:
            return self.statesets[self.pos]
        except IndexError:
            raise RecognitionError

    def get_current_input(self):
        return self.inputstring[self.pos]

    def add_to_stateset(self, state, i):
        try:
            ss = self.statesets[i]
        except IndexError:
            ss = StateSet()
            self.statesets.append(ss)

        ss.elements.append(state)

    def get_next_stateset(self):
        try:
            return self.statesets[self.pos+1]
        except IndexError:
            return None

    def _init_statesets(self):
        # create startset
        p = Production(None, [self.start_symbol])
        state = State(p, 0, 0)
        self.add_to_stateset(state, 0)

    def predict(self, s):
        if s.isfinal() or not isinstance(s.next_symbol(), Nonterminal):
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
        ns = s.next_symbol().raw
        if self.inputstring[self.s_pos:self.s_pos+len(ns)] == ns:
            newstate = s.clone()
            newstate.d += 1
            print("    Adding", newstate)
            self.add_to_stateset(newstate, self.pos + 1)
            self.s_pos += len(ns)

    def complete(self, s):
        if not s.isfinal():
            return

        print("Completing", s)
        old_state_set = self.statesets[s.get_backpointer()]
        for old_state in old_state_set.elements:
            if old_state.next_symbol() and old_state.next_symbol() == s.get_left():
                print("        Adding from fromer state:", old_state)
                newstate = old_state.clone()
                newstate.d += 1
                self.get_current_stateset().elements.append(newstate)
