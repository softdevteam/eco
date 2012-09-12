from gparser import Parser, Rule, Nonterminal, Terminal
from recognizer import Recognizer, State, Production
import pytest

grammar1 = """
E ::= E "+" E
    | "a"
"""

class TestBasicClasses(object):

    def test_production(self):
        p1 = Production(Nonterminal("E"), [Terminal("a")])
        p2 = Production(Nonterminal("E"), [Terminal("a")])
        assert p1 == p2

    def test_state(self):
        p = Production(Nonterminal("E"), [Terminal("a")])
        s = State(p, 0, 0, Recognizer.terminal)
        assert s.equals_str("E ::= .a | 0")

    def test_state2(self):
        p = Production(Nonterminal("E"), [Nonterminal("E"), Terminal("\"+\""), Nonterminal("E")])
        s = State(p, 1, 0, Recognizer.terminal)
        assert s.equals_str("E ::= E.\"+\"E | 0")

    def test_state_functions(self):
        p = Production(Nonterminal("E"), [Terminal("\"a\"")])
        s = State(p, 0, 0, "|")
        assert s.next_symbol() == Terminal("\"a\"")
        s = State(p, 1, 0, "|")
        pytest.raises(IndexError, s.next_symbol)
        assert s.end_of_production()

    def test_state_nextsymbol(self):
        p = Production(Nonterminal("E"), [Nonterminal("E"), Terminal("\"+\""), Nonterminal("E")])
        s = State(p, 1, 0, Recognizer.terminal)
        assert s.next_symbol() == Terminal("\"+\"")

class TestRecognizer(object):

    def setup_method(self, method):
        p = Parser(grammar1)
        p.parse()
        self.p = p.rules
        self.r = Recognizer(self.p, "a+a")

    def test_init(self):
        s0 = self.r.statesets[0]
        assert s0.elements[0].equals_str("None ::= .E | 0")

    def test_predicter(self):
        """
        The predictor checks whether the next symbol is a Nonterminal. If so, it
        adds all alternatives of that Nonterminal to the current state.

        At the beginning we have the starting rule S ::= .E Thus the first
        phase of the predictor adds all productions with 'E' on the left side
        to the current state, which are:
            E ::= E + E | 0
            E ::= a     | 0
        """
        self.r.predict()
        s0 = self.r.statesets[0]
        assert s0.elements[0].equals_str("None ::= .E | 0")
        assert s0.elements[1].equals_str("E ::= .E\"+\"E | 0")
        assert s0.elements[2].equals_str("E ::= .\"a\" | 0")

    def test_predicter_lookahead(self):
        """
        In the other phases the predictor does the same with newly added
        productions, thus adding the same productions again, but this time with
        a different lookahead symbol (derived from E ::= E + E):
            E ::= .E + E + 0
            E ::= .a     + 0
        """
        self.r.predict()
        s0 = self.r.statesets[0]
        assert s0.elements[3].equals_str("E ::= .E\"+\"E \"+\" 0")
        assert s0.elements[4].equals_str("E ::= .\"a\" \"+\" 0")

    def test_scanner(self):
        """
        The scanner checks whether the next symbol is a Terminal and copies all
        states with this terminal over to the next stateset, with the dot moved
        one step further:
            E ::= a. | 0
            E ::= a. + 0
        """
        self.r.predict()
        self.r.scan()
        s1 = self.r.statesets[1]
        assert s1.elements[0].equals_str("""E ::= "a". | 0""")
        assert s1.elements[1].equals_str("""E ::= "a". "+" 0""")
        assert len(s1.elements) == 2

    def test_completer(self):
        """
        The completer takes action if a state has reached the end of its production.
        Then the completer:
            - compares the lookahead of that state with the next inputsymbol
            - goes back to the stateset indicated by the state
            - adds all state from the other stateset to this one where the left
              side of the current production is right of the dot
            - moves the dot one step further

        Our current stateset is S1:
            E ::= a. | 0
            E ::= a. + 0

        The next symbol is "+". Thus we go back to S0 and copy:
            E ::= E. + E | 0
            E ::= E. + E + 0
        over to S1
        """
        self.r.predict()
        self.r.scan()
        self.r.complete()
        s1 = self.r.statesets[1]
        assert s1.elements[2].equals_str("""None ::= E. | 0""")
        assert s1.elements[3].equals_str("""E ::= E."+"E | 0""")
        assert s1.elements[4].equals_str("""E ::= E."+"E "+" 0""")
        assert len(s1.elements) == 5
