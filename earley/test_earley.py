from gparser import Parser, Rule, Nonterminal, Terminal
from recognizer import Recognizer, State, Production

grammar1 = """
E ::= E "+" E
    | "a"
"""

class TestRecognizer(object):

    def setup_method(self, method):
        p = Parser(grammar1)
        p.parse()
        self.p = p.rules

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

    def test_recognizer_init(self):
        r = Recognizer(self.p, "a")
        s0 = r.states[0]
        assert Production(Nonterminal("E"), [Terminal("\"a\"")]) in s0
        assert Production(Nonterminal("E"), [Nonterminal("E"), Terminal("\"+\""), Nonterminal("E")]) in s0

