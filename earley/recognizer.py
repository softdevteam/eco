
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

    def __repr__(self):
        right = [x.name for x in self.p.right]
        right.insert(self.d, ".")
        right = "".join(right)
        s = "%s ::= %s %s %s" % (self.p.left.name, right, self.k, self.b)
        return s

    def equals_str(self, s):
        return self.__repr__() == s

class Recognizer(object):

    terminal = "|"

    def __init__(self, grammar, inputstring, lookahead=1):
        self.grammar = grammar
        self.inputstring = inputstring
        self.lookahead = lookahead
        self.states = []
        self.pos = 0
        self.create_state_zero()

    def start(self):
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

    def create_state_zero(self):
        start = self.grammar[0]
        state = set()
        for a in start.alternatives:
            p = Production(start.symbol, a)
            state.add(p)
        self.states.append(state)

    def predict(self):
        pass
