import sys
sys.path.append("../")

from lrparser import LRParser
from incparser import IncParser
from constants import LR0, LR1, LALR
from astree import AST, Node
from gparser import Parser, Nonterminal, Terminal, Epsilon

grammar = """
    E ::= T
        | E "+" T
    T ::= P
        | T "*" P
    P ::= "1" | "2" | "3" | "4" | "5" | "6" | "7" | "8" | "9"
"""

E = Nonterminal("E")
T = Nonterminal("T")
P = Nonterminal("P")
plus = Terminal("\"+\"")
mul = Terminal("\"*\"")
n1 = Terminal("\"1\"")
n2 = Terminal("\"2\"")
n3 = Terminal("\"3\"")

def notest_ast():
    lrp = LRParser(grammar)
    lrp.check("1 + 2 * 3")
    ast = lrp.get_ast()

    AST(
        Node(E, [
            Node(E, [Node(T, [Node(P, [n1])])]),
            Node(plus, []),
            Node(T, [
                Node(T, [Node(P, [n2])]),
                Node(mul, []),
                Node(P, [n3])
            ])
        ])
    ) == ast

    lrp.check("1 + 2 * 1")
    ast2 = lrp.get_ast()

def test_incparser_ast():
    lrp = IncParser(grammar)

    lrp.check("1 + 2 * 3")
    ast1 = lrp.get_ast()

    lrp.check("1 + 2 * 1")
    ast2 = lrp.get_ast()

    # reparsing should reuse parent node
    assert ast1.parent is ast2.parent
