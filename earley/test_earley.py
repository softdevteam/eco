from gparser import Parser, Rule, Nonterminal, Terminal
from recognizer import Recognizer, State, Production

grammar1 = """
E ::= E "+" E
E ::= a
"""

class TestRecognizer(object):

    def setup_method(self, method):
        p = Parser(grammar1)
        p.parse()
        self.p = p.rules

    def test_state(self):
        p = Production(Nonterminal("E"), [Terminal("a")])
        s = State(p, 0, 0, Recognizer.terminal)
        assert s.equals_str("E ::= .a | 0")

    def test_state2(self):
        p = Production(Nonterminal("E"), [Nonterminal("E"), Terminal("\"+\""), Nonterminal("E")])
        s = State(p, 1, 0, Recognizer.terminal)
        assert s.equals_str("E ::= E.\"+\"E | 0")

    def test_predictor(self):
        r = Recognizer(self.p, "a")
        r.predict()
        assert r.states[0] == ["E ::= E \"+\" E", "E ::= a"]

