# Copyright (c) 2012--2013 King's College London
# Created by the Software Development Team <http://soft-dev.org/>
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to
# deal in the Software without restriction, including without limitation the
# rights to use, copy, modify, merge, publish, distribute, sublicense, and/or
# sell copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
# FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS
# IN THE SOFTWARE.

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
plus = Terminal("+")
mul = Terminal("*")
n1 = Terminal("1")
n2 = Terminal("2")
n3 = Terminal("3")

def test_node():
    i1 = Node(1, 0, [])
    i2 = Node(2, 0, [])
    plus = Node("+", 0, [])
    parent = Node("T", 0, [i1, plus, i2])

    assert i1.right_sibling() is plus
    assert plus.right_sibling() is i2
    assert i2.right_sibling() is None

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
