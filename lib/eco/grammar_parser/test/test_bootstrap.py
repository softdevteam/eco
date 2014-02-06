from grammar_parser.bootstrap import BootstrapParser
from grammar_parser.gparser import Nonterminal, Terminal, Epsilon

class Test_Bootstrap(object):

    def test_simple(self):
        grammar = """
X ::= A "b"
    | C;

A ::= "a";
C ::= "c";

%%

a:"a"
b:"b"
c:"c"
"""
        bp = BootstrapParser()
        bp.parse(grammar)
        assert bp.start_symbol == Nonterminal("X")
        assert bp.rules[Nonterminal("X")].symbol == Nonterminal("X")
        assert bp.rules[Nonterminal("X")].alternatives == [[Nonterminal("A"), Terminal("b")], [Nonterminal("C")]]
        assert bp.rules[Nonterminal("A")].alternatives == [[Terminal("a")]]
        assert bp.rules[Nonterminal("C")].alternatives == [[Terminal("c")]]

    def test_empty_alternative(self):
        grammar = """
A ::= "a"
    | ;

%%

a:"a"
"""
        bp = BootstrapParser()
        bp.parse(grammar)
        assert bp.start_symbol == Nonterminal("A")
        assert bp.rules[Nonterminal("A")].alternatives == [[Terminal("a")], [Epsilon()]]

import py
from treemanager import TreeManager
from incparser.incparser import IncParser
class Test_EcoGrammar(object):

    def test_error(self):
        bootstrap = BootstrapParser()
        test_grammar = """S ::= A {If(child1=#1, child2=[#3, #4]}; %% a:\"a\""""
        py.test.raises(Exception, "bootstrap.parse(test_grammar)")

    def test_simple(self):
        bootstrap = BootstrapParser()
        test_grammar = """S ::= A {If(child1=#1, child2=[#3, #4])}; A ::= \"a\"; %% a:\"a\""""
        bootstrap.parse(test_grammar)

    def test_bootstrapping(self):
        bootstrap = BootstrapParser(lr_type=1, whitespaces=False)
        test_grammar = """S ::= "abc"; %% abc:\"abc\""""
        bootstrap.parse(test_grammar)
        self.treemanager = TreeManager()
        self.treemanager.add_parser(bootstrap.incparser, bootstrap.inclexer, "")
        self.treemanager.set_font_test(7, 17)
        self.treemanager.key_normal("a")
        assert bootstrap.incparser.last_status == False
        self.treemanager.key_normal("b")
        assert bootstrap.incparser.last_status == False
        self.treemanager.key_normal("c")
        assert bootstrap.incparser.last_status == True

