from gparser import Nonterminal

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
        self.init_first_state()

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

    def init_first_state(self):
        # XXX get start symbol from parser
        p = Production(None, [Nonterminal("E")])
        state = State(p, 0, 0, self.terminal)
        s0 = StateSet()
        s0.elements.append(state)
        self.statesets.append(s0)

    def predict(self):
        currentstateset = self.statesets[self.pos]
        for s in currentstateset.elements:
            symbol = s.next_symbol()
            if isinstance(symbol, Nonterminal):
                # add alternatives of that Nonterminal to stateset
                rule = self.grammar[symbol]
                alternatives = rule.alternatives
                for a in alternatives:
                    p = Production(symbol, a)
                    s = State(p, 0, self.pos, Recognizer.terminal)
                    if s not in currentstateset.elements:
                        currentstateset.elements.append(s)
